#!/usr/bin/env python3
"""Point at the running app, and have the pointing land as a record.

The most valuable input in interface work is a person looking at the real thing
and saying "that". It is also the input that evaporates fastest: it arrives as
"the spacing on the card feels off", the agent guesses which card, and the
correction is lost by the next message.

This injects a selection overlay into the page the browser already has open.
Hovering outlines an element; clicking captures it — its selector, its computed
type, colour, spacing, radius and shadow, its box, and the viewport it was seen
at — and asks what is wrong with it in the vocabulary the operations already use.
Each answer becomes `.deuxui/requests/REQ-NNN.yaml`, which names an operation and
an element rather than a feeling.

It needs no server and no framework adapter. The overlay keeps its queue on
`window.__uxSelect`, and this process reads it over the Chrome DevTools
Protocol — the same channel `ux_forcedcolors.py` and `ux_slow.py` use, because
`agent-browser get cdp-url` publishes the browser's own endpoint.

What it deliberately does not do: patch the DOM with a generated variant. The
change belongs in the source, where the dev server's own hot reload will show it
and `ux_live.sh` will measure the delta. A variant that exists only in the page
has to be committed back later, and that round trip is where an edit gets lost.

    ux_select.py watch [--timeout 1800] [--out .deuxui/requests]
    ux_select.py list
    ux_select.py clear

Exit: 0 something was captured, 2 the browser could not be reached, 3 nobody
pointed at anything.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yaml                                                        # noqa: E402
import cdp                                                         # noqa: E402

REQUESTS = Path(".deuxui/requests")

# The actions are the operation names, so a request routes straight into a move
# that already exists rather than into a conversation about what was meant.
ACTIONS = [
    ("bolder", "Too quiet — it should carry more weight"),
    ("quieter", "Too loud — it is competing with something more important"),
    ("distill", "Too much here — remove what is not doing work"),
    ("clarify", "I cannot tell what this is or what it does"),
    ("layout", "The arrangement is wrong — order, alignment, or proportion"),
    ("space", "The spacing is wrong — cramped, loose, or grouping the wrong things"),
    ("colorize", "The colour is wrong, or I cannot read it"),
    ("typeset", "The type is wrong — size, weight, leading, or measure"),
    ("polish", "Nearly right; the details are off"),
    ("broken", "This is a defect, not a preference"),
]

OVERLAY = r"""
(() => {
  if (window.__uxSelect) { window.__uxSelect.active = true; return "already"; }
  const S = window.__uxSelect = { queue: [], active: true, version: 1 };
  const ACTIONS = __ACTIONS__;

  const css = document.createElement('style');
  css.textContent = `
  .uxsel-hi{position:fixed;pointer-events:none;z-index:2147483646;
    outline:2px solid #2f6fed;outline-offset:1px;background:rgba(47,111,237,.10)}
  .uxsel-tag{position:fixed;z-index:2147483647;pointer-events:none;
    font:600 11px/1.4 ui-monospace,monospace;background:#2f6fed;color:#fff;
    padding:2px 6px;border-radius:3px;white-space:nowrap}
  .uxsel-panel{position:fixed;z-index:2147483647;right:16px;bottom:16px;width:330px;
    max-height:80vh;overflow:auto;background:#fff;color:#16181d;
    font:14px/1.5 system-ui,sans-serif;border:1px solid #d8d8d4;border-radius:12px;
    box-shadow:0 12px 40px rgba(0,0,0,.18);padding:16px}
  .uxsel-panel h2{font:650 15px/1.3 system-ui;margin:0 0 4px}
  .uxsel-panel p.sel{font:12px/1.4 ui-monospace,monospace;color:#5d6068;
    margin:0 0 12px;word-break:break-all}
  .uxsel-panel button.act{display:block;width:100%;text-align:left;margin:0 0 6px;
    padding:9px 11px;min-height:40px;font:inherit;background:#f7f7f5;
    border:1px solid #dcdcd8;border-radius:8px;cursor:pointer}
  .uxsel-panel button.act:hover{background:#eceaff}
  .uxsel-panel button.act:focus-visible{outline:3px solid #2f6fed;outline-offset:2px}
  .uxsel-panel textarea{width:100%;min-height:74px;font:inherit;padding:8px;
    border:1px solid #cfcfca;border-radius:8px;margin:6px 0}
  .uxsel-panel .row{display:flex;gap:8px}
  .uxsel-panel .row button{flex:1;padding:11px;min-height:44px;font:600 14px system-ui;
    border-radius:8px;border:0;cursor:pointer}
  .uxsel-send{background:#2f6fed;color:#fff}
  .uxsel-cancel{background:#eee;color:#16181d}
  .uxsel-badge{position:fixed;z-index:2147483647;left:16px;bottom:16px;
    font:600 12px/1 ui-monospace,monospace;background:#16181d;color:#fff;
    padding:9px 12px;border-radius:999px;box-shadow:0 4px 14px rgba(0,0,0,.25)}
  @media (prefers-color-scheme:dark){
    .uxsel-panel{background:#1d1c19;color:#f3efe6;border-color:#3b382f}
    .uxsel-panel button.act{background:#26241f;color:#f3efe6;border-color:#413d34}
    .uxsel-panel textarea{background:#26241f;color:#f3efe6;border-color:#4a453a}
    .uxsel-cancel{background:#3a362e;color:#f3efe6}}
  `;
  document.head.appendChild(css);

  const hi = document.createElement('div'); hi.className = 'uxsel-hi';
  const tag = document.createElement('div'); tag.className = 'uxsel-tag';
  const badge = document.createElement('div'); badge.className = 'uxsel-badge';
  badge.textContent = 'deuxui · click anything · Esc to stop';
  document.body.appendChild(badge);
  let panel = null, target = null;

  const isOurs = n => n && n.closest && (n.closest('.uxsel-panel') || n === badge
                  || n === hi || n === tag);

  function selectorFor(el) {
    // Short, stable, and readable by a person grepping the source. An id wins; a
    // test id wins next; otherwise a class path with nth-of-type where needed.
    if (el.id) return '#' + el.id;
    const t = el.getAttribute('data-testid') || el.getAttribute('data-test');
    if (t) return `[data-testid="${t}"]`;
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && parts.length < 4 && n !== document.body) {
      let p = n.tagName.toLowerCase();
      const cls = (n.getAttribute('class') || '').trim().split(/\s+/)
        .filter(c => c && !/^(uxsel|ng-|css-[0-9a-z]{4,})/.test(c)).slice(0, 3);
      if (cls.length) p += '.' + cls.join('.');
      const sibs = n.parentElement
        ? [...n.parentElement.children].filter(x => x.tagName === n.tagName) : [];
      if (sibs.length > 1) p += `:nth-of-type(${sibs.indexOf(n) + 1})`;
      parts.unshift(p);
      n = n.parentElement;
    }
    return parts.join(' > ');
  }

  function describe(el) {
    const c = getComputedStyle(el), r = el.getBoundingClientRect();
    const txt = (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 120);
    return {
      selector: selectorFor(el), tag: el.tagName.toLowerCase(),
      role: el.getAttribute('role') || null,
      classes: (el.getAttribute('class') || '').slice(0, 200),
      text: txt,
      box: {x: Math.round(r.x), y: Math.round(r.y),
            w: Math.round(r.width), h: Math.round(r.height)},
      computed: {
        fontSize: c.fontSize, fontWeight: c.fontWeight, fontFamily: c.fontFamily,
        lineHeight: c.lineHeight, letterSpacing: c.letterSpacing,
        color: c.color, background: c.backgroundColor, backgroundImage:
          c.backgroundImage === 'none' ? null : c.backgroundImage.slice(0, 120),
        padding: c.padding, margin: c.margin, gap: c.gap,
        borderRadius: c.borderRadius, border: c.border,
        boxShadow: c.boxShadow === 'none' ? null : c.boxShadow.slice(0, 160),
        display: c.display, position: c.position, zIndex: c.zIndex,
        width: c.width, height: c.height,
      },
      viewport: {w: innerWidth, h: innerHeight, dpr: devicePixelRatio},
      url: location.href,
    };
  }

  function place(el) {
    const r = el.getBoundingClientRect();
    hi.style.cssText += `;left:${r.x}px;top:${r.y}px;width:${r.width}px;height:${r.height}px`;
    if (!hi.isConnected) { document.body.appendChild(hi); document.body.appendChild(tag); }
    tag.textContent = `${el.tagName.toLowerCase()} ${Math.round(r.width)}×${Math.round(r.height)}`;
    tag.style.left = r.x + 'px';
    tag.style.top = (r.y > 22 ? r.y - 22 : r.y + r.height + 4) + 'px';
  }

  function openPanel(info) {
    closePanel();
    panel = document.createElement('div');
    panel.className = 'uxsel-panel';
    panel.innerHTML =
      '<h2>What is wrong with this?</h2><p class="sel"></p>' +
      ACTIONS.map(([id, label]) =>
        `<button class="act" data-a="${id}">${label}</button>`).join('') +
      '<textarea placeholder="Anything else worth saying (optional)"></textarea>' +
      '<div class="row"><button class="uxsel-cancel">Cancel</button></div>';
    panel.querySelector('p.sel').textContent = info.selector;
    panel.querySelectorAll('button.act').forEach(b => b.onclick = () => {
      S.queue.push(Object.assign({}, info, {
        action: b.dataset.a,
        note: panel.querySelector('textarea').value.trim(),
        at: new Date().toISOString(),
      }));
      badge.textContent = `deuxui · ${S.queue.length} captured · Esc to stop`;
      closePanel();
    });
    panel.querySelector('.uxsel-cancel').onclick = closePanel;
    document.body.appendChild(panel);
    panel.querySelector('button.act').focus();
  }
  function closePanel() { if (panel) { panel.remove(); panel = null; } }

  addEventListener('mousemove', e => {
    if (!S.active || panel) return;
    const el = e.target;
    if (isOurs(el)) return;
    target = el; place(el);
  }, true);

  addEventListener('click', e => {
    if (!S.active || isOurs(e.target)) return;
    e.preventDefault(); e.stopPropagation();
    openPanel(describe(e.target));
  }, true);

  addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      if (panel) return closePanel();
      S.active = false; hi.remove(); tag.remove();
      badge.textContent = `deuxui · stopped · ${S.queue.length} captured`;
    }
  }, true);
  return "installed";
})()
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_id() -> str:
    REQUESTS.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in REQUESTS.glob("REQ-*.yaml"):
        m = re.match(r"REQ-(\d+)", f.stem)
        if m:
            n = max(n, int(m.group(1)))
    return f"REQ-{n + 1:03d}"


