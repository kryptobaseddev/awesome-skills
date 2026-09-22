#!/usr/bin/env python3
"""A live A/B review page: the real UI, side by side, with the human's words on it.

The comp round (`ux_question.py`) decides a direction from drawings. This decides
a *build* from the thing itself. Two variants of a real interface -- two routes on
a running dev server, two HTML files, or one of each -- are hosted side by side in
a page the reviewer opens, at whichever viewport width they want to judge it at.

Then the part that usually gets lost: they click any element inside either variant
and type, in their own words, what is wrong with it. That note is captured with
the element it is about -- selector, text, computed type, colour, spacing, radius,
shadow, box, viewport -- and written to `.deuxui/requests/REQ-NNN.yaml`, which is
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
import ux_ledger                                                   # noqa: E402
import uxconfig                                                    # noqa: E402
import ux_question                                                 # noqa: E402

DECISIONS = Path(".deuxui/decisions")
REQUESTS = Path(".deuxui/requests")
# A floor, not a bar. Forty characters was a length test standing in for a
# substance test, and it fails in both directions: forty characters of "aaaa"
# passes, and "It loses the price on a phone" -- which is the whole truth -- does
# not. Twelve is low enough that anything with a subject and a verb clears it,
# and high enough to exclude "ok".
#
# What actually has to be refused is a NON-reason, and that is detectable by what
# it says rather than how long it is.
MIN_REASON = 12
EMPTY_REASON = re.compile(
    r"^(?:looks?\s*good|lgtm|good|fine|ok(?:ay)?|yes|yep|nice|better|best|great|"
    r"perfect|love it|ship it|sure|\\+1|done|approved|agreed|this one|the first|"
    r"the second|no comment|n/?a)[\s.!]*$", re.I)
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
        self.seq = 0
        # The highest REQ number already on disk, fixed once at start. Deriving
        # each filename from the next free slot meant deleting REQ-002 and adding
        # another note produced a second, unrelated REQ-002 -- one id, two
        # different work items, and the agent's log showing it twice.
        self.base = _highest(REQUESTS, "REQ")
        self.resume()

    def resume(self) -> None:
        """Pick up notes this project already has for these variants.

        A review is not one sitting. Restarting the server used to empty the
        panel and drop every pin while the work items sat on disk, which reads as
        "your notes are gone" -- the one thing that stops somebody leaving more."""
        mine = {v for v in self.variants}
        for f in sorted(REQUESTS.glob("REQ-*.yaml")) if REQUESTS.exists() else []:
            try:
                d = yaml.safe_load(f.read_text()) or {}
            except (OSError, yaml.YAMLError):
                continue
            if d.get("source") != "review" or d.get("variant") not in mine:
                continue
            d["_file"] = str(f)
            d["req"] = f.stem
            d["n"] = int(d.get("n") or (self.seq + 1))
            self.seq = max(self.seq, d["n"])
            self.notes.append(d)
        self.notes.sort(key=lambda x: x.get("n", 0))
        self.decision: dict | None = None
        self.done = threading.Event()
        self.lock = threading.Lock()
        self.started = now()

    def add_note(self, rec: dict) -> dict:
        with self.lock:
            # Numbers are never reused. A pin that changes meaning because an
            # earlier note was deleted is worse than a gap in the sequence.
            self.seq += 1
            rec["n"] = self.seq
            rec["at"] = now()
            self.notes.append(rec)
            return rec

    def find(self, n: int) -> dict | None:
        with self.lock:
            return next((x for x in self.notes if x.get("n") == n), None)

    def update_note(self, n: int, text: str, chip: str) -> dict | None:
        with self.lock:
            rec = next((x for x in self.notes if x.get("n") == n), None)
            if rec is None:
                return None
            rec["text"] = text
            if chip:
                rec["chip"] = chip
            rec["edited_at"] = now()
            rec["revision"] = int(rec.get("revision") or 0) + 1
            return rec

    def remove_note(self, n: int) -> dict | None:
        with self.lock:
            rec = next((x for x in self.notes if x.get("n") == n), None)
            if rec is None:
                return None
            self.notes = [x for x in self.notes if x.get("n") != n]
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
<script data-deuxui-review>
(() => {
  if (window.__uxReview) return;
  const VARIANT = "__VARIANT__";
  const CHIPS = {chips};
const REQS = {reqs_json};
const META = {meta};
  // `armed` is sticky. It used to clear itself after one capture while the
  // parent's button stayed pressed, so note mode looked on, was off, and the
  // second note could not be left at all.
  const S = window.__uxReview = { armed: false, pins: new Map(), version: 2 };

  const css = document.createElement('style');
  css.textContent = `
  .uxr-hi{position:fixed;pointer-events:none;z-index:2147483644;
    outline:2px solid #2f6fed;outline-offset:1px;background:rgba(47,111,237,.08)}
  .uxr-pin{position:absolute;z-index:2147483645;min-width:22px;height:22px;
    padding:0 6px;border-radius:999px;background:#b4451f;color:#fff;
    font:700 12px/22px system-ui;text-align:center;cursor:pointer;border:0;
    box-shadow:0 1px 6px rgba(0,0,0,.35)}
  .uxr-pin:focus-visible{outline:3px solid #2f6fed;outline-offset:2px}
  .uxr-flash{animation:uxrflash 1.2s ease-out 2}
  @keyframes uxrflash{0%,100%{box-shadow:0 0 0 0 rgba(180,69,31,0)}
    40%{box-shadow:0 0 0 6px rgba(180,69,31,.55)}}
  @media (prefers-reduced-motion:reduce){.uxr-flash{animation:none;
    outline:3px solid #b4451f;outline-offset:2px}}
  .uxr-box{position:fixed;z-index:2147483646;width:310px;background:#fff;color:#16181d;
    font:14px/1.5 system-ui,sans-serif;border:1px solid #d5d5d0;border-radius:10px;
    box-shadow:0 10px 34px rgba(0,0,0,.22);padding:12px}
  .uxr-box p{margin:0 0 8px;font:12px/1.4 ui-monospace,monospace;color:#5d6068;
    word-break:break-all}
  .uxr-box textarea{width:100%;min-height:88px;font:inherit;padding:8px;
    border:1px solid #cfcfca;border-radius:7px;resize:vertical}
  .uxr-chips{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
  .uxr-chips button{font:12px system-ui;padding:4px 8px;border-radius:999px;
    border:1px solid #dcdcd8;background:#f6f6f4;cursor:pointer;min-height:30px}
  .uxr-chips button[aria-pressed=true]{background:#2f6fed;color:#fff;border-color:#2f6fed}
  .uxr-row{display:flex;gap:8px;margin-top:8px}
  .uxr-row button{flex:1;min-height:40px;font:600 14px system-ui;border:0;
    border-radius:7px;cursor:pointer}
  .uxr-save{background:#2f6fed;color:#fff}.uxr-cancel{background:#ececea}
  .uxr-del{background:#fbeae8;color:#a8231b;flex:0 0 auto;padding:0 12px}
  .uxr-box :focus-visible,.uxr-chips :focus-visible{outline:3px solid #2f6fed;
    outline-offset:2px}
  @media (prefers-color-scheme:dark){
    .uxr-box{background:#1d1c19;color:#f3efe6;border-color:#3b382f}
    .uxr-box textarea{background:#26241f;color:#f3efe6;border-color:#4a453a}
    .uxr-chips button{background:#26241f;color:#f3efe6;border-color:#413d34}
    .uxr-cancel{background:#3a362e;color:#f3efe6}
    .uxr-del{background:#3a221f;color:#ffb4ab}}`;
  document.documentElement.appendChild(css);

  const hi = document.createElement('div'); hi.className = 'uxr-hi';
  let box = null;

  const ours = n => n && n.closest && (n.closest('.uxr-box') || (n.classList &&
                 (n.classList.contains('uxr-hi') || n.classList.contains('uxr-pin'))));
  const tell = (m) => { try { parent.postMessage(Object.assign({uxreview:1}, m), '*'); }
                        catch (e) {} };

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

  function findEl(info){
    // The element a note is about, after a re-render. The selector first, the
    // recorded box as a fallback -- a note pinned to something that has moved is
    // still a note about that thing.
    try { const el = document.querySelector(info.selector); if (el) return el; }
    catch (e) {}
    if (!info.box) return null;
    const el = document.elementFromPoint(
      Math.min(innerWidth-2, Math.max(1, info.box.x - scrollX + info.box.w/2)),
      Math.min(innerHeight-2, Math.max(1, info.box.y - scrollY + info.box.h/2)));
    return el && !ours(el) ? el : null;
  }

  function pin(n, info){
    let d = S.pins.get(n);
    if (!d) {
      d = document.createElement('button');
      d.type = 'button'; d.className = 'uxr-pin';
      d.onclick = (ev) => { ev.preventDefault(); ev.stopPropagation();
                            tell({kind:'pin', n}); };
      document.body.appendChild(d);
      S.pins.set(n, d);
    }
    d.textContent = n;
    d.title = 'Note ' + n + ' — click to edit it';
    d.setAttribute('aria-label', 'Note ' + n + ' on ' + (info.element_text || info.tag));
    d.dataset.sel = info.selector;
    d.style.left = (info.box.x + info.box.w - 11) + 'px';
    d.style.top  = (info.box.y - 11) + 'px';
  }
  function unpin(n){ const d = S.pins.get(n); if (d) { d.remove(); S.pins.delete(n); } }

  function open(info, ev, existing){
    close();
    box = document.createElement('div'); box.className = 'uxr-box';
    box.innerHTML = '<p></p><textarea placeholder="What is wrong with this? Your own words."></textarea>'
      + '<div class="uxr-chips">' + CHIPS.map(([id,l]) =>
          `<button type="button" data-c="${id}" aria-pressed="false">${l}</button>`).join('')
      + '</div><div class="uxr-row">'
      + (existing ? '<button class="uxr-del" type="button">Delete</button>' : '')
      + '<button class="uxr-cancel" type="button">Cancel</button>'
      + `<button class="uxr-save" type="button">${existing ? 'Save note' : 'Add note'}</button></div>`;
    box.querySelector('p').textContent = info.selector;
    const ta = box.querySelector('textarea');
    let chip = (existing && existing.chip) || 'note';
    if (existing) ta.value = existing.text || '';
    const setChip = (c) => { chip = c; box.querySelectorAll('.uxr-chips button').forEach(o =>
      o.setAttribute('aria-pressed', String(o.dataset.c === c))); };
    setChip(chip);
    box.querySelectorAll('.uxr-chips button').forEach(b =>
      b.onclick = () => setChip(b.dataset.c));

    const r = (ev && ev.clientX != null)
      ? {x: ev.clientX, y: ev.clientY}
      : {x: (info.box.x - scrollX) + info.box.w, y: (info.box.y - scrollY)};
    box.style.left = Math.min(innerWidth - 322, Math.max(8, r.x - 150)) + 'px';
    box.style.top  = Math.min(innerHeight - 280, Math.max(8, r.y + 14)) + 'px';

    box.querySelector('.uxr-cancel').onclick = close;
    if (existing) box.querySelector('.uxr-del').onclick = async () => {
      await fetch('/api/note/' + existing.n, {method: 'DELETE'});
      unpin(existing.n); close(); tell({kind:'note'});
    };
    box.querySelector('.uxr-save').onclick = async () => {
      const text = ta.value.trim();
      if (!text) { ta.focus(); return; }
      if (existing) {
        await fetch('/api/note/' + existing.n, {method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({text, chip})});
        pin(existing.n, Object.assign({}, existing, info));
      } else {
        const res = await fetch('/api/note', {method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(Object.assign({}, info, {chip, text}))});
        const j = await res.json();
        pin(j.n, info);
      }
      close(); tell({kind:'note'});
      // Note mode stays on. A reviewer leaving one note is usually leaving five.
    };
    document.body.appendChild(box);
    ta.focus();
  }
  function close(){ if (box) { box.remove(); box = null; } }

  addEventListener('mousemove', e => {
    if (!S.armed || box || ours(e.target)) { if (!S.armed) hi.remove(); return; }
    const r = e.target.getBoundingClientRect();
    hi.style.left = r.x + 'px'; hi.style.top = r.y + 'px';
    hi.style.width = r.width + 'px'; hi.style.height = r.height + 'px';
    if (!hi.isConnected) document.body.appendChild(hi);
  }, true);

  addEventListener('click', e => {
    // A plain click must still work: reviewers navigate, open dialogs, type in
    // forms. Alt-click captures anywhere; note mode captures on a plain click.
    if (ours(e.target)) return;
    if (!(e.altKey || S.armed)) return;
    e.preventDefault(); e.stopPropagation();
    open(describe(e.target), e, null);
  }, true);

  addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      if (box) { close(); return; }
      if (S.armed) { S.armed = false; hi.remove(); tell({kind:'armed', on:false}); }
    }
  }, true);

  addEventListener('message', e => {
    const d = e.data || {};
    if (!d.uxreview && d.uxreview !== 1) return;
    if (d.kind === 'arm') {
      S.armed = !!d.on;
      if (!S.armed) { hi.remove(); close(); }
    } else if (d.kind === 'edit' && d.note) {
      const el = findEl(d.note);
      if (el) { el.scrollIntoView({block:'center', behavior:'smooth'});
                el.classList.add('uxr-flash');
                setTimeout(() => el.classList.remove('uxr-flash'), 2600); }
      open(Object.assign({}, d.note), null, d.note);
    } else if (d.kind === 'show' && d.note) {
      const el = findEl(d.note);
      if (!el) return;
      el.scrollIntoView({block:'center', behavior:'smooth'});
      el.classList.add('uxr-flash');
      setTimeout(() => el.classList.remove('uxr-flash'), 2600);
    } else if (d.kind === 'sync') {
      (d.notes || []).forEach(n => { if (n.variant === VARIANT) pin(n.n, n); });
      const live = new Set((d.notes || []).filter(n => n.variant === VARIANT)
                           .map(n => n.n));
      [...S.pins.keys()].forEach(k => { if (!live.has(k)) unpin(k); });
    }
  });
})();
</script>
"""


