#!/usr/bin/env python3
"""A live A/B review page: the real UI, side by side, with the human's words on it.

The comp round (`ux_question.py`) decides a direction from drawings. This decides
a *build* from the thing itself. Two variants of a real interface -- two routes on
a running dev server, two HTML files, or one of each -- are hosted side by side in
a page the reviewer opens, at whichever viewport width they want to judge it at.

Then the part that usually gets lost: they click any element inside either variant
and type, in their own words, what is wrong with it. That note is captured with
the element it is about -- selector, text, computed type, colour, spacing, radius,
shadow, box, viewport -- and written to `.deluxui/requests/REQ-NNN.yaml`, which is
a work item an agent can act on without guessing which card was meant.

Element notes work because this server **hosts** both variants rather than framing
them from elsewhere: a file is served, a URL is proxied, and in both cases the
selection script is injected into the HTML and the frame-blocking headers are
dropped on the way through. Same origin, so a click inside the frame is readable;
no dev-server plugin, no framework adapter, no build step.

The reviewer ends with one of five outcomes -- accept A, accept B, combine,
request changes, or reject -- and the first three are approvals the phase gate will
accept. "Request changes" deliberately is not: the notes are the work list, and
nothing has been approved yet.

    ux_review.py serve --variant "A=http://localhost:5173/jobs" \
                       --variant "B=http://localhost:5173/jobs?v=2" \
                       --question "Which job list do engineers read faster?"
    ux_review.py serve --variant "current=dist/index.html" --variant "proposed=/tmp/new.html"
    ux_review.py notes            # what the reviewer said, newest last
    ux_review.py watch            # stream notes as they arrive, for a long session

Exit: 0 a decision was recorded, 2 a variant could not be served, 3 nobody
reviewed it (NOT_RUN -- an unreviewed screen is not an approved one).
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yaml                                                        # noqa: E402
import ux_image                                                    # noqa: E402

DECISIONS = Path(".deluxui/decisions")
REQUESTS = Path(".deluxui/requests")
MIN_REASON = 40
SELF = re.compile(r"\b(?:claude|chatgpt|gpt|copilot|cursor|codex|gemini|llm|ai|"
                  r"agent|assistant|model|bot|automated|self|me|myself|"
                  r"this session|the tool)\b", re.I)

# The same vocabulary the operations use, so a note routes straight into a move
# that already exists. `note` is the default because the reviewer's own words are
# the point; the chip is a shortcut, not a form to fill in.
CHIPS = [("note", "just a note"), ("broken", "this is a defect"),
         ("bolder", "too quiet"), ("quieter", "too loud"),
         ("distill", "too much here"), ("clarify", "unclear"),
         ("layout", "arrangement"), ("space", "spacing"),
         ("colorize", "colour"), ("typeset", "type"), ("polish", "details")]

TEXTUAL = ("text/html", "text/css", "application/javascript", "text/javascript",
           "application/json", "image/svg+xml", "text/plain")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------- state
class Review:
    def __init__(self, variants: dict, question: str, surface: str):
        self.variants = variants          # id -> {"kind": file|url, "target": ...}
        self.question = question
        self.surface = surface
        self.notes: list[dict] = []
        self.decision: dict | None = None
        self.done = threading.Event()
        self.lock = threading.Lock()
        self.started = now()

    def add_note(self, rec: dict) -> dict:
        with self.lock:
            rec["n"] = len(self.notes) + 1
            rec["at"] = now()
            self.notes.append(rec)
            return rec

    def sha(self) -> str:
        h = hashlib.sha256()
        h.update((self.question + "\x1f" + self.surface).encode())
        for vid, v in sorted(self.variants.items()):
            h.update((vid + "\x1f" + v["kind"] + "\x1f" + str(v["target"])).encode())
            if v["kind"] == "file":
                try:
                    h.update(Path(v["target"]).read_bytes())
                except OSError:
                    h.update(b"missing")
        return h.hexdigest()[:16]


def parse_variant(spec: str) -> tuple[str, dict]:
    if "=" not in spec:
        raise SystemExit(f"--variant wants ID=target, got {spec!r}")
    vid, target = spec.split("=", 1)
    vid = re.sub(r"[^A-Za-z0-9_-]", "", vid.strip()) or "V"
    target = target.strip()
    if re.match(r"https?://", target):
        return vid, {"kind": "url", "target": target}
    p = Path(target)
    if not p.exists():
        raise SystemExit(f"{target} does not exist, and a variant that cannot be "
                         f"served is not a variant")
    return vid, {"kind": "file", "target": str(p.resolve())}


# ------------------------------------------------------------------ injection
INJECT = r"""
<script data-deluxui-review>
(() => {
  if (window.__uxReview) return;
  const VARIANT = "__VARIANT__";
  const CHIPS = __CHIPS__;
  const S = window.__uxReview = { on: true };

  const css = document.createElement('style');
  css.textContent = `
  .uxr-hi{position:fixed;pointer-events:none;z-index:2147483644;
    outline:2px solid #2f6fed;outline-offset:1px;background:rgba(47,111,237,.08)}
  .uxr-pin{position:absolute;z-index:2147483645;width:22px;height:22px;
    border-radius:999px;background:#b4451f;color:#fff;font:700 12px/22px system-ui;
    text-align:center;box-shadow:0 1px 6px rgba(0,0,0,.35);cursor:pointer}
  .uxr-box{position:fixed;z-index:2147483646;width:300px;background:#fff;color:#16181d;
    font:14px/1.5 system-ui,sans-serif;border:1px solid #d5d5d0;border-radius:10px;
    box-shadow:0 10px 34px rgba(0,0,0,.22);padding:12px}
  .uxr-box p{margin:0 0 8px;font:12px/1.4 ui-monospace,monospace;color:#5d6068;
    word-break:break-all}
  .uxr-box textarea{width:100%;min-height:86px;font:inherit;padding:8px;
    border:1px solid #cfcfca;border-radius:7px;resize:vertical}
  .uxr-chips{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
  .uxr-chips button{font:12px system-ui;padding:4px 8px;border-radius:999px;
    border:1px solid #dcdcd8;background:#f6f6f4;cursor:pointer;min-height:28px}
  .uxr-chips button[aria-pressed=true]{background:#2f6fed;color:#fff;border-color:#2f6fed}
  .uxr-row{display:flex;gap:8px;margin-top:8px}
  .uxr-row button{flex:1;min-height:40px;font:600 14px system-ui;border:0;
    border-radius:7px;cursor:pointer}
  .uxr-save{background:#2f6fed;color:#fff}.uxr-cancel{background:#ececea}
  .uxr-box :focus-visible,.uxr-chips :focus-visible{outline:3px solid #2f6fed;
    outline-offset:2px}
  @media (prefers-color-scheme:dark){
    .uxr-box{background:#1d1c19;color:#f3efe6;border-color:#3b382f}
    .uxr-box textarea{background:#26241f;color:#f3efe6;border-color:#4a453a}
    .uxr-chips button{background:#26241f;color:#f3efe6;border-color:#413d34}
    .uxr-cancel{background:#3a362e;color:#f3efe6}}`;
  document.documentElement.appendChild(css);

  const hi = document.createElement('div'); hi.className = 'uxr-hi';
  let box = null, armed = false;

  const ours = n => n && n.closest && (n.closest('.uxr-box') || n.classList
                 && (n.classList.contains('uxr-hi') || n.classList.contains('uxr-pin')));

  function selectorFor(el){
    if (el.id) return '#'+el.id;
    const t = el.getAttribute('data-testid')||el.getAttribute('data-test');
    if (t) return `[data-testid="${t}"]`;
    const parts=[]; let n=el;
    while(n && n.nodeType===1 && parts.length<4 && n!==document.body){
      let p=n.tagName.toLowerCase();
      const cls=(n.getAttribute('class')||'').trim().split(/\s+/)
        .filter(c=>c && !/^(uxr-|ng-|css-[0-9a-z]{4,})/.test(c)).slice(0,3);
      if(cls.length) p+='.'+cls.join('.');
      const sibs=n.parentElement?[...n.parentElement.children].filter(x=>x.tagName===n.tagName):[];
      if(sibs.length>1) p+=`:nth-of-type(${sibs.indexOf(n)+1})`;
      parts.unshift(p); n=n.parentElement;
    }
    return parts.join(' > ');
  }
  function describe(el){
    const c=getComputedStyle(el), r=el.getBoundingClientRect();
    return {variant:VARIANT, selector:selectorFor(el), tag:el.tagName.toLowerCase(),
      role:el.getAttribute('role')||null,
      element_text:(el.innerText||'').trim().replace(/\s+/g,' ').slice(0,140),
      box:{x:Math.round(r.x+scrollX),y:Math.round(r.y+scrollY),
           w:Math.round(r.width),h:Math.round(r.height)},
      computed:{fontSize:c.fontSize,fontWeight:c.fontWeight,fontFamily:c.fontFamily,
        lineHeight:c.lineHeight,color:c.color,background:c.backgroundColor,
        padding:c.padding,margin:c.margin,gap:c.gap,borderRadius:c.borderRadius,
        border:c.border,boxShadow:c.boxShadow==='none'?null:c.boxShadow.slice(0,160),
        display:c.display,width:c.width,height:c.height},
      viewport:{w:innerWidth,h:innerHeight,dpr:devicePixelRatio},
      url:location.href};
  }
  function pin(info, n){
    const d=document.createElement('div'); d.className='uxr-pin'; d.textContent=n;
    d.style.left=(info.box.x+info.box.w-11)+'px'; d.style.top=(info.box.y-11)+'px';
    d.title='note '+n; document.body.appendChild(d);
  }
  function open(info, ev){
    close();
    box=document.createElement('div'); box.className='uxr-box';
    box.innerHTML='<p></p><textarea placeholder="What is wrong with this? Your own words."></textarea>'
      +'<div class="uxr-chips">'+CHIPS.map(([id,l],i)=>
        `<button type="button" data-c="${id}" aria-pressed="${i===0}">${l}</button>`).join('')
      +'</div><div class="uxr-row"><button class="uxr-cancel">Cancel</button>'
      +'<button class="uxr-save">Add note</button></div>';
    box.querySelector('p').textContent=info.selector;
    const x=Math.min(innerWidth-316, Math.max(8,(ev?ev.clientX:20)-150));
    const y=Math.min(innerHeight-260, Math.max(8,(ev?ev.clientY:20)+14));
    box.style.left=x+'px'; box.style.top=y+'px';
    let chip='note';
    box.querySelectorAll('.uxr-chips button').forEach(b=>b.onclick=()=>{
      chip=b.dataset.c;
      box.querySelectorAll('.uxr-chips button').forEach(o=>
        o.setAttribute('aria-pressed', String(o===b)));
    });
    box.querySelector('.uxr-cancel').onclick=close;
    box.querySelector('.uxr-save').onclick=async ()=>{
      const text=box.querySelector('textarea').value.trim();
      if(!text){ box.querySelector('textarea').focus(); return; }
      const rec=Object.assign({},info,{chip, text});
      const r=await fetch('/api/note',{method:'POST',
        headers:{'Content-Type':'application/json'},body:JSON.stringify(rec)});
      const j=await r.json(); pin(info, j.n); close();
      try{ parent.postMessage({uxreview:'note', n:j.n, variant:VARIANT}, '*'); }catch(e){}
    };
    document.body.appendChild(box);
    box.querySelector('textarea').focus();
  }
  function close(){ if(box){box.remove(); box=null;} }

  addEventListener('mousemove', e=>{
    if(!S.on||box||ours(e.target)) return;
    const r=e.target.getBoundingClientRect();
    hi.style.left=r.x+'px'; hi.style.top=r.y+'px';
    hi.style.width=r.width+'px'; hi.style.height=r.height+'px';
    if(!hi.isConnected) document.body.appendChild(hi);
  }, true);
  addEventListener('click', e=>{
    // A plain click must still work -- reviewers navigate. Alt/Option-click, or
    // the review bar's "note mode", is what captures. A page you cannot use is a
    // page you cannot review.
    if(!S.on||ours(e.target)) return;
    if(!(e.altKey||armed)) return;
    e.preventDefault(); e.stopPropagation(); armed=false;
    try{ parent.postMessage({uxreview:'armed', on:false}, '*'); }catch(err){}
    open(describe(e.target), e);
  }, true);
  addEventListener('keydown', e=>{ if(e.key==='Escape') close(); }, true);
  addEventListener('message', e=>{
    if(e.data && e.data.uxreview==='arm'){ armed=!!e.data.on; }
  });
})();
</script>
"""


def inject_into(body: bytes, variant: str) -> bytes:
    js = INJECT.replace("__VARIANT__", variant).replace("__CHIPS__", json.dumps(CHIPS))
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        return body
    low = text.lower()
    i = low.rfind("</body>")
    if i == -1:
        i = low.rfind("</html>")
    if i == -1:
        return (text + js).encode()
    return (text[:i] + js + text[i:]).encode()


# --------------------------------------------------------------------- page
def theme() -> dict:
    c = ux_image.load_contract(None)
    return {"canvas": c.roles["canvas"], "surface": c.roles["surface"],
            "ink": c.roles["ink"], "muted": c.roles["muted"],
            "accent": c.roles["interactive"], "danger": c.roles["danger"],
            "display": c.families["display"], "body": c.families["body"],
            "mono": c.families["mono"], "r_ctl": c.r_control, "r_card": c.r_card}


CSS = """
:root{--canvas:%(canvas)s;--surface:%(surface)s;--ink:%(ink)s;--muted:%(muted)s;
  --accent:%(accent)s;--danger:%(danger)s;
  --line:color-mix(in oklab,var(--ink) 16%%,var(--canvas))}
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:%(body)s;
  font-size:17px;line-height:1.5}
