#!/usr/bin/env python3
"""Serve one design decision as a page, and record the answer as evidence.

An agent asking "which of these three?" in a chat transcript gets an answer that
lives nowhere. Six weeks later nobody can say which comp was approved, by whom, or
against what -- so the approval cannot gate anything, and in practice it does not.

This serves the decision as a real page on localhost: the comps side by side, the
structural claim each one makes, and a form. The answer becomes
`.deluxui/decisions/DEC-NNN.yaml`, hashed against exactly what was shown, and the
phase gate reads it.

Three refusals are the point of the thing:

  * An answer with no `who` and no reason is not recorded. The bar is the same one
    `ux_report.vet_attestation` applies to a manual check, for the same reason: a
    signature nobody can weigh is not evidence, and letting it through would make
    the approval gate launderable by whoever is holding the keyboard.
  * A timeout records nothing and exits 3. Nobody chose, so there is no choice --
    NOT_RUN, never a default that the transcript later describes as approved.
  * The hash covers the comps as served. Approving A and then editing A means the
    recorded approval no longer matches the file, and `--check` says so.

    ux_question.py ask <comps.yaml|question.yaml> [--port 8787] [--timeout 1800]
    ux_question.py list
    ux_question.py show DEC-003
    ux_question.py check          exit 2 when an approval no longer matches its files

Exit: 0 answered, 2 a recorded approval is stale, 3 nobody answered.
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
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yaml                                                        # noqa: E402
import ux_image                                                    # noqa: E402

DECISIONS = Path(".deluxui/decisions")
# See scripts/ux_review.py: a length test is a stand-in for a substance test and
# fails in both directions. Twelve excludes "ok"; the stock-phrase list excludes
# the thing the long minimum was actually reaching for.
MIN_REASON = 12
EMPTY_REASON = re.compile(
    r"^(?:looks?\s*good|lgtm|good|fine|ok(?:ay)?|yes|yep|nice|better|best|great|"
    r"perfect|love it|ship it|sure|\+1|done|approved|agreed|this one|the first|"
    r"the second|no comment|n/?a)[\s.!]*$", re.I)
# The same list ux_report uses to refuse a self-attestation. A decision the agent
# made and then recorded as the user's is the single most damaging thing this file
# could allow, because everything downstream treats an approval as human judgement.
SELF = re.compile(r"\b(?:claude|chatgpt|gpt|copilot|cursor|codex|gemini|llm|ai|"
                  r"agent|assistant|model|bot|automated|self|me|myself|"
                  r"this session|the tool)\b", re.I)
MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


# ------------------------------------------------------------------ the input
def load_question(path: Path) -> dict:
    d = yaml.safe_load(path.read_text()) or {}
    opts = []
    for o in d.get("options") or []:
        img = o.get("image")
        opts.append({"id": str(o.get("id") or len(opts) + 1),
                     "title": o.get("title") or "",
                     "decides": o.get("decides") or "",
                     "cost": o.get("cost") or "",
                     "regions": o.get("regions") or [],
                     "image": str(img) if img else None})
    if not opts and d.get("rendered"):
        for i, f in enumerate(d["rendered"]):
            opts.append({"id": chr(65 + i), "title": Path(f).stem, "decides": "",
                         "cost": "", "regions": [], "image": f})
    return {"question": d.get("question") or "Which direction?",
            "surface": d.get("surface") or "",
            "viewport": d.get("viewport") or [1440, 900],
            "kind": d.get("kind") or ("approval" if len(opts) == 1 else "choice"),
            "contract_sha": d.get("contract_sha"),
            "contract_undeclared": d.get("contract_undeclared") or [],
            "brief_sha": d.get("brief_sha"),
            "source": str(path), "options": opts}


def file_sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def options_sha(q: dict) -> str:
    """A hash of exactly what the person was shown.

    Not of the question file: of the question text, each option's claim, and the
    bytes of each image. Editing a comp after approval has to be detectable, or
    "approved" degrades into "approved something, once"."""
    h = hashlib.sha256()
    h.update((q["question"] + "\x1f" + q["surface"]).encode())
    for o in q["options"]:
        h.update(("\x1e" + o["id"] + "\x1f" + o["title"] + "\x1f" + o["decides"]
                  + "\x1f" + json.dumps(o["regions"], sort_keys=True)).encode())
        if o["image"]:
            h.update((file_sha(Path(o["image"])) or "missing").encode())
    return h.hexdigest()[:16]


# -------------------------------------------------------------------- the page
def theme() -> dict:
    c = ux_image.load_contract(None)
    return {"canvas": c.roles["canvas"], "surface": c.roles["surface"],
            "ink": c.roles["ink"], "muted": c.roles["muted"],
            "accent": c.roles["interactive"], "danger": c.roles["danger"],
            "display": c.families["display"], "body": c.families["body"],
            "mono": c.families["mono"], "r_card": c.r_card, "r_ctl": c.r_control,
            "undeclared": c.undeclared}


# The page takes its colours and families from the project's contract so it looks
# like the product it is asking about -- but its type ladder is its own. Inheriting
# a project's flat scale would make deluxui's own surface fail deluxui's own craft
# check, and the finding would be about the contract rather than about this page.
# Steps: 13 / 17 / 22 / 29 / clamp(29-48), each at least 1.25x the one below.
CSS = """
:root{--canvas:%(canvas)s;--surface:%(surface)s;--ink:%(ink)s;--muted:%(muted)s;
      --accent:%(accent)s;--danger:%(danger)s;--line:color-mix(in oklab,var(--ink) 14%%,var(--canvas))}
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:%(body)s;
     font-size:17px;line-height:1.55;-webkit-text-size-adjust:100%%;
     padding-inline:16px}