def inject_into(body: bytes, variant: str) -> bytes:
    js = INJECT.replace("__VARIANT__", variant).replace("{chips}", json.dumps(CHIPS))
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
    """DeuxUI's own contract, not the reviewed project's.

    This read the project's contract, so the review chrome wore the colours of the
    thing being reviewed -- and the entire job of this page is a person deciding
    between two variants of that thing. When the frame and the content are the same
    palette, "is that the tool or the product?" has no answer, and a reviewer ends up
    judging DeuxUI's buttons.

    The framed variants keep their own theming. Only the frame changes."""
    c = ux_image.Contract(uxconfig.brand_contract()) if uxconfig.brand_contract() \
        else ux_image.load_contract(None)
    ink, canvas = c.roles["ink"], c.roles["canvas"]
    return {"canvas": canvas, "surface": c.roles["surface"],
            "ink": ink, "muted": c.roles["muted"],
            "accent": c.roles["interactive"], "danger": c.roles["danger"],
            "display": c.families["display"], "body": c.families["body"],
            "mono": c.families["mono"], "r_ctl": c.r_control, "r_card": c.r_card,
            # Composed from this contract's own ink and canvas. Three warm literals
            # used to live in the dark block, which is the drift S-TOKEN-HEX and
            # S-CONTRACT-RAMP exist to catch -- and they caught it here.
            **ux_question._dark(c)}