def write(rec: dict) -> Path:
    rid = next_id()
    out = dict(rec)
    out["id"] = rid
    out["recorded_at"] = now()
    out["recorded_by"] = ("deuxui/scripts/ux_select.py -- a person pointed at this "
                          "element in the running app")
    p = REQUESTS / f"{rid}.yaml"
    p.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=92))
    return p


def cmd_watch(a) -> int:
    ws, target = cdp.connect_page(getattr(a, 'url', None))
    if ws is None:
        sys.stderr.write(
            f"{target}\n\nStart the app and open it:\n"
            f"  agent-browser open <url>\n"
            f"Then run this again. Nothing is captured and nothing is claimed.\n")
        return 2
    js = OVERLAY.replace("__ACTIONS__", json.dumps(ACTIONS))
    try:
        state = cdp.evaluate(ws, js)
    except RuntimeError as e:
        sys.stderr.write(f"the overlay would not install: {e}\n")
        ws.close()
        return 2
    url = (target or {}).get("url", "")
    sys.stderr.write(
        f"\n  Overlay {state} on {url}\n\n"
        f"  Hover to outline, click to capture, Esc to stop.\n"
        f"  Each capture records the element, its computed type, colour, spacing,\n"
        f"  radius and shadow, its box and the viewport it was seen at.\n"
        f"  Waiting up to {a.timeout}s. Nothing is invented if nobody points.\n\n")
    seen, deadline = 0, time.time() + a.timeout
    made = []
    try:
        while time.time() < deadline:
            time.sleep(1.0)
            try:
                q = cdp.evaluate(ws, "JSON.stringify(window.__uxSelect ? "
                                     "{q: window.__uxSelect.queue, a: "
                                     "window.__uxSelect.active} : null)")
            except RuntimeError:
                # A navigation drops the overlay with the page. Re-install rather
                # than exiting: moving between routes is how someone reviews an
                # app, and treating it as an error loses everything they were
                # about to say.
                try:
                    cdp.evaluate(ws, js)
                    sys.stderr.write("  (page navigated; overlay re-installed)\n")
                except RuntimeError:
                    break
                continue
            if not q:
                try:
                    cdp.evaluate(ws, js)
                except RuntimeError:
                    break
                continue
            items = q.get("q") or []
            for rec in items[seen:]:
                p = write(rec)
                made.append((p, rec))
                sys.stderr.write(f"  {p.stem}  {rec['action']:<9} {rec['selector'][:60]}\n")
            seen = len(items)
            if not q.get("a") and seen:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            cdp.evaluate(ws, "window.__uxSelect && (window.__uxSelect.active=false)")
        except Exception:
            pass
        ws.close()

    if not made:
        sys.stderr.write(
            "\nNobody pointed at anything, so nothing was recorded. That is NOT_RUN, "
            "not agreement -- an unreviewed screen is not a reviewed one.\n")
        return 3
    sys.stderr.write(f"\n{len(made)} request(s) in {REQUESTS}/\n\n"
                     "Each names an operation and an element. Read the operation, find "
                     "the element in the source (the selector and the text are both "
                     "there), make the change, and let the dev server reload it. Then "
                     "measure what moved:\n"
                     "  bash scripts/ux_live.sh <url>\n")
    for p, rec in made:
        sys.stderr.write(f"  {p.stem}: references/ops/{_op_file(rec['action'])}\n")
    return 0