.wrap{max-width:1180px;margin:0 auto;padding:32px 4px 96px}
h1{font-family:%(display)s;font-size:clamp(29px,3.4vw,48px);line-height:1.12;
   margin:0 0 8px;font-weight:650;text-wrap:balance;max-width:26ch}
.sub{color:var(--muted);margin:0 0 4px;max-width:68ch;text-wrap:pretty}
.meta{font-family:%(mono)s;font-size:13px;color:var(--muted);margin:18px 0 0;
   max-width:80ch;text-wrap:pretty}
.warn{background:color-mix(in oklab,var(--danger) 10%%,var(--canvas));
      border-left:4px solid var(--danger);padding:12px 14px;margin:20px 0;
      border-radius:%(r_ctl)spx;max-width:80ch}
.grid{display:grid;gap:22px;margin:26px 0 0;
      grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.opt{background:var(--surface);border:1px solid var(--line);
     border-radius:%(r_card)spx;overflow:hidden;display:flex;flex-direction:column}
.opt:focus-within{outline:3px solid var(--accent);outline-offset:2px}
.opt img{width:100%%;height:auto;display:block;background:var(--canvas);
         border-bottom:1px solid var(--line)}
.opt .body{padding:16px 18px 18px}
.opt h2{font-family:%(display)s;font-size:22px;margin:0 0 4px;font-weight:650;
   text-wrap:balance}
.opt .decides{color:var(--muted);margin:0 0 12px;text-wrap:pretty}
.tscroll{overflow-x:auto}
table{width:100%%;border-collapse:collapse;font-family:%(mono)s;font-size:13px}
th{text-align:left;font-weight:600;color:var(--muted);padding:3px 8px 6px 0;
   border-bottom:1px solid color-mix(in oklab,var(--ink) 30%%,var(--canvas));
   white-space:nowrap}
td{padding:3px 8px 3px 0;vertical-align:top;border-bottom:1px solid var(--line)}
td.n{color:var(--muted);white-space:nowrap}
.pick{display:flex;gap:10px;align-items:center;padding:14px 18px;
      border-top:1px solid var(--line);margin-top:auto;
      min-height:56px;cursor:pointer;font-weight:600}
.pick input{width:22px;height:22px;accent-color:var(--accent);margin:0}
.pick:has(input:checked){background:color-mix(in oklab,var(--accent) 14%%,var(--surface))}
fieldset{border:0;padding:0;margin:0}
legend{font-family:%(display)s;font-size:29px;font-weight:650;padding:0;
       margin:40px 0 6px;text-wrap:balance}
label.f{display:block;font-weight:600;margin:20px 0 6px}
.hint{color:var(--muted);font-weight:400;font-size:13px;display:block;margin-top:2px;
  max-width:62ch;text-wrap:pretty}
input[type=text],textarea{width:100%%;font:inherit;padding:11px 13px;min-height:48px;
  max-width:62ch;border:1px solid color-mix(in oklab,var(--ink) 34%%,var(--canvas));
  border-radius:%(r_ctl)spx;background:var(--surface);color:var(--ink)}
textarea{min-height:120px;resize:vertical}
input:focus-visible,textarea:focus-visible,button:focus-visible,
a:focus-visible,.tscroll:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
button{font:inherit;font-weight:650;background:var(--accent);color:#fff;border:0;
  padding:14px 26px;min-height:48px;border-radius:%(r_ctl)spx;cursor:pointer;
  margin-top:26px}
button:hover{filter:brightness(1.08)}
.err{background:color-mix(in oklab,var(--danger) 12%%,var(--canvas));
     border:1px solid var(--danger);border-radius:%(r_ctl)spx;padding:14px 16px;
     margin:22px 0;max-width:80ch}
.err h3{margin:0 0 6px;font-size:22px}
.err ul{margin:0;padding-left:20px}
.done{text-align:center;padding:80px 20px}
@media (prefers-reduced-motion:no-preference){.opt{transition:box-shadow .14s ease}}
/* Dark is composed, not inverted: the ground goes warm-dark, the ink goes warm
   paper, and muted is re-derived against the new ground rather than carried over
   from the light theme -- a muted grey chosen against paper lands at about 2.5:1
   on a dark card, which is the most common way a dark mode fails a contrast check
   that its light twin passes. */
@media (prefers-color-scheme:dark){
  :root{--canvas:#14120e;--surface:#1e1b16;--ink:#f4f0e7;
        --muted:color-mix(in oklab,#f4f0e7 72%%,#14120e);
        --accent:color-mix(in oklab,%(accent)s 78%%,#ffffff);
        --line:color-mix(in oklab,#f4f0e7 22%%,#14120e)}
  button{color:#14120e}
}
"""

def _regions_table(o: dict) -> str:
    if not o["regions"]:
        return ""
    rows = []
    tot = sum(float(r.get("share") or 0) for r in o["regions"]) or 1.0
    for r in o["regions"]:
        share = float(r.get("share") or 0) / tot
        rows.append(f"<tr><td class=n>{html.escape(str(r.get('name') or ''))}</td>"
                    f"<td class=n>{html.escape(str(r.get('medium') or ''))}</td>"
                    f"<td class=n>{share * 100:.0f}%</td>"
                    f"<td>{html.escape(str(r.get('holds') or ''))}</td></tr>")
    return ("<div class=tscroll role=region tabindex=0 "
            f"aria-label=\"Regions of option {html.escape(o['id'])}\">"
            "<table><caption class='sr-only'>What this option claims: each region, "
            "whether it ships as code or as a raster, how much of the height it "
            "takes, and what it holds.</caption>"
            "<thead><tr><th scope=col>Region</th><th scope=col>Medium</th>"
            "<th scope=col>Share</th><th scope=col>Holds</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def page(q: dict, th: dict, errors=None, form=None) -> str:
    form = form or {}
    errors = errors or []
    cards = []
    vp = q.get("viewport") or [1440, 900]
    iw, ih = int(vp[0]), int(vp[1]) + 150      # the sheet includes its caption block
    for i, o in enumerate(q["options"]):
        img = (f'<img src="/asset/{i}" width="{iw}" height="{ih}" '
               f'style="aspect-ratio:{iw}/{ih}" alt="Comp {html.escape(o["id"])}: '
               f'{html.escape(o["title"])}. The region table below states what it '
               f'claims; the image is not the only description.">'
               if o["image"] else "")
        checked = " checked" if form.get("choice") == o["id"] else ""
        cards.append(f"""
<div class="opt">{img}
  <div class="body">
    <h2>{html.escape(o['id'])} &mdash; {html.escape(o['title'])}</h2>
    <p class="decides">{html.escape(o['decides'] or 'No stated decision.')}</p>
    {_regions_table(o)}
    {f'<p class="decides">Cost: {html.escape(o["cost"])}</p>' if o['cost'] else ''}
  </div>
  <label class="pick" for="c{i}">
    <input type="radio" name="choice" id="c{i}" value="{html.escape(o['id'])}"{checked}>
    Choose {html.escape(o['id'])}
  </label>
</div>""")
    for extra, label, desc in (
            ("combine", "Combine", "Take parts of more than one. Say which parts."),
            ("reject", "Reject all", "None of these. Say what is wrong with the "
                                     "direction so the next round is not a guess.")):
        checked = " checked" if form.get("choice") == extra else ""
        cards.append(f"""
<div class="opt"><div class="body">
  <h2>{html.escape(label)}</h2><p class="decides">{html.escape(desc)}</p></div>
  <label class="pick" for="x{extra}">
    <input type="radio" name="choice" id="x{extra}" value="{extra}"{checked}>
    {html.escape(label)}
  </label></div>""")

    errblock = ""
    if errors:
        items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errblock = (f'<div class="err" role="alert" tabindex="-1" id="errors">'
                    f'<h3>This was not recorded</h3><ul>{items}</ul></div>')
    und = ""
    if q.get("contract_undeclared"):
        und = (f'<div class="warn"><strong>'
               f'{len(q["contract_undeclared"])} contract fields are undeclared</strong> '
               f'({html.escape(", ".join(q["contract_undeclared"]))}). Those parts of '
               f'these comps are placeholders, not proposals &mdash; approving this '
               f'does not decide them.</div>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(q['question'])}</title>
<style>{CSS % th}
.sr-only{{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
  overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}}</style>
</head><body>
<div class="wrap">
<h1>{html.escape(q['question'])}</h1>
<p class="sub">{html.escape(q['surface'] or '')}</p>
{und}{errblock}
<form method="post" action="/answer" novalidate>
<fieldset>
  <legend class="sr-only">The options</legend>
  <div class="grid">{''.join(cards)}</div>
</fieldset>
<fieldset>
  <legend>Record the decision</legend>
  <label class="f" for="who">Who is deciding
    <span class="hint">A person's name. This is recorded as the authority for the
    decision, so an agent's name is refused.</span></label>
  <input type="text" id="who" name="who" autocomplete="name"
         value="{html.escape(form.get('who', ''))}">
  <label class="f" for="why">Why this one
    <span class="hint">A sentence. The reason is what the next person reads when
    they are about to undo this, so "looks better" tells them nothing — say
    what this option does that the others do not.</span></label>
  <textarea id="why" name="why">{html.escape(form.get('why', ''))}</textarea>
  <button type="submit">Record this decision</button>
</fieldset>
</form>
<p class="meta">served by deluxui &middot; contract {html.escape(str(q.get('contract_sha') or 'none'))}
 &middot; shown-hash {html.escape(options_sha(q))} &middot; nothing is recorded until you submit</p>
</div>
<script>
 var e=document.getElementById('errors'); if(e){{e.focus();}}
</script>
</body></html>"""


DONE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recorded</title><style>%(css)s</style></head><body><div class="wrap done">
<h1>Recorded</h1><p class="sub">%(what)s</p>
<p class="meta">%(file)s</p><p class="sub">You can close this tab.</p>
</div></body></html>"""


# ------------------------------------------------------------------ recording
def next_id() -> str:
    DECISIONS.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in DECISIONS.glob("DEC-*.yaml"):
        m = re.match(r"DEC-(\d+)", f.stem)
        if m:
            n = max(n, int(m.group(1)))
    return f"DEC-{n + 1:03d}"


def validate_answer(form: dict, q: dict) -> list:
    errs = []
    choice = (form.get("choice") or "").strip()
    who = (form.get("who") or "").strip()
    why = (form.get("why") or "").strip()
    ids = {o["id"] for o in q["options"]} | {"combine", "reject"}
    if choice not in ids:
        errs.append("Pick one of the options, or Combine, or Reject all. "
                    "Nothing is recorded without a choice.")
    if not who:
        errs.append("Say who is deciding. An approval with no author cannot be "
                    "weighed later and cannot gate anything.")
    elif SELF.search(who):
        errs.append(f"“{who}” names the party that produced these comps. "
                    f"The agent proposing a direction cannot also be the authority "
                    f"approving it — that is the whole reason this page exists.")
    if EMPTY_REASON.match(why):
        errs.append(f"\u201c{why}\u201d does not say anything the next person can "
                    f"use. Say what this option does that the others do not.")
    elif len(why) < MIN_REASON:
        errs.append("Say a little more \u2014 what does this option do that the "
                    "others do not?")
    if choice == "combine":
        low = why.lower()
        named = [o["id"] for o in q["options"]
                 if re.search(rf"\b{re.escape(o['id'].lower())}\b", low)]
        if not named and "both" not in low and "each" not in low:
            errs.append("Say which parts come from which option. The options are "
                        + ", ".join(o["id"] for o in q["options"])
                        + ", and the next round is built from this sentence.")
    return errs


def record(form: dict, q: dict) -> Path:
    did = next_id()
    rec = {
        "id": did,
        "question": q["question"],
        "surface": q["surface"],
        "chosen": form["choice"].strip(),
        "who": form["who"].strip(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rationale": form["why"].strip(),
        "options_sha": options_sha(q),
        "contract_sha": q.get("contract_sha"),
        "brief_sha": q.get("brief_sha"),
        "contract_undeclared_at_decision": q.get("contract_undeclared") or [],
        "shown": [{"id": o["id"], "title": o["title"], "image": o["image"],
                   "image_sha": file_sha(Path(o["image"])) if o["image"] else None}
                  for o in q["options"]],
        "source": q["source"],
        "recorded_by": "deluxui/scripts/ux_question.py (served page, human submitted)",
    }
    DECISIONS.mkdir(parents=True, exist_ok=True)
    p = DECISIONS / f"{did}.yaml"
    p.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=92))
    return p


# --------------------------------------------------------------------- server
class State:
    def __init__(self, q, th):
        self.q, self.th = q, th
        self.result: Path | None = None
        self.done = threading.Event()


def handler_for(st: State):
    class H(BaseHTTPRequestHandler):
        server_version = "deluxui"

        def log_message(self, *a):        # the page is the output, not the log
            pass

        def _send(self, body: bytes, ctype="text/html; charset=utf-8", code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                return self._send(page(st.q, st.th).encode())
            m = re.fullmatch(r"/asset/(\d+)", u.path)
            if m:
                # Index into the options that were declared. Never a path from the
                # request: this process can read the whole working tree, and a
                # decision page is not a file server.
                i = int(m.group(1))
                if 0 <= i < len(st.q["options"]) and st.q["options"][i]["image"]:
                    p = Path(st.q["options"][i]["image"])
                    try:
                        return self._send(p.read_bytes(),
                                          MIME.get(p.suffix.lower(),
                                                   "application/octet-stream"))
                    except OSError:
                        pass
                return self._send(b"no such asset", "text/plain", 404)
            return self._send(b"not found", "text/plain", 404)

        def do_POST(self):
            if urlparse(self.path).path != "/answer":
                return self._send(b"not found", "text/plain", 404)
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(min(n, 200_000)).decode("utf-8", "replace")
            form = {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}
            errs = validate_answer(form, st.q)
            if errs:
                return self._send(page(st.q, st.th, errs, form).encode(), code=422)
            st.result = record(form, st.q)
            body = DONE % {"css": CSS % st.th,
                           "what": html.escape(f"{form['choice']} — recorded as "
                                               f"{st.result.stem}"),
                           "file": html.escape(str(st.result))}
            self._send(body.encode())
            threading.Thread(target=lambda: (time.sleep(0.4), st.done.set()),
                             daemon=True).start()
    return H


def free_port(host: str, want: int) -> int:
    for p in [want] + list(range(want + 1, want + 40)):
        with socket.socket() as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise SystemExit("no free port in range")


def cmd_ask(a) -> int:
    src = Path(a.file)
    if not src.exists():
        sys.stderr.write(f"{src} does not exist. Render comps first:\n"
                         f"  python3 scripts/ux_image.py render <brief.yaml>\n")
        return 2
    q = load_question(src)
    if not q["options"]:
        sys.stderr.write(f"{src} declares no options. One comp is not a decision.\n")
        return 2
    missing = [o["image"] for o in q["options"]
               if o["image"] and not Path(o["image"]).exists()]
    if missing:
        sys.stderr.write("these comps do not exist on disk:\n  "
                         + "\n  ".join(missing) + "\n")
        return 2
    st = State(q, theme())
    port = free_port(a.host, a.port)
    srv = ThreadingHTTPServer((a.host, port), handler_for(st))
    url = f"http://{a.host}:{port}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    sys.stderr.write(
        f"\n  {q['question']}\n\n  Open this and decide:  {url}\n\n"
        f"  {len(q['options'])} option(s), plus combine and reject.\n"
        f"  Waiting up to {a.timeout}s. Nothing is recorded until somebody submits,\n"
        f"  and a timeout records nothing rather than defaulting to the first one.\n\n")
    if a.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    ok = st.done.wait(timeout=a.timeout)
    srv.shutdown()
    if not ok or not st.result:
        sys.stderr.write(
            "\nNobody answered inside the timeout, so nothing was recorded. The "
            "direction is undecided -- which is a real state, and the phase gate "
            "will keep saying so until someone decides.\n")
        return 3
    rec = yaml.safe_load(st.result.read_text())
    sys.stderr.write(f"\nRecorded {st.result}\n  chosen: {rec['chosen']}\n"
                     f"  who:    {rec['who']} on {rec['date']}\n"
                     f"  why:    {rec['rationale'][:160]}\n")
    print(str(st.result))
    return 0


def cmd_list(a) -> int:
    got = sorted(DECISIONS.glob("DEC-*.yaml"))
    if not got:
        sys.stderr.write("No decisions recorded. Nothing has been approved, which is "
                         "different from nothing having been asked.\n")
        return 0
    for f in got:
        d = yaml.safe_load(f.read_text()) or {}
        sys.stderr.write(f"{d.get('id')}  {d.get('date')}  {d.get('chosen'):<10} "
                         f"{str(d.get('who'))[:20]:<20} {str(d.get('question'))[:60]}\n")
    return 0


def cmd_show(a) -> int:
    f = DECISIONS / f"{a.id}.yaml"
    if not f.exists():
        sys.stderr.write(f"{f} does not exist\n")
        return 2
    print(f.read_text())
    return 0


def cmd_check(a) -> int:
    """Every recorded approval still matches the files it approved."""
    got = sorted(DECISIONS.glob("DEC-*.yaml"))
    if not got:
        sys.stderr.write("No decisions recorded.\n")
        return 0
    stale = []
    for f in got:
        d = yaml.safe_load(f.read_text()) or {}
        for s in d.get("shown") or []:
            if not s.get("image"):
                continue
            now = file_sha(Path(s["image"]))
            if now is None:
                stale.append(f"{d['id']}: {s['image']} no longer exists, so what was "
                             f"approved cannot be produced")
            elif s.get("image_sha") and now != s["image_sha"]:
                stale.append(f"{d['id']}: {s['image']} has changed since it was "
                             f"approved ({s['image_sha']} -> {now}). The approval is "
                             f"for the old file; re-serve the decision or restore it")
    for s in stale:
        sys.stderr.write(f"  STALE  {s}\n")
    sys.stderr.write(f"\n{len(got)} decision(s), {len(stale)} stale.\n")
    return 2 if stale else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    k = sub.add_parser("ask")
    k.add_argument("file")
    k.add_argument("--port", type=int, default=8787)
    k.add_argument("--host", default="127.0.0.1")
    k.add_argument("--timeout", type=int, default=1800)
    k.add_argument("--open", action="store_true", help="try to open a browser")
    k.set_defaults(fn=cmd_ask)
    for nm, fn in (("list", cmd_list), ("check", cmd_check)):
        s = sub.add_parser(nm)
        s.set_defaults(fn=fn)
    s = sub.add_parser("show")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 1
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