CSS = """
:root{--canvas:%(canvas)s;--surface:%(surface)s;--ink:%(ink)s;--muted:%(muted)s;
  --accent:%(accent)s;--danger:%(danger)s;
  /* Declared once, referenced everywhere. A family repeated as a literal in eight
     rules is what S-CONTRACT-FAMILY reports, and it reported it on this page. */
  --font-display:%(display)s;--font-body:%(body)s;--font-mono:%(mono)s;
  --line:color-mix(in oklab,var(--ink) 16%%,var(--canvas));
  --hdr:64px;
  caret-color:var(--accent);accent-color:var(--accent);
  scrollbar-color:color-mix(in oklab,var(--ink) 30%%,var(--canvas)) transparent}
::selection{background:color-mix(in oklab,var(--accent) 26%%,var(--canvas));color:var(--ink)}
a{color:var(--accent);text-underline-offset:0.18em}
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light dark;scroll-padding-top:calc(var(--hdr) + 8px)}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:var(--font-body);
  font-size:17px;line-height:1.5;padding-inline:16px}

/* The header was a sticky bar taking a quarter of a phone screen -- measured, not
   guessed (R-STICKY-OBSTRUCTION). It sticks only where there is room for it. */
header{padding:14px 0 0;background:var(--canvas)}
/* Only the toolbar sticks. A tall sticky header covers whatever is focused near
   the top of the page, and no amount of scroll-padding moves something that was
   never scrolled (SC 2.4.11, measured by R-STICKY-OBSTRUCTION). */
.bar{position:sticky;top:0;z-index:5;background:var(--canvas);
  border-bottom:1px solid var(--line);padding:8px 0 10px}
h1{font-family:var(--font-display);font-size:clamp(21px,2.4vw,27px);line-height:1.2;
  margin:0 0 2px;font-weight:650;text-wrap:balance;max-width:34ch}
.sub{margin:0;color:var(--muted);max-width:62ch;text-wrap:pretty;font-size:17px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.bar label{font:13px %(mono)s;color:var(--muted)}
.seg{display:flex;border:1px solid var(--line);border-radius:%(r_ctl)spx;overflow:hidden}
.seg button{font:13px %(mono)s;padding:8px 12px;min-height:44px;min-width:44px;border:0;
  background:var(--surface);color:var(--ink);cursor:pointer}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff;
  font-weight:700;text-decoration:underline;text-underline-offset:4px;
  text-decoration-thickness:3px}
.tog{font:600 17px system-ui;padding:8px 14px;min-height:44px;border-radius:%(r_ctl)spx;
  border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.tog[aria-pressed=true]{background:var(--accent);color:#fff;border-color:var(--accent);
  text-decoration:underline;text-underline-offset:4px;text-decoration-thickness:3px}
.tally{font:13px %(mono)s;color:var(--muted)}

main{display:grid;grid-template-columns:1fr;gap:0}
/* Two variants stacked, not in a horizontal scroller. Side-scrolling to compare
   two things defeats the comparison. */
.frames{display:flex;flex-direction:column;gap:14px;padding:14px 0}
.vwrap{display:flex;flex-direction:column;gap:5px;min-width:0;max-width:100%%}
/* Asking to see 390px on a 320px screen is a legitimate thing to want. The frame
   keeps its width and scrolls inside its own box; the page never scrolls
   sideways, which is the thing that makes a comparison unusable. */
.vport{max-width:100%%;overflow-x:auto;overscroll-behavior-x:contain}
.vwrap h2{font-family:var(--font-display);font-size:21px;margin:0;font-weight:650}
.vwrap .t{font:13px %(mono)s;color:var(--muted);margin:0;word-break:break-all}
iframe{border:1px solid var(--line);border-radius:%(r_card)spx;background:#fff;
  height:min(72dvh,780px);width:100%%;max-width:100%%;display:block}
@media (min-width:1100px){
  main{grid-template-columns:minmax(0,1fr) 370px}
  .frames{flex-direction:row;align-items:flex-start;overflow-x:auto;padding:14px 16px 14px 0}
  .vwrap{flex:0 0 auto}
  .vwrap[data-fill=true]{flex:1 1 0;min-width:0}
}

aside{padding:14px 0 72px;border-top:1px solid var(--line)}
@media (min-width:1100px){
  aside{border-top:0;border-left:1px solid var(--line);padding:14px 0 24px 16px;
    position:sticky;top:var(--hdr);max-height:calc(100dvh - var(--hdr));
    overflow:auto}}
aside h2{font-family:var(--font-display);font-size:21px;margin:0;font-weight:650}
.panelhead{display:flex;align-items:center;justify-content:space-between;gap:8px;
  margin:0 0 8px}
.linkish{font:13px system-ui;background:none;border:0;color:var(--accent);
  cursor:pointer;padding:10px 6px;min-height:44px;text-decoration:underline}

.note{border:1px solid var(--line);border-radius:%(r_ctl)spx;margin:0 0 8px;
  background:var(--surface);overflow:hidden}
.note > .head{display:flex;width:100%%;gap:8px;align-items:flex-start;text-align:left;
  background:none;border:0;color:inherit;font:inherit;cursor:pointer;padding:10px 13px;
  min-height:48px}
.note .num{font:700 13px/20px %(mono)s;background:var(--accent);color:#fff;
  border-radius:999px;min-width:20px;height:20px;text-align:center;flex:0 0 auto;
  margin-top:2px;padding:0 5px}
.note .gist{flex:1 1 auto;min-width:0}
.note .gist .who{font:13px %(mono)s;color:var(--muted);display:block}
.note .gist .txt{display:block;text-wrap:pretty}
.note .chev{flex:0 0 auto;color:var(--muted);font:13px %(mono)s;margin-top:3px}
.note .body{padding:0 13px 13px;border-top:1px solid var(--line);margin-top:2px}
.note .s{font:13px %(mono)s;color:var(--muted);word-break:break-all;padding:8px 0 6px}
.note .acts{display:flex;gap:6px;flex-wrap:wrap}
.note .acts button{font:13px system-ui;min-height:44px;padding:10px 12px;
  border-radius:%(r_ctl)spx;border:1px solid var(--line);background:var(--canvas);
  color:var(--ink);cursor:pointer}
.note .acts button.danger{color:var(--danger);border-color:var(--danger)}
.note textarea,.note select{width:100%%;font:inherit;padding:9px;margin:6px 0;
  border:1px solid color-mix(in oklab,var(--ink) 30%%,var(--canvas));
  border-radius:%(r_ctl)spx;background:var(--canvas);color:var(--ink)}
.note textarea{min-height:88px;resize:vertical}
.note select{min-height:44px}
.note[data-editing=true]{border-color:var(--accent);
  box-shadow:0 0 0 2px color-mix(in oklab,var(--accent) 28%%,transparent)}
.empty{color:var(--muted);text-wrap:pretty;font-size:17px}

form{border-top:1px solid var(--line);margin-top:14px;padding-top:13px}
fieldset{border:0;padding:0;margin:0 0 8px}
legend{font-family:var(--font-display);font-size:21px;font-weight:650;padding:0;margin:0 0 6px}
.opt{display:flex;gap:9px;align-items:flex-start;padding:9px 10px;min-height:48px;
  border:1px solid var(--line);border-radius:%(r_ctl)spx;margin:0 0 6px;cursor:pointer;
  background:var(--surface)}
.opt input{width:20px;height:20px;margin:3px 0 0;flex:0 0 auto}
.opt:has(input:checked){background:color-mix(in oklab,var(--accent) 14%%,var(--surface));
  border-color:var(--accent);outline:2px solid var(--accent);outline-offset:-2px}
.opt span.h{font-weight:600;display:block}
.opt span.d{font-size:14px;color:var(--muted);display:block;text-wrap:pretty}
.opt.primary span.h::before{content:"✓ ";color:var(--accent);
  font-weight:700}
.divider{font:13px %(mono)s;color:var(--muted);margin:10px 0 6px;
  display:flex;align-items:center;gap:8px}
.divider::after{content:"";flex:1;height:1px;background:var(--line)}
label.f{display:block;font-weight:600;margin:13px 0 4px}
label.f .opt-tag{font-weight:400;color:var(--muted);font-size:14px}
.hint{display:block;font-weight:400;font-size:14px;color:var(--muted);margin:2px 0 6px;
  text-wrap:pretty;max-width:52ch}
input[type=text],textarea{width:100%%;font:inherit;padding:10px 13px;min-height:46px;
  border:1px solid color-mix(in oklab,var(--ink) 32%%,var(--canvas));
  border-radius:%(r_ctl)spx;background:var(--surface);color:var(--ink)}
textarea{min-height:88px;resize:vertical}
button.send{width:100%%;margin-top:13px;font:650 17px system-ui;min-height:48px;
  border:0;border-radius:%(r_ctl)spx;background:var(--accent);color:#fff;cursor:pointer}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.err{background:color-mix(in oklab,var(--danger) 12%%,var(--canvas));
  border:1px solid var(--danger);border-radius:%(r_ctl)spx;padding:10px 13px;margin:10px 0}
.err ul{margin:4px 0 0;padding-left:18px}
.fielderr{color:var(--danger);font-size:14px;margin:4px 0 0;display:block}
.state{display:block;font-size:14px;margin:4px 0 0;color:var(--muted);
  text-wrap:pretty;max-width:52ch}
.state[data-ok=yes]{color:var(--success)}
.state[data-ok=yes]::before{content:"✓ "}
.loading{padding:22px 0;color:var(--muted);display:flex;gap:10px;align-items:center}
.spin{width:18px;height:18px;border-radius:999px;border:3px solid var(--line);
  border-top-color:var(--accent);animation:spin 900ms linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.spin{animation-duration:2.4s}}
@media (prefers-color-scheme:dark){
  :root{--canvas:%(d_canvas)s;--surface:%(d_surface)s;--ink:%(d_ink)s;
    --muted:color-mix(in oklab,var(--ink) 72%%,var(--canvas));
    --accent:color-mix(in oklab,%(accent)s 78%%,#ffffff);
    --line:color-mix(in oklab,var(--ink) 22%%,var(--canvas))}
  button.send,.seg button[aria-pressed=true],.tog[aria-pressed=true],
  .note .num{color:var(--canvas)}}
"""