header{padding:18px 20px 12px;border-bottom:1px solid var(--line);
  position:sticky;top:0;background:var(--canvas);z-index:5}
h1{font-family:%(display)s;font-size:clamp(22px,2.4vw,29px);margin:0 0 4px;
  font-weight:650;text-wrap:balance;max-width:40ch}
.sub{margin:0;color:var(--muted);max-width:74ch;text-wrap:pretty}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
.bar label{font:13px %(mono)s;color:var(--muted)}
.seg{display:flex;border:1px solid var(--line);border-radius:%(r_ctl)spx;overflow:hidden}
.seg button{font:13px %(mono)s;padding:8px 11px;min-height:40px;border:0;
  background:var(--surface);color:var(--ink);cursor:pointer}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff}
.tog{font:600 14px system-ui;padding:9px 14px;min-height:44px;border-radius:%(r_ctl)spx;
  border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.tog[aria-pressed=true]{background:var(--accent);color:#fff;border-color:var(--accent)}
main{display:grid;grid-template-columns:1fr 340px;gap:0;align-items:start}
.frames{display:flex;gap:16px;padding:16px 20px;overflow-x:auto;align-items:flex-start}
.vwrap{flex:0 0 auto;display:flex;flex-direction:column;gap:6px}
.vwrap h2{font-family:%(display)s;font-size:20px;margin:0;font-weight:650}
.vwrap .t{font:12px %(mono)s;color:var(--muted);margin:0 0 2px;word-break:break-all;
  max-width:100%%}
iframe{border:1px solid var(--line);border-radius:%(r_card)spx;background:#fff;
  height:78vh;width:768px;max-width:100%%;display:block}
aside{border-left:1px solid var(--line);padding:16px;position:sticky;top:120px;
  height:calc(100vh - 140px);overflow:auto}
aside h2{font-family:%(display)s;font-size:20px;margin:0 0 4px;font-weight:650}
.note{border:1px solid var(--line);border-radius:%(r_ctl)spx;padding:10px 12px;
  margin:10px 0;background:var(--surface)}
.note .m{font:12px %(mono)s;color:var(--muted);display:flex;gap:8px;
  justify-content:space-between}
.note .s{font:12px %(mono)s;color:var(--muted);word-break:break-all;margin:3px 0 6px}
.note p{margin:0;text-wrap:pretty}
.empty{color:var(--muted);text-wrap:pretty}
form{border-top:1px solid var(--line);margin-top:16px;padding-top:12px}
fieldset{border:0;padding:0;margin:0 0 10px}
legend{font-family:%(display)s;font-size:20px;font-weight:650;padding:0;margin:0 0 6px}
.opt{display:flex;gap:9px;align-items:flex-start;padding:9px 10px;min-height:44px;
  border:1px solid var(--line);border-radius:%(r_ctl)spx;margin:0 0 6px;cursor:pointer;
  background:var(--surface)}
.opt input{width:20px;height:20px;margin:2px 0 0;accent-color:var(--accent)}
.opt:has(input:checked){background:color-mix(in oklab,var(--accent) 14%%,var(--surface))}
.opt span.h{font-weight:600;display:block}
.opt span.d{font-size:14px;color:var(--muted);display:block;text-wrap:pretty}
label.f{display:block;font-weight:600;margin:12px 0 4px}
input[type=text],textarea{width:100%%;font:inherit;padding:10px 12px;min-height:46px;
  border:1px solid color-mix(in oklab,var(--ink) 32%%,var(--canvas));
  border-radius:%(r_ctl)spx;background:var(--surface);color:var(--ink)}
textarea{min-height:92px;resize:vertical}
button.send{width:100%%;margin-top:12px;font:650 15px system-ui;min-height:48px;
  border:0;border-radius:%(r_ctl)spx;background:var(--accent);color:#fff;cursor:pointer}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.err{background:color-mix(in oklab,var(--danger) 12%%,var(--canvas));
  border:1px solid var(--danger);border-radius:%(r_ctl)spx;padding:10px 12px;margin:10px 0}
.err ul{margin:4px 0 0;padding-left:18px}
@media (max-width:1100px){main{grid-template-columns:1fr}
  aside{border-left:0;border-top:1px solid var(--line);position:static;height:auto}}
@media (prefers-color-scheme:dark){
  :root{--canvas:#14120e;--surface:#1e1b16;--ink:#f4f0e7;
    --muted:color-mix(in oklab,#f4f0e7 72%%,#14120e);
    --accent:color-mix(in oklab,%(accent)s 78%%,#ffffff);
    --line:color-mix(in oklab,#f4f0e7 22%%,#14120e)}
  button.send,.seg button[aria-pressed=true],.tog[aria-pressed=true]{color:#14120e}}
"""

WIDTHS = [("320", 320), ("390", 390), ("768", 768), ("1024", 1024), ("full", 0)]


def page(rv: Review, th: dict, errors=None, form=None) -> str:
    errors, form = errors or [], form or {}
    frames = []
    for vid, v in rv.variants.items():
        label = v["target"] if v["kind"] == "url" else Path(v["target"]).name
        frames.append(
            f'<div class="vwrap" data-v="{html.escape(vid)}">'
            f'<h2>{html.escape(vid)}</h2>'
            f'<p class="t">{html.escape(str(label))}</p>'
            f'<iframe title="Variant {html.escape(vid)}" src="/v/{html.escape(vid)}/"'
            f'></iframe></div>')
    opts = [("accept:" + vid, f"Accept {vid}", "This is the one to build on.")
            for vid in rv.variants]
    opts += [("combine", "Combine", "Take parts of more than one — say which, below."),
             ("changes", "Request changes",
              "Not yet. The notes are the work list; nothing is approved."),
             ("reject", "Reject", "None of these. Say what is wrong with the direction.")]
    radios = "".join(
        f'<label class="opt"><input type="radio" name="choice" value="{html.escape(v)}"'
        f'{" checked" if form.get("choice") == v else ""}>'
        f'<span><span class="h">{html.escape(h_)}</span>'
        f'<span class="d">{html.escape(d)}</span></span></label>' for v, h_, d in opts)
    errblock = ""
    if errors:
        errblock = ('<div class="err" role="alert" tabindex="-1" id="errors">'
                    '<strong>Not recorded</strong><ul>'
                    + "".join(f"<li>{html.escape(e)}</li>" for e in errors) + "</ul></div>")
    segs = "".join(
        f'<button type="button" data-w="{w}" aria-pressed="{str(w == 1024).lower()}">'
        f'{html.escape(lbl)}</button>' for lbl, w in WIDTHS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(rv.question)}</title><style>{CSS % th}</style></head><body>
<header>
  <h1>{html.escape(rv.question)}</h1>
  <p class="sub">{html.escape(rv.surface or '')} — this is the running interface, not a
  picture of it. <strong>Alt-click</strong> anything inside a frame to leave a note about
  it, or press <em>Note mode</em> and click.</p>
  <div class="bar">
    <label for="segw">Width</label>
    <div class="seg" id="segw">{segs}</div>
    <button class="tog" id="armbtn" type="button" aria-pressed="false">Note mode</button>
    <button class="tog" id="darkbtn" type="button" aria-pressed="false">Try dark</button>
    <span class="sub" id="count" style="font:13px {th['mono']}"></span>
  </div>
</header>
<main>
  <div class="frames">{''.join(frames)}</div>
  <aside>
    <h2>Notes</h2>
    <div id="notes"><p class="empty">Nothing yet. Alt-click an element in either
      frame and say what is wrong with it, in your own words.</p></div>
    <form method="post" action="/api/decide" id="decide">
      {errblock}
      <fieldset><legend>Decide</legend>{radios}</fieldset>
      <label class="f" for="who">Who is deciding
        <span class="d">A person's name. An agent's name is refused.</span></label>
      <input type="text" id="who" name="who" autocomplete="name"
             value="{html.escape(form.get('who',''))}">
      <label class="f" for="why">Why</label>
      <textarea id="why" name="why">{html.escape(form.get('why',''))}</textarea>
      <button class="send" type="submit">Record this decision</button>
    </form>
  </aside>
</main>
<script>
const frames = () => [...document.querySelectorAll('iframe')];
// Two variants side by side is the whole point, so the opening width is the
// widest one that actually fits both. Defaulting to 1024 pushed B off-screen and
// turned an A/B comparison into a horizontal scroll.
function fit() {{
  const n = frames().length || 1;
  const room = (document.querySelector('.frames').clientWidth - 16 * (n - 1)) / n;
  const pick = [1024, 768, 390, 320].find(w => w <= room) || 320;
  const b = document.querySelector(`#segw button[data-w="${{pick}}"]`)
        || document.querySelector('#segw button[data-w="320"]');
  if (b) b.click();
}}
document.querySelectorAll('#segw button').forEach(b => b.onclick = () => {{
  document.querySelectorAll('#segw button').forEach(o =>
    o.setAttribute('aria-pressed', String(o === b)));
  const w = +b.dataset.w;
  frames().forEach(f => f.style.width = w ? w + 'px' : '100%');
}});
const arm = document.getElementById('armbtn');
arm.onclick = () => {{
  const on = arm.getAttribute('aria-pressed') !== 'true';
  arm.setAttribute('aria-pressed', String(on));
  frames().forEach(f => f.contentWindow.postMessage({{uxreview:'arm', on}}, '*'));
}};
// Adds the two conventions an app is most likely to honour. It is a probe, not a
// guarantee: if neither moves, this product does not implement dark that way.
const dk = document.getElementById('darkbtn');
dk.onclick = () => {{
  const on = dk.getAttribute('aria-pressed') !== 'true';
  dk.setAttribute('aria-pressed', String(on));
  frames().forEach(f => {{
    try {{
      const h = f.contentDocument.documentElement;
      h.classList.toggle('dark', on);
      h.setAttribute('data-theme', on ? 'dark' : 'light');
      h.style.colorScheme = on ? 'dark' : 'light';
    }} catch (e) {{}}
  }});
}};
addEventListener('message', e => {{ if (e.data && e.data.uxreview === 'note') refresh(); }});
async function refresh() {{
  const r = await fetch('/api/state'); const s = await r.json();
  const box = document.getElementById('notes');
  document.getElementById('count').textContent =
    s.notes.length ? s.notes.length + ' note' + (s.notes.length === 1 ? '' : 's') : '';
  if (!s.notes.length) return;
  box.innerHTML = s.notes.map(n => `<div class="note">
    <div class="m"><span>${{n.n}} · ${{n.variant}}</span><span>${{n.chip}}</span></div>
    <div class="s">${{n.selector}}</div><p></p></div>`).join('');
  [...box.querySelectorAll('.note p')].forEach((p, i) => p.textContent = s.notes[i].text);
}}
setInterval(refresh, 1500); refresh(); fit(); addEventListener('resize', fit);
const e = document.getElementById('errors'); if (e) e.focus();
</script></body></html>"""


DONE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Recorded</title>
<style>%(css)s</style></head><body><div style="padding:80px 20px;text-align:center">
<h1>Recorded</h1><p class="sub" style="margin:0 auto">%(what)s</p>
<p class="sub" style="margin:8px auto"><code>%(file)s</code></p>
<p class="sub" style="margin:8px auto">%(notes)s</p></div></body></html>"""


# ------------------------------------------------------------------ recording
def _next(dirp: Path, prefix: str) -> str:
    dirp.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in dirp.glob(f"{prefix}-*.yaml"):
        m = re.match(rf"{prefix}-(\d+)", f.stem)
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}-{n + 1:03d}"


def write_note(rec: dict) -> Path:
    rid = _next(REQUESTS, "REQ")
    out = dict(rec)
    out["id"] = rid
    out["source"] = "review"
    out["action"] = rec.get("chip") or "note"
    out["recorded_by"] = ("deluxui/scripts/ux_review.py -- a person wrote this while "
                          "looking at the running interface")
    p = REQUESTS / f"{rid}.yaml"
    p.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=92))
    return p


def validate(form: dict, rv: Review) -> list:
    errs = []
    choice = (form.get("choice") or "").strip()
    who = (form.get("who") or "").strip()
    why = (form.get("why") or "").strip()
    valid = {f"accept:{v}" for v in rv.variants} | {"combine", "changes", "reject"}
    if choice not in valid:
        errs.append("Pick an outcome. Nothing is recorded without one.")
    if not who:
        errs.append("Say who is deciding. An approval with no author cannot be "
                    "weighed later and cannot gate anything.")
    elif SELF.search(who):
        errs.append(f"“{who}” names the party that built these. The agent "
                    f"that produced a variant cannot also be the authority accepting "
                    f"it.")
    if choice == "changes":
        if not rv.notes and len(why) < MIN_REASON:
            errs.append("Requesting changes with no notes and no reason leaves nothing "
                        "to act on. Note the elements, or say what to change.")
    elif len(why) < MIN_REASON:
        errs.append(f"The reason is {len(why)} characters; {MIN_REASON} is the minimum. "
                    f"It is what the next person reads when they are about to undo this.")
    return errs


def record(form: dict, rv: Review, notes_written: list) -> Path:
    did = _next(DECISIONS, "DEC")
    choice = form["choice"].strip()
    rec = {
        "id": did,
        "question": rv.question,
        "surface": rv.surface,
        "chosen": choice.split(":", 1)[1] if choice.startswith("accept:") else choice,
        "outcome": choice,
        "approves_a_build": choice.startswith("accept:") or choice == "combine",
        "who": form["who"].strip(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "recorded_at": now(),
        "rationale": form.get("why", "").strip(),
        "options_sha": rv.sha(),
        "reviewed": [{"id": vid, "kind": v["kind"], "target": v["target"]}
                     for vid, v in rv.variants.items()],
        "shown": [{"id": vid, "title": f"{vid} ({v['kind']})", "image": None,
                   "image_sha": None} for vid, v in rv.variants.items()],
        "notes": [{"id": p.stem, "variant": n["variant"], "chip": n.get("chip"),
                   "selector": n["selector"], "text": n["text"]}
                  for p, n in notes_written],
        "source": "ux_review.py (live A/B review of the running interface)",
        "recorded_by": "deluxui/scripts/ux_review.py (served page, human submitted)",
    }
    DECISIONS.mkdir(parents=True, exist_ok=True)
    p = DECISIONS / f"{did}.yaml"
    p.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=92))
    return p


# --------------------------------------------------------------------- server
def handler_for(rv: Review, th: dict, notes_written: list, echo):
    class H(BaseHTTPRequestHandler):
        server_version = "deluxui-review"
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, body: bytes, ctype="text/html; charset=utf-8", code=200,
                  extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        # --- variant hosting ------------------------------------------------
        def _variant_of_referer(self):
            ref = self.headers.get("Referer") or ""
            m = re.search(r"/v/([A-Za-z0-9_-]+)/", ref)
            return m.group(1) if m else None

        def _serve_file(self, vid, rest):
            base = Path(rv.variants[vid]["target"])
            target = base if not rest else (base.parent / rest)
            try:
                target = target.resolve()
                if not str(target).startswith(str(base.parent.resolve())):
                    return self._send(b"outside the variant", "text/plain", 403)
                data = target.read_bytes()
            except OSError:
                return self._send(b"not found", "text/plain", 404)
            ctype = _guess(target.name)
            if ctype.startswith("text/html"):
                data = inject_into(data, vid)
            self._send(data, ctype)

        def _proxy(self, vid, rest, query):
            origin = rv.variants[vid]["target"]
            if rest:
                base = origin.split("?")[0].rstrip("/")
                # A path from the app's own root, not appended to the route.
                root = "/".join(base.split("/")[:3])
                url = root + "/" + rest.lstrip("/")
            else:
                url = origin
            if query:
                url += ("&" if "?" in url else "?") + query
            req = urllib.request.Request(url, headers={
                "User-Agent": self.headers.get("User-Agent", "deluxui"),
                "Accept": self.headers.get("Accept", "*/*")})
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = r.read()
                    ctype = r.headers.get("Content-Type", "application/octet-stream")
            except urllib.error.HTTPError as e:
                data, ctype = e.read(), e.headers.get("Content-Type", "text/plain")
                if ctype.startswith("text/html"):
                    data = inject_into(data, vid)
                return self._send(data, ctype, e.code)
            except (urllib.error.URLError, OSError) as e:
                return self._send(
                    (f"<!doctype html><meta charset=utf-8>"
                     f"<p style='font:16px system-ui;padding:24px'>deluxui could not "
                     f"reach <code>{html.escape(url)}</code>: {html.escape(str(e))}."
                     f"<br>Start the dev server, then reload.</p>").encode(),
                    "text/html; charset=utf-8", 502)
            if ctype.split(";")[0].strip() == "text/html":
                data = inject_into(data, vid)
            # Frame-blocking headers are dropped on the way through: this page is
            # the reviewer's own browser looking at their own app, and a dev
            # server's clickjacking defence is not about that.
            self._send(data, ctype)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/":
                return self._send(page(rv, th).encode())
            if u.path == "/api/state":
                with rv.lock:
                    body = json.dumps({"notes": rv.notes,
                                       "decided": bool(rv.decision)}).encode()
                return self._send(body, "application/json")
            m = re.match(r"^/v/([A-Za-z0-9_-]+)/?(.*)$", u.path)
            if m and m.group(1) in rv.variants:
                vid, rest = m.group(1), m.group(2)
                if rv.variants[vid]["kind"] == "file":
                    return self._serve_file(vid, rest)
                return self._proxy(vid, rest, u.query)
            # Anything else is an asset the framed app asked for by absolute path.
            vid = self._variant_of_referer()
            if vid and vid in rv.variants:
                if rv.variants[vid]["kind"] == "url":
                    return self._proxy(vid, u.path.lstrip("/"), u.query)
                return self._serve_file(vid, u.path.lstrip("/"))
            return self._send(b"not found", "text/plain", 404)

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(min(n, 500_000)).decode("utf-8", "replace")
            if u.path == "/api/note":
                try:
                    rec = json.loads(raw)
                except ValueError:
                    return self._send(b'{"error":"bad json"}', "application/json", 400)
                rec = rv.add_note(rec)
                p = write_note(rec)
                notes_written.append((p, rec))
                echo(f"  {p.stem}  {rec['variant']}/{rec.get('chip','note'):<9} "
                     f"{rec['selector'][:44]}\n      “{rec['text'][:150]}”\n")
                return self._send(json.dumps({"n": rec["n"], "id": p.stem}).encode(),
                                  "application/json")
            if u.path == "/api/decide":
                form = {k: v[0] for k, v in
                        urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
                errs = validate(form, rv)
                if errs:
                    return self._send(page(rv, th, errs, form).encode(), code=422)
                p = record(form, rv, notes_written)
                rv.decision = {"file": str(p), "outcome": form["choice"]}
                body = DONE % {
                    "css": CSS % th,
                    "what": html.escape(f"{form['choice']} — recorded as {p.stem}"),
                    "file": html.escape(str(p)),
                    "notes": html.escape(f"{len(notes_written)} element note(s) written "
                                         f"to .deluxui/requests/")}
                self._send(body.encode())
                threading.Thread(target=lambda: (time.sleep(0.4), rv.done.set()),
                                 daemon=True).start()
                return
            return self._send(b"not found", "text/plain", 404)
    return H


def _guess(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return {"html": "text/html; charset=utf-8", "htm": "text/html; charset=utf-8",
            "css": "text/css; charset=utf-8", "js": "application/javascript",
            "mjs": "application/javascript", "json": "application/json",
            "svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg",
            "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif",
            "woff2": "font/woff2", "woff": "font/woff", "ttf": "font/ttf",
            "ico": "image/x-icon", "map": "application/json",
            "txt": "text/plain; charset=utf-8"}.get(ext, "application/octet-stream")


def free_port(host: str, want: int) -> int:
    for p in [want] + list(range(want + 1, want + 40)):
        with socket.socket() as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise SystemExit("no free port in range")


# ------------------------------------------------------------------------ CLI
def cmd_serve(a) -> int:
    variants = {}
    for spec in a.variant:
        vid, v = parse_variant(spec)
        variants[vid] = v
    if len(variants) < 1:
        sys.stderr.write("give at least one --variant ID=target\n")
        return 2
    rv = Review(variants, a.question or "Which of these should we build on?",
                a.surface or "")
    notes_written = []
    echo = (lambda s: sys.stderr.write(s)) if not a.quiet else (lambda s: None)
    port = free_port(a.host, a.port)
    srv = ThreadingHTTPServer((a.host, port), handler_for(rv, theme(), notes_written,
                                                          echo))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://{a.host}:{port}/"
    sys.stderr.write(
        f"\n  {rv.question}\n\n  Open and review:  {url}\n\n"
        + "".join(f"    {vid}  {v['target']}\n" for vid, v in variants.items())
        + f"\n  This serves the real interface, not a picture of it. Alt-click any\n"
          f"  element in either frame to leave a note in your own words; the note\n"
          f"  lands in .deluxui/requests/ with the element it is about.\n"
          f"  Waiting up to {a.timeout}s. Notes appear here as they are written.\n\n")
    if a.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    ok = rv.done.wait(timeout=a.timeout)
    srv.shutdown()
    if not ok or not rv.decision:
        if notes_written:
            sys.stderr.write(
                f"\nNo decision was recorded, but {len(notes_written)} note(s) were. "
                f"Those are real work items; the approval is still NOT_RUN.\n")
            print("\n".join(str(p) for p, _ in notes_written))
            return 0
        sys.stderr.write(
            "\nNobody reviewed it, so nothing was recorded. NOT_RUN -- an unreviewed "
            "screen is not an approved one, and no default was invented.\n")
        return 3
    rec = yaml.safe_load(Path(rv.decision["file"]).read_text())
    sys.stderr.write(
        f"\nRecorded {rv.decision['file']}\n"
        f"  outcome:  {rec['outcome']}"
        f"{'  (an approval the phase gate accepts)' if rec['approves_a_build'] else '  (NOT an approval)'}\n"
        f"  who:      {rec['who']} on {rec['date']}\n"
        f"  why:      {rec['rationale'][:160]}\n"
        f"  notes:    {len(notes_written)} element note(s) in .deluxui/requests/\n")
    print(rv.decision["file"])
    return 0


def cmd_notes(a) -> int:
    got = sorted(REQUESTS.glob("REQ-*.yaml"))
    if not got:
        sys.stderr.write("No notes recorded.\n")
        return 0
    for f in got:
        d = yaml.safe_load(f.read_text()) or {}
        if a.source and d.get("source") != a.source:
            continue
        sys.stderr.write(f"\n{d.get('id')}  [{d.get('action')}]  "
                         f"{d.get('variant', '-')}  {str(d.get('selector'))[:60]}\n"
                         f"    “{d.get('text') or d.get('note') or ''}”\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("serve")
    s.add_argument("--variant", action="append", default=[], metavar="ID=TARGET",
                   help="a URL on a running app, or an HTML file. Repeatable.")
    s.add_argument("--question")
    s.add_argument("--surface", default="")
    s.add_argument("--port", type=int, default=8788)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--timeout", type=int, default=3600)
    s.add_argument("--open", action="store_true")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(fn=cmd_serve)
    n = sub.add_parser("notes")
    n.add_argument("--source", help="only notes from one source, e.g. review")
    n.set_defaults(fn=cmd_notes)
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 1
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