def _op_file(action: str) -> str:
    return {"space": "layout.md", "broken": "../verification/static-checks.md",
            "layout": "layout.md"}.get(action, f"{action}.md")


def cmd_list(a) -> int:
    got = sorted(REQUESTS.glob("REQ-*.yaml"))
    if not got:
        sys.stderr.write("No requests recorded.\n")
        return 0
    for f in got:
        d = yaml.safe_load(f.read_text()) or {}
        sys.stderr.write(f"{d.get('id')}  {d.get('action'):<9} "
                         f"{str(d.get('selector'))[:52]:<52} {str(d.get('note'))[:40]}\n")
    return 0


def cmd_clear(a) -> int:
    got = sorted(REQUESTS.glob("REQ-*.yaml"))
    for f in got:
        f.unlink()
    sys.stderr.write(f"removed {len(got)} request(s)\n")
    return 0


def main(argv=None) -> int:
    global REQUESTS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("watch")
    w.add_argument("--timeout", type=int, default=1800)
    w.add_argument("--url", help="the page under test. Without it the overlay goes "
                                 "into whichever tab is first, which is wrong the "
                                 "moment two are open.")
    w.add_argument("--out", default=str(REQUESTS))
    w.set_defaults(fn=cmd_watch)
    for nm, fn in (("list", cmd_list), ("clear", cmd_clear)):
        s = sub.add_parser(nm)
        s.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 1
    if getattr(a, "out", None):
        REQUESTS = Path(a.out)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