WIDTHS = [("320", 320), ("390", 390), ("768", 768), ("1024", 1024), ("full", 0)]


def page(rv: Review, th: dict, errors=None, form=None) -> str:
    errors, form = errors or [], form or {}
    chips = json.dumps(CHIPS)
    # The form and the validator read the SAME requirement, so the hint can never
    # promise something the server then refuses -- which is how "one or two
    # sentences" led to "a combination needs to say which parts of which variant".
    reqs = {c: why_requirement(c, rv)
            for c in ([f"accept:{v}" for v in rv.variants]
                      + ["combine", "changes", "reject"])}
    reqs_json = json.dumps({k: {"state": v[0], "hint": v[1]} for k, v in reqs.items()})
    meta = json.dumps({"min": MIN_REASON, "variants": list(rv.variants),
                       "notes": len(rv.notes)})
    frames = []
    for vid, v in rv.variants.items():
        label = v["target"] if v["kind"] == "url" else Path(v["target"]).name
        frames.append(
            f'<div class="vwrap" data-v="{html.escape(vid)}">'
            f'<h2>{html.escape(vid)}</h2>'
            f'<p class="t">{html.escape(str(label))}</p>'
            f'<div class="vport"><iframe title="Variant {html.escape(vid)}" '
            f'src="/v/{html.escape(vid)}/" loading="eager"></iframe></div></div>')

    # The two acceptances lead and are marked as the outcomes that let work
    # continue. Listing five neutral radios made "reject" as prominent as
    # "accept", which is not the shape of the decision.
    opts = [("accept:" + vid, f"Accept {vid}", "Build on this one.", True)
            for vid in rv.variants]
    opts += [("combine", "Combine", "Parts of more than one \u2014 say which below.", True),
             (None, "Not yet", None, False),
             ("changes", "Request changes",
              "Your notes are the work list. Nothing is approved.", False),
             ("reject", "Reject", "Wrong direction, not wrong details.", False)]
    radios = []
    for value, head, desc, primary in opts:
        if value is None:
            radios.append(f'<p class="divider">{html.escape(head)}</p>')
            continue
        radios.append(
            f'<label class="opt{" primary" if primary else ""}">'
            f'<input type="radio" name="choice" value="{html.escape(value)}"'
            f'{" checked" if form.get("choice") == value else ""}>'
            f'<span><span class="h">{html.escape(head)}</span>'
            f'<span class="d">{html.escape(desc)}</span></span></label>')

    errblock = ""
    if errors:
        errblock = ('<div class="err" role="alert" tabindex="-1" id="errors">'
                    '<strong>Not recorded yet</strong><ul>'
                    + "".join(f"<li>{html.escape(e)}</li>" for e in errors)
                    + "</ul></div>")
    segs = "".join(
        f'<button type="button" data-w="{w}" aria-pressed="false">'
        f'{html.escape(lbl)}</button>' for lbl, w in WIDTHS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(rv.question)}</title><style>{CSS % th}</style></head><body>
<header>
  <h1>{html.escape(rv.question)}</h1>
  <p class="sub">{html.escape(rv.surface or '')} &mdash; the running interface, not a
    picture of it. <strong>Alt-click</strong> anything in a frame to note it.</p>
  <div class="bar">
    <label for="segw">Width</label>
    <div class="seg" id="segw">{segs}</div>
    <button class="tog" id="armbtn" type="button" aria-pressed="false">Note mode</button>
    <button class="tog" id="darkbtn" type="button" aria-pressed="false">Try dark</button>
    <span class="tally" id="count"></span>
  </div>
</header>
<main>
  <div class="frames" id="frames" aria-busy="true">
    <p class="loading" role="status" id="loading"><span class="spin"></span>
      Loading the variants&hellip;</p>
    {''.join(frames)}
  </div>
  <aside>
    <div class="panelhead">
      <h2 id="noteshead">Notes</h2>
      <button type="button" class="linkish" id="expandall" hidden>Expand all</button>
    </div>
    <div id="notes" aria-labelledby="noteshead"></div>

    <form method="post" action="/api/decide" id="decide" novalidate>
      {errblock}
      <fieldset><legend>Decide</legend>{''.join(radios)}</fieldset>
      <label class="f" for="who">Your name</label>
      <span class="hint" id="whohint">Recorded as the person who decided this.</span>
      <input type="text" id="who" name="who" autocomplete="name"
             aria-describedby="whohint"
             value="{html.escape(form.get('who',''))}">
      <label class="f" for="why">Why<span class="opt-tag" id="whytag"></span></label>
      <span class="hint" id="whyhint">Choose an outcome above and this will say what it
        needs.</span>
      <textarea id="why" name="why"
        aria-describedby="whyhint whystate">{html.escape(form.get('why',''))}</textarea>
      <span class="state" id="whystate" role="status"></span>
      <button class="send" type="submit" id="send">Record this decision</button>
    </form>
  </aside>
</main>
<script>
const CHIPS = {chips};
const REQS = {reqs_json};
const META = {meta};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const frames = () => $$('iframe');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g,
  c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}})[c]);
function post(kind, payload) {{
  frames().forEach(f => {{
    try {{ f.contentWindow.postMessage(Object.assign({{uxreview:1, kind}}, payload), '*'); }}
    catch (e) {{}}
  }});
}}

/* ---- width. "full" means fill the column, which needs the wrapper to grow --
   it used to set the iframe to 100% of a wrapper that was sized to its content,
   so "full" rendered narrower than 320. */
function setWidth(w) {{
  $$('#segw button').forEach(o => o.setAttribute('aria-pressed',
    String(+o.dataset.w === w)));
  frames().forEach(f => {{
    f.style.width = w ? w + 'px' : '100%';
    f.closest('.vwrap').dataset.fill = w ? 'false' : 'true';
  }});
}}
$$('#segw button').forEach(b => b.onclick = () => setWidth(+b.dataset.w));
function fit() {{
  const wide = matchMedia('(min-width:1100px)').matches;
  if (!wide) return setWidth(0);            // stacked: each frame fills the column
  const n = frames().length || 1;
  const room = ($('#frames').clientWidth - 16 * (n - 1)) / n;
  setWidth([1024, 768, 390, 320].find(w => w <= room) || 0);
}}

const arm = $('#armbtn');
arm.onclick = () => {{
  const on = arm.getAttribute('aria-pressed') !== 'true';
  arm.setAttribute('aria-pressed', String(on));
  arm.textContent = on ? 'Note mode: on' : 'Note mode';
  post('arm', {{on}});
}};
const dk = $('#darkbtn');
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

/* ---- notes: collapsed to one line, opened to read or change */
let editing = null, open = new Set(), LAST = '';
addEventListener('message', e => {{
  const d = e.data || {{}};
  if (!d.uxreview && d.uxreview !== 1) return;
  if (d.kind === 'note') refresh(true);
  else if (d.kind === 'pin') {{ open.add(d.n); editing = d.n; refresh(true); focusNote(d.n); }}
  else if (d.kind === 'armed') {{
    arm.setAttribute('aria-pressed', String(!!d.on));
    arm.textContent = d.on ? 'Note mode: on' : 'Note mode';
  }}
}});
function focusNote(n) {{
  const el = document.getElementById('note' + n);
  if (!el) return;
  el.scrollIntoView({{block: 'center'}});
  const ta = el.querySelector('textarea');
  if (ta) {{ ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }}
}}
async function refresh(force) {{
  const r = await fetch('/api/state'); const s = await r.json();
  post('sync', {{notes: s.notes}});
  const sig = JSON.stringify(s.notes) + '|' + editing + '|' + [...open].join(',');
  if (!force && sig === LAST) return;
  LAST = sig;
  const box = $('#notes');
  $('#count').textContent = s.notes.length
    ? s.notes.length + ' note' + (s.notes.length === 1 ? '' : 's') : '';
  $('#expandall').hidden = s.notes.length < 2;
  if (!s.notes.length) {{
    box.innerHTML = '<p class="empty">Nothing yet. Turn on <em>Note mode</em> (or hold '
      + 'Alt) and click anything in either frame, then say what is wrong with it in '
      + 'your own words. Notes stay editable.</p>';
    return;
  }}
  box.innerHTML = s.notes.map(render).join('');
  s.notes.forEach(wire);
  hintFor();
}}
function render(n) {{
  const isOpen = open.has(n.n), isEdit = editing === n.n;
  const body = isEdit ? `
      <div class="s">${{esc(n.selector)}}</div>
      <label class="hint" for="t${{n.n}}">Your note</label>
      <textarea id="t${{n.n}}" data-f="text"></textarea>
      <label class="hint" for="c${{n.n}}">What kind</label>
      <select id="c${{n.n}}" data-f="chip">
        ${{CHIPS.map(([id, l]) => `<option value="${{id}}"${{id === n.chip ? ' selected' : ''}}>${{esc(l)}}</option>`).join('')}}
      </select>
      <div class="acts">
        <button type="button" data-a="save" data-n="${{n.n}}">Save</button>
        <button type="button" data-a="cancel" data-n="${{n.n}}">Cancel</button>
        <button type="button" class="danger" data-a="del" data-n="${{n.n}}">Delete</button>
      </div>` : `
      <div class="s">${{esc(n.selector)}}</div>
      <div class="acts">
        <button type="button" data-a="show" data-n="${{n.n}}">Show me</button>
        <button type="button" data-a="edit" data-n="${{n.n}}">Edit</button>
        <button type="button" class="danger" data-a="del" data-n="${{n.n}}">Delete</button>
      </div>`;
  return `<div class="note" id="note${{n.n}}" data-open="${{isOpen || isEdit}}"
      data-editing="${{isEdit}}">
    <button type="button" class="head" data-a="toggle" data-n="${{n.n}}"
        aria-expanded="${{isOpen || isEdit}}" aria-controls="body${{n.n}}">
      <span class="num">${{n.n}}</span>
      <span class="gist"><span class="who">${{esc(n.variant)}} \u00b7 ${{esc(n.chip)}}${{n.revision ? ' \u00b7 edited' : ''}}</span>
        <span class="txt"></span></span>
      <span class="chev">${{isOpen || isEdit ? '\u2212' : '+'}}</span>
    </button>
    <div class="body" id="body${{n.n}}"${{isOpen || isEdit ? '' : ' hidden'}}>${{body}}</div>
  </div>`;
}}
function wire(n) {{
  const el = document.getElementById('note' + n.n);
  if (!el) return;
  el.querySelector('.txt').textContent = n.text;
  const ta = el.querySelector('textarea');
  if (ta) ta.value = n.text || '';
  el.querySelectorAll('button[data-a]').forEach(b => b.onclick = async (ev) => {{
    ev.preventDefault();
    const num = +b.dataset.n, a = b.dataset.a;
    if (a === 'toggle') {{
      if (open.has(num)) {{ open.delete(num); if (editing === num) editing = null; }}
      else open.add(num);
      return refresh(true);
    }}
    if (a === 'show') return post('show', {{note: n}});
    if (a === 'edit') {{ editing = num; open.add(num); await refresh(true); return focusNote(num); }}
    if (a === 'cancel') {{ editing = null; return refresh(true); }}
    if (a === 'del') {{
      await fetch('/api/note/' + num, {{method: 'DELETE'}});
      open.delete(num); if (editing === num) editing = null;
      return refresh(true);
    }}
    if (a === 'save') {{
      const text = el.querySelector('[data-f=text]').value.trim();
      if (!text) {{ el.querySelector('[data-f=text]').focus(); return; }}
      const res = await fetch('/api/note/' + num, {{method: 'PATCH',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{text, chip: el.querySelector('[data-f=chip]').value,
                             revision: n.revision || 0}})}});
      if (res.status === 409) {{
        alert('Somebody else changed this note while you were editing it. '
              + 'Reloading it so you can see theirs first.');
      }}
      editing = null; return refresh(true);
    }}
  }});
}}
$('#expandall').onclick = () => {{
  const all = $$('#notes .note').map(e => +e.id.slice(4));
  if (open.size >= all.length) {{ open.clear(); editing = null; $('#expandall').textContent = 'Expand all'; }}
  else {{ all.forEach(n => open.add(n)); $('#expandall').textContent = 'Collapse all'; }}
  refresh(true);
}};

/* ---- the decision form asks for what the outcome actually needs, and says so
   while you type rather than after you submit. The requirement text comes from
   the server, so the hint and the refusal cannot disagree. */
const STOCK = /^(?:looks? *good|lgtm|good|fine|ok(?:ay)?|yes|yep|nice|better|best|great|perfect|love it|ship it|sure|\\+1|done|approved|agreed|this one|the first|the second|no comment|n\\/?a)[\\s.!]*$/i;
function choiceNow() {{ const r = $('input[name=choice]:checked'); return r ? r.value : ''; }}
function hintFor() {{
  const v = choiceNow();
  const req = REQS[v] || {{state: '', hint: 'Choose an outcome above and this will say what it needs.'}};
  $('#whytag').textContent = req.state === 'optional' ? '  \u2014 optional here'
    : (req.state ? '  \u2014 needed' : '');
  $('#whyhint').textContent = req.hint;
  $('#send').textContent = v && v.startsWith('accept:')
    ? 'Accept ' + v.slice(7) : (v === 'changes' ? 'Send these changes back'
    : (v === 'reject' ? 'Record the rejection' : 'Record this decision'));
  whyState();
}}
function whyState() {{
  const v = choiceNow(), why = $('#why').value.trim(), el = $('#whystate');
  const req = REQS[v];
  if (!v || !req || !req.state) {{ el.textContent = ''; el.dataset.ok = ''; return; }}
  let msg = '', ok = '';
  if (!why) {{
    msg = req.state === 'optional' ? 'Optional \u2014 you can leave this empty.'
        : 'Needed before this can be recorded.';
    ok = req.state === 'optional' ? 'yes' : '';
  }} else if (STOCK.test(why)) {{
    msg = '\u201c' + why + '\u201d does not say anything the next person can use.';
  }} else if (why.length < META.min) {{
    msg = 'A few more words.';
  }} else if (req.state === 'named') {{
    const low = why.toLowerCase();
    // A word boundary, written without a backslash escape: this JS lives inside
    // a Python f-string, and `\b` there arrives in the browser as a literal
    // backspace character, which matches nothing and silently never names a
    // variant. Index arithmetic cannot be mangled on the way through.
    const named = META.variants.filter(n => {{
      const t = n.toLowerCase(), i = low.indexOf(t);
      if (i < 0) return false;
      const before = i === 0 ? ' ' : low[i - 1];
      const after = low[i + t.length] || ' ';
      return !/[a-z0-9]/.test(before) && !/[a-z0-9]/.test(after);
    }});
    if (named.length || low.includes('both') || low.includes('each')) {{
      msg = 'Good \u2014 it names what is being combined.'; ok = 'yes';
    }} else {{
      msg = 'Name which variant each part comes from: ' + META.variants.join(' or ') + '.';
    }}
  }} else {{
    msg = 'That reads like a reason.'; ok = 'yes';
  }}
  el.textContent = msg; el.dataset.ok = ok;
}}
$$('input[name=choice]').forEach(r => r.onchange = hintFor);
$('#why').addEventListener('input', whyState);
hintFor();

/* ---- loading: say something while the frames arrive (R-STATE-SLOW) */
let pending = frames().length;
frames().forEach(f => f.addEventListener('load', () => {{
  if (--pending <= 0) {{
    $('#frames').setAttribute('aria-busy', 'false');
    const l = $('#loading'); if (l) l.remove();
  }}
  refresh(true);
}}));
setTimeout(() => {{ const l = $('#loading'); if (l) l.remove();
  $('#frames').setAttribute('aria-busy', 'false'); }}, 12000);

setInterval(() => refresh(false), 1500);
refresh(true); fit();
addEventListener('resize', fit);
const e0 = document.getElementById('errors'); if (e0) e0.focus();
</script></body></html>"""


DONE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Recorded</title>
<style>%(css)s
.done{max-width:56ch;margin:0 auto;padding:64px 0 48px}
.done h1{max-width:none;margin:0 0 6px}
.done p{max-width:none;margin:0 0 12px}
.done .rec{background:var(--surface);border:1px solid var(--line);
  border-radius:%(r_card)spx;padding:14px 16px;margin:18px 0}
.done .rec dt{font:13px %(mono)s;color:var(--muted);margin-top:8px}
.done .rec dt:first-child{margin-top:0}
.done .rec dd{margin:2px 0 0;word-break:break-word}
.done ul{margin:6px 0 0;padding-left:20px}
.done li{margin:0 0 6px}
.done .next{border-top:1px solid var(--line);padding-top:14px;margin-top:20px}
</style></head><body><main class="done">
<h1>%(head)s</h1>
<p class="sub">%(lede)s</p>
<div class="rec"><dl>
  <dt>Outcome</dt><dd>%(outcome)s</dd>
  <dt>Decided by</dt><dd>%(who)s on %(date)s</dd>
  <dt>Record</dt><dd><code>%(file)s</code></dd>
</dl></div>
%(notes)s
<div class="next"><p class="sub">%(next)s</p></div>
</main></body></html>"""


# ------------------------------------------------------------------ recording
def _highest(dirp: Path, prefix: str) -> int:
    n = 0
    if dirp.exists():
        for f in dirp.glob(f"{prefix}-*.yaml"):
            m = re.match(rf"{prefix}-(\d+)", f.stem)
            if m:
                n = max(n, int(m.group(1)))
    return n


def _next(dirp: Path, prefix: str) -> str:
    dirp.mkdir(parents=True, exist_ok=True)
    return f"{prefix}-{_highest(dirp, prefix) + 1:03d}"


def note_path(rv: "Review", n: int) -> Path:
    """One note number, one file, for the life of this review."""
    return REQUESTS / f"REQ-{rv.base + n:03d}.yaml"


def write_note(rec: dict, path: Path | None = None) -> Path:
    """Write (or rewrite) the work item for one note.

    A note the reviewer can no longer change is a note they will stop leaving, so
    an edit rewrites the same file rather than adding a second one -- and the file
    keeps a count of how many times it was revised, because a sentence somebody
    rewrote three times is usually the one that matters."""
    p = path or (REQUESTS / f"{_next(REQUESTS, 'REQ')}.yaml")
    out = {k: v for k, v in rec.items() if not k.startswith("_")}
    out["id"] = p.stem
    out["source"] = "review"
    out["action"] = rec.get("chip") or "note"
    out["recorded_by"] = ("deuxui/scripts/ux_review.py -- a person wrote this while "
                          "looking at the running interface")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=92))
    return p


def why_requirement(choice: str, rv: "Review") -> tuple[str, str]:
    """(state, sentence) for the reason field, given the outcome.

    The same function answers the form before submission and the validator after
    it, so what the field asks for and what the server refuses cannot drift --
    which is how somebody picks Combine, reads a hint about "one or two
    sentences", and is then told they needed to name the variants."""
    names = " / ".join(rv.variants)
    if choice == "combine":
        return ("named", f"Name the parts and which variant each comes from \u2014 "
                         f"\u201c{names.split(' / ')[0]}\u2019s card layout with "
                         f"{list(rv.variants)[-1]}\u2019s action row\u201d. The build "
                         f"is made from this sentence, so it has to say which is which.")
    if choice == "reject":
        return ("needed", "What is wrong with the direction \u2014 not the details. "
                          "The next round is built from this.")
    if choice.startswith("accept:"):
        return ("needed", "A sentence for whoever reads this later, deciding whether "
                          "to undo it. What does this one do that the other does not?")
    if choice == "changes":
        if rv.notes:
            return ("optional", f"Your {len(rv.notes)} note(s) are the work list. Add "
                                f"anything they do not cover, or leave this empty.")
        return ("needed", "You have left no notes, so this is the only thing the next "
                          "round has to go on.")
    return ("", "Choose an outcome above and this will say what it needs.")


def validate(form: dict, rv: Review) -> list:
    """What this outcome actually needs, and nothing else."""
    errs = []
    choice = (form.get("choice") or "").strip()
    who = (form.get("who") or "").strip()
    why = (form.get("why") or "").strip()
    valid = {f"accept:{v}" for v in rv.variants} | {"combine", "changes", "reject"}
    if choice not in valid:
        errs.append("Choose an outcome. Nothing is recorded without one.")
        return errs
    if not who:
        errs.append("Add your name. An approval with no author cannot be weighed "
                    "later, so it cannot gate anything.")
    elif SELF.search(who):
        errs.append(f"\u201c{who}\u201d is the agent that produced these. Whoever is "
                    f"deciding has to be someone other than the thing proposing \u2014 "
                    f"put your own name in.")

    state, sentence = why_requirement(choice, rv)
    if state == "optional" and not why:
        return errs
    if state in ("needed", "named", "optional") and why:
        # A stock phrase is the thing the old length test was reaching for, and it
        # catches it directly: "looks good" is not short, it is empty.
        if EMPTY_REASON.match(why):
            errs.append(f"\u201c{why}\u201d does not say anything the next person can "
                        f"use. {sentence}")
            return errs
    if state in ("needed", "named") and len(why) < MIN_REASON:
        errs.append((("Nothing in the Why field. " if not why else "Say a little more. ")
                     + sentence))
    elif state == "named":
        # Combine is the one outcome with a checkable requirement: it has to name
        # what is being combined. Counting characters never tested that.
        low = why.lower()
        named = sum(1 for v in rv.variants
                    if re.search(rf"\b{re.escape(v.lower())}\b", low))
        if named < 1 and "both" not in low and "each" not in low:
            errs.append(f"Say which variant each part comes from. The options are "
                        f"{', '.join(rv.variants)}, and the build is made from this "
                        f"sentence.")
    return errs


def _contract_sha() -> str | None:
    """The sha of the declaration in force, archived so it stays resolvable.

    Archiving here rather than only in a separate step is deliberate: the moment a
    person approves something is exactly the moment the contract's bytes acquire
    evidential value, and an archive that depends on somebody having run a command
    earlier has holes precisely at the approvals."""
    try:
        c = ux_image.load_contract(None)
        if not c.raw:
            return None
        ux_ledger.archive(by="ux_review.py (an approval was recorded against it)")
        return c.sha()
    except Exception:                       # never lose a decision over bookkeeping
        return None


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
        # The declaration this was approved against, content-addressed. Without it
        # the approval survives and what it approved does not, so the ledger can
        # only report the decision as unresolvable -- see ux_ledger.py.
        "contract_sha": _contract_sha(),
        "reviewed": [{"id": vid, "kind": v["kind"], "target": v["target"]}
                     for vid, v in rv.variants.items()],
        "shown": [{"id": vid, "title": f"{vid} ({v['kind']})", "image": None,
                   "image_sha": None} for vid, v in rv.variants.items()],
        # rv.notes, not the notes typed in this process: a review that resumed
        # after a restart has its work items on disk and in the panel, and
        # recording zero of them made the decision look unexamined.
        "notes": [{"id": n.get("req") or Path(str(n.get("_file") or "")).stem,
                   "variant": n.get("variant"), "chip": n.get("chip"),
                   "selector": n.get("selector"), "text": n.get("text")}
                  for n in rv.notes],
        "source": "ux_review.py (live A/B review of the running interface)",
        "recorded_by": "deuxui/scripts/ux_review.py (served page, human submitted)",
    }
    DECISIONS.mkdir(parents=True, exist_ok=True)
    p = DECISIONS / f"{did}.yaml"
    p.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=92))
    return p


# --------------------------------------------------------------------- server
def handler_for(rv: Review, th: dict, notes_written: list, echo):
    class H(BaseHTTPRequestHandler):
        server_version = "deuxui-review"
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
                "User-Agent": self.headers.get("User-Agent", "deuxui"),
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
                     f"<p style='font:16px system-ui;padding:24px'>deuxui could not "
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
                p = write_note(rec, note_path(rv, rec["n"]))
                rec["_file"] = str(p)
                rec["req"] = p.stem
                write_note(rec, p)
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
                rec = yaml.safe_load(p.read_text()) or {}
                rv.decision = {"file": str(p), "outcome": form["choice"]}
                approves = bool(rec.get("approves_a_build"))
                notes_html = ""
                if rv.notes:
                    items = "".join(
                        f"<li><strong>{html.escape(str(n.get('req') or ''))}</strong> "
                        f"<span class=\"sub\">({html.escape(str(n.get('variant')))} · "
                        f"{html.escape(str(n.get('chip')))})</span><br>"
                        f"{html.escape(str(n.get('text') or ''))}</li>"
                        for n in rv.notes)
                    notes_html = (f'<p class="sub">{len(rv.notes)} work item(s) went '
                                  f'with it, in <code>.deuxui/requests/</code>:</p>'
                                  f"<ul>{items}</ul>")
                else:
                    notes_html = ('<p class="sub">No element notes were left, so the '
                                  'decision stands on its reason alone.</p>')
                body = DONE % {
                    **th,
                    "css": CSS % th, "r_card": th["r_card"],
                    "head": "Recorded" if approves else "Sent back",
                    "lede": html.escape(
                        "This is now the approval the build gate reads."
                        if approves else
                        "Nothing is approved. The notes are the work list, and the "
                        "build stays closed until somebody accepts a version."),
                    "outcome": html.escape(str(rec.get("outcome") or "")),
                    "who": html.escape(str(rec.get("who") or "")),
                    "date": html.escape(str(rec.get("date") or "")),
                    "file": html.escape(str(p)),
                    "notes": notes_html,
                    "next": html.escape(
                        "You can close this tab. The agent has the record and every "
                        "note, with the element each one is about."),
                }
                self._send(body.encode())
                threading.Thread(target=lambda: (time.sleep(0.4), rv.done.set()),
                                 daemon=True).start()
                return
            return self._send(b"not found", "text/plain", 404)

        # --- a note is not a receipt. It is a sentence somebody is still working
        # out, so it stays editable and removable for as long as the review runs.
        def _note_num(self, path):
            m = re.fullmatch(r"/api/note/(\d+)", path)
            return int(m.group(1)) if m else None

        def do_PATCH(self):
            n = self._note_num(urllib.parse.urlparse(self.path).path)
            if n is None:
                return self._send(b"not found", "text/plain", 404)
            ln = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(min(ln, 200_000)).decode("utf-8",
                                                                           "replace"))
            except ValueError:
                return self._send(b'{"error":"bad json"}', "application/json", 400)
            text = str(body.get("text") or "").strip()
            if not text:
                return self._send(b'{"error":"a note with no words is a deletion"}',
                                  "application/json", 400)
            # Two tabs, or two reviewers, editing one note. The client sends the
            # revision it read; a mismatch means somebody else has written since,
            # and last-write-wins would drop their sentence without telling
            # anyone (S-CONFLICT-OVERWRITE).
            cur = rv.find(n)
            if cur is None:
                return self._send(b'{"error":"no such note"}', "application/json", 404)
            seen = body.get("revision")
            if seen is not None and int(seen) != int(cur.get("revision") or 0):
                return self._send(json.dumps({
                    "error": "changed since you opened it",
                    "current": cur.get("text"), "revision": cur.get("revision")}).encode(),
                    "application/json", 409)
            rec = rv.update_note(n, text, str(body.get("chip") or "").strip())
            if rec is None:
                return self._send(b'{"error":"no such note"}', "application/json", 404)
            path = Path(rec["_file"]) if rec.get("_file") else None
            p = write_note(rec, path)
            rec["_file"] = str(p)
            for i, (q, r) in enumerate(notes_written):
                if r.get("n") == n:
                    notes_written[i] = (p, rec)
                    break
            echo(f"  {p.stem}  edited -> \u201c{text[:120]}\u201d\n")
            return self._send(json.dumps({"n": n, "id": p.stem}).encode(),
                              "application/json")

        def do_DELETE(self):
            n = self._note_num(urllib.parse.urlparse(self.path).path)
            if n is None:
                return self._send(b"not found", "text/plain", 404)
            rec = rv.remove_note(n)
            if rec is None:
                return self._send(b'{"error":"no such note"}', "application/json", 404)
            p = Path(rec["_file"]) if rec.get("_file") else None
            if p and p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
            notes_written[:] = [(q, r) for q, r in notes_written if r.get("n") != n]
            echo(f"  {p.stem if p else 'note ' + str(n)}  withdrawn by the reviewer\n")
            return self._send(json.dumps({"n": n, "deleted": True}).encode(),
                              "application/json")
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
          f"  lands in .deuxui/requests/ with the element it is about.\n"
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
        f"  notes:    {len(notes_written)} element note(s) in .deuxui/requests/\n")
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
