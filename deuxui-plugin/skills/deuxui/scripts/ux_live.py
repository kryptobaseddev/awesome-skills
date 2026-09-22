#!/usr/bin/env python3
"""Pick an element in the running app, compare variants in place, accept one into
the source.

    ux_live.py pick                         point at it; capture it and find it in source
    ux_live.py vary REQ-001 [--count 3]     variants, every value taken from the contract
    ux_live.py show REQ-001                 all of them in the real page, with a switcher
    ux_live.py accept REQ-001 --variant B   check it, write it, record it
    ux_live.py status | discard REQ-001

The loop this closes is the one nobody automates: a person looks at the real screen,
says "that bit", sees two or three honest alternatives *in place* rather than in a
mock, picks one, and the pick lands in the source. Everything before this in the
skill either measured an existing screen or generated a separate artefact to look at.

Four things make this different from a visual editor, and they are the reason it
exists rather than being a nicer devtools panel.

**A variant can only propose declared values.** Every size comes off the type
ladder, every colour is a role, every gap is on the spacing scale, every raise uses
the one declared depth metaphor. So the variants are conformant by construction and
a person choosing between them cannot accidentally choose drift. A generator free to
propose anything would turn this into the fastest way yet to leave the system.

**One axis at a time.** Three variants that each change type, colour, spacing and
depth together cannot tell you which change did the work; the answer to "why did you
pick B" becomes "it looked better", which is not a decision anyone can build on.
Each variant names the single axis it moves.

**Ambiguous source refuses.** Writing to the wrong line is worse than not writing,
because the wrong line still looks like success. The element has to resolve to
exactly one place in the source by a distinctive anchor. Zero matches or several,
and this says which and stops.

**Accept is measured, not just chosen.** The edit is applied to a copy, the static
tier runs against it, and a variant that introduces a P0 or P1 finding is refused
with the finding quoted. Taste chooses between admissible options; it does not get
to make an inadmissible one admissible.
"""
from __future__ import annotations
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yaml                                                        # noqa: E402
import cdp                                                         # noqa: E402
import ux_select                                                   # noqa: E402
import ux_image                                                    # noqa: E402
import uxconfig                                                    # noqa: E402

ROOT = Path(".deuxui")
LIVE = ROOT / "live"
REQUESTS = ROOT / "requests"
DECISIONS = ROOT / "decisions"
SKIP = {"node_modules", ".git", "dist", "build", ".next", ".svelte-kit", "out",
        "coverage", ".venv", "venv", "__pycache__", ".turbo", ".cache", ".deuxui",
        "target", "Pods", ".gradle"}
SPLIT = "[" + "\n" + "\u2022|\u00b7" + "]|\\s{2,}"
SRC_EXT = {".tsx", ".jsx", ".ts", ".js", ".svelte", ".vue", ".astro", ".html", ".htm"}
STYLE_EXT = {".css", ".scss", ".sass", ".less"}
# Where a lookup key for a piece of visible copy lives, as opposed to where the copy
# itself is rendered. Only `coupled()` reads this set; nothing is ever located here.
COUPLED_EXT = {".json", ".yaml", ".yml", ".toml", ".md", ".mdx", ".txt", ".csv",
               ".py", ".rb", ".go", ".java", ".kt", ".swift", ".php", ".cs", ".rs"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def w(s: str) -> None:
    sys.stderr.write(s)


def _next_id(d: Path, prefix: str) -> str:
    n = 0
    if d.exists():
        for p in d.glob(f"{prefix}-*.yaml"):
            m = re.fullmatch(rf"{prefix}-(\d+)", p.stem)
            if m:
                n = max(n, int(m.group(1)))
    return f"{prefix}-{n + 1:03d}"


def load(p: Path):
    try:
        return yaml.safe_load(p.read_text(errors="replace"))
    except (OSError, yaml.YAMLError):
        return None


def _rel(q: Path, root: Path) -> str:
    """`q` as the project sees it, or its own path when it is outside the project."""
    try:
        return str(q.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(q)


def session(rid: str) -> Path:
    return LIVE / f"{rid}.yaml"


# ------------------------------------------------------------------ the source
def iter_files(root: Path, exts: set, limit=8000):
    n = 0
    for p in sorted(root.rglob("*")):
        if n >= limit:
            return
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if any(part in SKIP for part in p.relative_to(root).parts):
            continue
        n += 1
        yield p


def anchors(rec: dict) -> list:
    """Distinctive strings to find this element by, strongest first.

    Text beats class, because a person picked the element they could read and the
    words are what they were looking at. A class is next. A tag name alone is never
    an anchor -- `<div>` is not a location."""
    out = []
    txt = str(rec.get("text") or "").strip()
    if len(txt) >= 8:
        # innerText concatenates children, so the captured run almost never appears
        # contiguously in source: "Boiler service at 14 Mill Lane Due Friday" is an h3
        # and a p, and searching for the whole string found nothing -- while the
        # element's class was ambiguous. So the strongest anchor went unused and the
        # location was refused. Progressively shorter prefixes, longest first: the
        # longest one that appears is the most specific anchor available.
        first = re.split(SPLIT, txt)[0].strip()
        words = first.split()
        for n in range(len(words), 1, -1):
            cand = " ".join(words[:n])
            if len(cand) >= 8:
                out.append(("text", cand[:70]))
            if sum(1 for o in out if o[0] == "text") >= 5:
                break
    for cls in str(rec.get("classes") or "").split():
        if len(cls) >= 6 and not re.fullmatch(r"[a-z]+-\d+", cls):
            out.append(("class", cls))
    return out[:10]


def locate(rec: dict, root: Path | None = None) -> dict:
    """Exactly one place in the source, or an explanation and no location.

    This is the gate on the whole write path. A visual tool that guesses the file
    writes a plausible edit to the wrong component, the page does not change, and the
    next twenty minutes go on wondering why -- so a guess is worse than a refusal."""
    root = root or Path.cwd()
    tried = []
    for kind, needle in anchors(rec):
        hits = []
        for p in iter_files(root, SRC_EXT):
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            for m in re.finditer(re.escape(needle), text):
                line = text[:m.start()].count("\n") + 1
                hits.append({"file": str(p.relative_to(root)), "line": line})
                if len(hits) > 8:
                    break
            if len(hits) > 8:
                break
        tried.append({"anchor": needle, "kind": kind, "hits": len(hits)})
        if len(hits) == 1:
            return {"found": True, "anchor": needle, "anchor_kind": kind, **hits[0],
                    "tried": tried}
        if len(hits) > 1:
            continue
    return {"found": False, "tried": tried,
            "why": ("no anchor in this element resolved to exactly one place in the "
                    "source. Give the element a distinctive class, or name the file "
                    "yourself with --file.")}


# ----------------------------------------------------------------- the variants
def token_map(root: Path | None = None) -> dict:
    """Declared colour value -> the project's own custom property for it.

    Written because the check caught this generator drifting. A variant that emitted
    `background-color: #1b5fd9` used a value the contract declares, and still added
    two S-CONTRACT-COLOR findings: a literal in a rule is a token that escaped, it
    will not follow the theme, it will not flip in dark mode, and nobody will find it
    again. The value being *declared* is not the same as the value being *referenced*.

    Matched by value first, then by the `--color-<role>` convention, so a project
    naming its properties something else still gets references rather than hex."""
    try:
        from checks._util import collect_css_vars
        vars_ = collect_css_vars(root or Path.cwd())
    except Exception:
        return {}
    by_value = {}
    for name, val in vars_.items():
        v = str(val).strip().lower()
        if v and v not in by_value:
            by_value[v] = name
    return by_value


def as_token(value: str, tokens: dict, role: str | None = None) -> str:
    """`var(--x)` where the project has one for this value, else the literal."""
    v = str(value).strip().lower()
    if v in tokens:
        return f"var({tokens[v]})"
    if role:
        for cand in (f"--color-{role}", f"--{role}"):
            if cand in {n for n in tokens.values()} or cand in tokens:
                return f"var({cand})"
    return value


def _rung(c, which: str) -> float:
    return c.rung(which) if hasattr(c, "rung") else 16.0


def axes(c, rec: dict, tokens: dict | None = None) -> list:
    """The axes a variant may move, each entirely inside the declaration.

    Returned as (axis, title, what it decides, {property: value}) so the page can
    label every variant with the one thing it changes. The values are read off the
    contract -- the ladder, the roles, the scale, the metaphor -- which is what makes
    "conformant by construction" a property of this generator rather than a claim."""
    comp = rec.get("computed") or {}
    tokens = tokens if tokens is not None else token_map()
    tk = lambda v, role=None: as_token(v, tokens, role)
    out = []
    ladder = sorted(c.scale)
    cur = 16.0
    m = re.match(r"([\d.]+)", str(comp.get("fontSize") or ""))
    if m:
        cur = float(m.group(1))
    nearest = min(range(len(ladder)), key=lambda i: abs(ladder[i] - cur))

    # Leading by size, not a constant. A hardcoded 1.2 produced a real
    # S-TYPE-LEADING finding on a 20px rung: under 24px this tool's own craft floor
    # wants 1.4 or more, because tighter crowds descenders and WCAG's text-spacing
    # criterion expects 1.5 to survive. The generator has to obey the floor it
    # enforces, or accepting a variant means accepting a fresh finding.
    lead = lambda px: "1.2" if px >= 24 else "1.5"

    up = ladder[min(nearest + 1, len(ladder) - 1)]
    if abs(up - cur) > 0.5:
        out.append(("type-up", "One rung louder",
                    "whether this element is carrying enough weight in the hierarchy",
                    {"font-size": f"{up:g}px", "line-height": lead(up)}))
    down = ladder[max(nearest - 1, 0)]
    if abs(down - cur) > 0.5:
        out.append(("type-down", "One rung quieter",
                    "whether this element is competing with what it should support",
                    {"font-size": f"{down:g}px", "line-height": lead(down)}))

    space = [s for s in (c.raw.get("spacing") or {}).get("scale") or [] if s]
    if space:
        sp = sorted(float(x) for x in space)
        looser = sp[min(len(sp) - 1, max(0, len(sp) // 2 + 1))]
        tighter = sp[max(0, len(sp) // 2 - 1)]
        out.append(("space-loose", "More air",
                    "whether the density is working against the reading",
                    {"padding": f"{looser:g}px", "gap": f"{looser:g}px"}))
        out.append(("space-tight", "Tighter",
                    "whether the grouping reads as one thing",
                    {"padding": f"{tighter:g}px", "gap": f"{tighter:g}px"}))

    roles = c.roles
    if "surface" in roles and "canvas" in roles:
        out.append(("surface", "Lifted onto a surface",
                    "whether this element is part of the page or sits on top of it",
                    {"background-color": tk(roles["surface"], "surface"),
                     "color": tk(roles["ink"], "ink")}))
    if "interactive" in roles:
        out.append(("emphasis", "Carries the accent",
                    "whether this is the thing the visitor is meant to act on",
                    {"background-color": tk(roles["interactive"], "interactive"),
                     "color": tk(roles["canvas"], "canvas")}))

    elevs = [e for e in (c.raw.get("depth") or {}).get("elevations") or [] if e]
    if c.depth == "shadow":
        val = str(elevs[min(1, len(elevs) - 1)]) if elevs else "0 1px 3px rgba(0,0,0,.12)"
        out.append(("depth", "Raised, by the declared metaphor",
                    "whether this element is above the page or on it",
                    {"box-shadow": val, "border": "0"}))
    else:
        val = str(elevs[0]) if elevs else f"1px solid {tk(roles.get('muted', '#e5e5e5'), 'muted')}"
        out.append(("depth", "Bounded, by the declared metaphor",
                    "whether this element needs an edge to be read as a unit",
                    {"border": val, "box-shadow": "none"}))

    out.append(("radius-card", "Card radius",
                "whether this reads as a control or as a container",
                {"border-radius": f"{c.r_card:g}px"}))
    out.append(("radius-control", "Control radius",
                "whether this reads as a control or as a container",
                {"border-radius": f"{c.r_control:g}px"}))
    return out


_DIRECTION = {
    "bolder": ["type-up", "emphasis", "depth"],
    "louder": ["type-up", "emphasis"],
    "quieter": ["type-down", "space-loose"],
    "calmer": ["type-down", "space-loose"],
    "tighter": ["space-tight", "radius-control"],
    "denser": ["space-tight"],
    "roomier": ["space-loose"],
    "lift": ["surface", "depth"],
    "raise": ["surface", "depth"],
    "flatter": ["depth", "radius-control"],
}


def steer(pool: list, direction: str | None, count: int) -> list:
    """Honour a plain-language steer without inventing an axis for it.

    A direction nobody has an axis for is reported rather than approximated: three
    variants labelled "brutalist" that are really just three font sizes is the kind of
    thing that makes a person stop trusting the labels."""
    if not direction:
        return pool[:count]
    words = re.findall(r"[a-z]+", direction.lower())
    want, unmatched = [], []
    for word in words:
        keys = _DIRECTION.get(word)
        if keys:
            want += keys
        elif len(word) > 3:
            unmatched.append(word)
    ranked = [a for k in want for a in pool if a[0] == k]
    seen, out = set(), []
    for a in ranked + pool:
        if a[0] in seen:
            continue
        seen.add(a[0])
        out.append(a)
    if unmatched and not ranked:
        w(f"\n  No axis matches {' '.join(unmatched)!r}, so the variants below are the "
          f"default set rather than an interpretation of it. The axes this can move "
          f"are: {', '.join(sorted({a[0] for a in pool}))}.\n")
    return out[:count]


def build_variants(rec: dict, c, count: int, direction: str | None) -> list:
    picked = steer(axes(c, rec, token_map()), direction, count)
    out = []
    for i, (axis, title, decides, decls) in enumerate(picked):
        out.append({"id": chr(ord("A") + i), "axis": axis, "title": title,
                    "decides": decides, "declarations": decls,
                    "css": "; ".join(f"{k}: {v}" for k, v in decls.items())})
    return out


# ------------------------------------------------------------------- in the page
OVERLAY = r"""
(() => {
  const S = window.__uxLive = window.__uxLive || {};
  S.sel = %(sel)s; S.variants = %(variants)s; S.rid = %(rid)s; S.chosen = null;
  const el = document.querySelector(S.sel);
  if (!el) return JSON.stringify({ok:false, why:"the element is no longer on this page"});
  if (!S.original) S.original = el.getAttribute('style') || '';
  const apply = v => {
    el.setAttribute('style', (S.original ? S.original + '; ' : '') + (v ? v.css : ''));
  };
  document.getElementById('ux-live-bar')?.remove();
  const bar = document.createElement('div');
  bar.id = 'ux-live-bar';
  bar.setAttribute('style', [
    'position:fixed','left:50%%','bottom:20px','transform:translateX(-50%%)','z-index:2147483647',
    'font:13px/1.45 ui-sans-serif,system-ui,sans-serif','background:#14161b','color:#f4f4f5',
    'border-radius:12px','padding:10px 12px','box-shadow:0 8px 30px rgba(0,0,0,.45)',
    'display:flex','gap:8px','align-items:center','max-width:min(94vw,860px)','flex-wrap:wrap'
  ].join(';'));
  const label = document.createElement('span');
  label.textContent = S.rid;
  label.setAttribute('style','opacity:.6;font-variant-numeric:tabular-nums');
  bar.appendChild(label);
  const note = document.createElement('span');
  note.setAttribute('style','opacity:.85;flex:1 1 220px;min-width:180px');
  note.textContent = 'Pick one. Nothing is written until you accept it in the terminal.';
  const mk = (text, v) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = text;
    b.setAttribute('style', [
      'font:inherit','cursor:pointer','border-radius:8px','padding:6px 10px',
      'border:1px solid #3f3f46','background:#1f2228','color:inherit'
    ].join(';'));
    b.onclick = () => {
      apply(v); S.chosen = v ? v.id : null;
      [...bar.querySelectorAll('button')].forEach(x => {
        x.style.background = '#1f2228'; x.style.borderColor = '#3f3f46';
      });
      b.style.background = '#2f6fed'; b.style.borderColor = '#2f6fed';
      note.textContent = v ? (v.id + ' — ' + v.title + '. Decides: ' + v.decides)
                           : 'Unchanged, as it is in the source today.';
    };
    return b;
  };
  bar.appendChild(mk('current', null));
  S.variants.forEach(v => bar.appendChild(mk(v.id + ' · ' + v.title, v)));
  bar.appendChild(note);
  document.body.appendChild(bar);
  el.scrollIntoView({block:'center', behavior:'smooth'});
  return JSON.stringify({ok:true, variants:S.variants.length});
})()
"""


def inject(rec: dict, variants: list, rid: str) -> dict:
    # `connect_page` returns (ws, info-or-reason). This unpacked it as a single value,
    # so `ws` was the tuple: always truthy, so the "no page is open" guard never fired,
    # and the next line raised AttributeError instead. `show` could not work at all,
    # and the failure surfaced as a traceback rather than as the guard's message.
    ws, why = cdp.connect_page()
    if ws is None:
        return {"ok": False, "why": str(why)}
    # A variant switcher is an overlay, and an overlay's <style> is inline style.
    # Under a strict `style-src` it appends and renders unstyled, which reads as
    # "the variants did not appear". Measured, never bypassed -- see cdp.style_policy.
    pol = cdp.style_policy(ws)
    if pol["styled"] is False:
        try:
            ws.close()
        except Exception:
            pass
        return {"ok": False, "why": pol["why"]}
    js = OVERLAY % {"sel": json.dumps(rec["selector"]),
                    "variants": json.dumps(variants),
                    "rid": json.dumps(rid)}
    try:
        res = cdp.evaluate(ws, js)
    finally:
        try:
            ws.close()
        except Exception:
            pass
    try:
        return json.loads(res) if res else {"ok": False, "why": "no answer from the page"}
    except (TypeError, ValueError):
        return {"ok": False, "why": f"unreadable answer: {str(res)[:80]}"}


def read_choice(rid: str) -> str | None:
    ws, _why = cdp.connect_page()
    if ws is None:
        return None
    try:
        res = cdp.evaluate(ws, "window.__uxLive && window.__uxLive.rid === "
                               + json.dumps(rid) + " ? (window.__uxLive.chosen || '') : ''")
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return (str(res).strip() or None) if res else None


# ---------------------------------------------------------------- the writeback
def stylesheet(root: Path) -> Path | None:
    """The stylesheet a rule belongs in: the one that already defines the tokens.

    Not a new file. A change that lands somewhere nobody imports is a change that
    does not happen, and a tool that creates `deuxui-overrides.css` has moved the
    problem rather than solved it."""
    best, best_score = None, -1
    for p in iter_files(root, STYLE_EXT, limit=400):
        try:
            t = p.read_text(errors="replace")
        except OSError:
            continue
        score = t.count("--") + (500 if "@theme" in t else 0) + (200 if ":root" in t else 0)
        score -= 400 if "node_modules" in str(p) else 0
        if score > best_score:
            best, best_score = p, score
    return best


def scope_for(rec: dict) -> str | None:
    """A selector the rule can be written against, from the element's own classes.

    Returns None rather than inventing one. A generated class name means the rule
    matches nothing until somebody also edits the component, and then the accepted
    change is half-applied -- visible in the stylesheet, absent on the screen."""
    for cls in str(rec.get("classes") or "").split():
        if len(cls) >= 4 and not re.fullmatch(r"[a-z]+-(?:\d+|px|full|auto)", cls):
            return "." + cls
    return None


def patch(root: Path, sheet: Path, scope: str, variant: dict, rid: str) -> str:
    """The stylesheet's new text. Appended as one commented rule, not merged into an
    existing one -- a merge silently changes whatever else used that rule."""
    old = sheet.read_text(errors="replace")
    decls = "\n".join(f"  {k}: {v};" for k, v in variant["declarations"].items())
    rule = (f"\n/* {rid} · {variant['title']} ({variant['axis']}) — accepted from a live\n"
            f"   comparison on the running app. Decides: {variant['decides']}.\n"
            f"   Every value here is declared in .deuxui/design.contract.yaml. */\n"
            f"{scope} {{\n{decls}\n}}\n")
    return old.rstrip("\n") + "\n" + rule


def severity_of() -> dict:
    """detector -> the worst severity of any rule it adjudicates.

    A finding carries no severity of its own; severity is a property of the RULE, and
    the registry is where it lives. This function exists because its absence made the
    accept gate unable to refuse anything: it read `finding["severity"]`, got nothing
    every time, and so found zero blocking findings on a variant that put grey on
    white at 2.1:1. A check that cannot fail is not a check -- which is the same
    sentence this whole skill is built around, so it is fitting that the gate had to
    be caught by its own control rather than by review."""
    order = {"P0": 3, "P1": 2, "P2": 1}
    try:
        import rulepack
        reg, det, _th = rulepack.load()
    except Exception:
        return {}
    sev = {}
    rules = reg["rules"] if isinstance(reg, dict) and "rules" in reg else reg
    by_id = {r["id"]: str(r.get("severity") or "") for r in rules if r.get("id")}
    for name, entry in (det.get("detectors") or {}).items():
        worst = ""
        for rid in (entry or {}).get("rules") or []:
            s = by_id.get(rid, "")
            if order.get(s, 0) > order.get(worst, 0):
                worst = s
        sev[name] = worst
    return sev


def check_delta(root: Path, sheet: Path, new_text: str) -> dict:
    """Run the static tier against the edit before it exists on disk.

    A variant is admissible or it is not, and that is measurable. Impeccable's accept
    is a matter of taste; this one is taste applied to options that already pass, which
    is the only order that cannot be argued with afterwards."""
    def scan(target: Path) -> list:
        r = subprocess.run([sys.executable, str(HERE / "ux_check.py"), str(target),
                            "--json"], capture_output=True, text=True)
        try:
            return json.loads(r.stdout).get("findings", [])
        except (ValueError, TypeError):
            return []

    before = scan(root)
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / root.name
        # `.deuxui` must come along. It holds the contract, and without it every
        # S-CONTRACT-* check reports NOT_RUN on the copy -- so the delta was measured
        # against a tree that could not see conformance at all, which is precisely
        # what a variant needs checking for. It read as "0 findings after" and looked
        # like an improvement.
        ignore = shutil.ignore_patterns(*(SKIP - {".deuxui"}))
        try:
            shutil.copytree(root, copy, ignore=ignore, symlinks=True)
        except (OSError, shutil.Error) as e:
            return {"ran": False, "why": f"could not copy the tree to test on: {e}"}
        dest = copy / sheet.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new_text)
        after = scan(copy)
    key = lambda f: (f.get("detector"), f.get("snippet"), f.get("line"))
    b = {key(f) for f in before}
    introduced = [f for f in after if key(f) not in b]
    sev = severity_of()
    for f in introduced:
        f["severity"] = sev.get(f.get("detector"), "")
    blocking = [f for f in introduced if f["severity"] in ("P0", "P1")]
    return {"ran": True, "before": len(before), "after": len(after),
            "introduced": introduced[:8], "blocking": blocking,
            "graded": bool(sev)}


def phase_permits(sheet: Path) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, str(HERE / "ux_phase.py"), "gate", "write",
                        str(sheet)], capture_output=True, text=True)
    if r.returncode == 0:
        return True, ""
    return False, (r.stderr or r.stdout).strip()[:400]


# -------------------------------------------------------------------- commands
# --------------------------------------------------------------- resolve by name
RESOLVE = r"""
(() => {
  const WANT = %(want)s;
__PICK_JS__
  const norm = s => (s || '').trim().replace(/\s+/g, ' ').toLowerCase();
  const want = norm(WANT);
  const words = want.split(' ').filter(w => w.length > 2);

  const ours = el => el.closest && (el.closest('.uxsel-panel') || el.closest('.uxlive-bar')
                || el.classList.contains('uxsel-hi') || el.classList.contains('uxsel-tag')
                || el.classList.contains('uxsel-badge'));
  const visible = el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const c = getComputedStyle(el);
    return c.visibility !== 'hidden' && c.display !== 'none' && c.opacity !== '0';
  };
  const all = [...document.querySelectorAll('body *')].filter(e => !ours(e) && visible(e));
  const name = el => norm(el.getAttribute('aria-label') || el.getAttribute('alt')
                          || el.getAttribute('title') || '');
  const text = el => norm(el.innerText || '');
  const tokens = el => norm((el.getAttribute('class') || '') + ' '
                            + (el.getAttribute('data-testid') || '')).replace(/-/g, ' ');

  // Tiers, most specific first. The FIRST tier with any hit decides; a later tier
  // never adds to an earlier one, because "matched the text exactly" and "shares
  // three class words" are not the same kind of evidence and must not be pooled.
  const tiers = [
    ['css selector',  () => { try { return WANT.match(/^[#.\[]|^[a-z]+[.#\[]/i)
                                ? [...document.querySelectorAll(WANT)].filter(visible) : []; }
                              catch (e) { return []; } }],
    ['test id',       () => all.filter(e => norm(e.getAttribute('data-testid')) === want)],
    ['accessible name', () => all.filter(e => name(e) === want)],
    ['exact text',    () => all.filter(e => text(e) === want)],
    ['text prefix',   () => all.filter(e => text(e).startsWith(want) && text(e).length < want.length + 40)],
    ['class words',   () => words.length ? all.filter(e => words.every(w => tokens(e).includes(w))) : []],
  ];

  for (const [kind, fn] of tiers) {
    let hits = fn();
    if (!hits.length) continue;

    // A container's text contains its children's, so an ancestor and its leaf both
    // match. Keep the innermost: the leaf is what a person means by "the heading".
    hits = hits.filter(e => !hits.some(o => o !== e && e.contains(o)));

    if (hits.length > 1) {
      // A plural phrase ("the pricing cards") names a group. If every hit is a
      // sibling under one parent, that parent IS the single thing meant. Otherwise
      // there is no single answer and inventing one picks the wrong element
      // silently.
      const p0 = hits[0].parentElement;
      if (p0 && hits.every(h => h.parentElement === p0)) {
        return JSON.stringify({ok: true, kind: kind + ' (the group they share)',
                               hits: hits.length, el: describe(p0)});
      }
      return JSON.stringify({ok: false, kind: kind, hits: hits.length,
        candidates: hits.slice(0, 8).map(e => ({selector: selectorFor(e),
                                                text: text(e).slice(0, 60)}))});
    }
    hits[0].scrollIntoView({block: 'center', behavior: 'instant'});
    return JSON.stringify({ok: true, kind: kind, hits: 1, el: describe(hits[0])});
  }
  return JSON.stringify({ok: false, kind: null, hits: 0, candidates: []});
})()
"""


def resolve_by_name(want: str) -> dict:
    """Find the one element a phrase names, on the page the browser already has open.

    `pick` needs a person to click, which is the right default: pointing is
    unambiguous and it is the input this whole loop exists to capture. But an agent
    handed "make the pricing cards bolder" has the element in words already, and
    forcing a human into the loop to re-express it as a click is ceremony.

    So this resolves words to exactly one node, or refuses and lists what it found.
    Six tiers of evidence, most specific first, and a later tier never adds to an
    earlier one -- "the text is exactly this" and "three class words overlap" are
    different claims and pooling them is how the wrong element gets picked with
    confidence. Ancestors of a hit are dropped, because a container's innerText
    contains its children's and a person saying "the heading" means the heading.

    The one place several hits still resolve to one element: when every hit is a
    sibling under one parent, a plural phrase named the group, and the group is
    that parent. Anything else is reported as ambiguous with the candidates, which
    is the only honest answer -- a guess here edits the wrong part of somebody's
    page and the variant looks like it worked."""
    ws, why = cdp.connect_page()
    if ws is None:
        return {"ok": False, "why": str(why)}
    pol = cdp.style_policy(ws)
    js = (RESOLVE % {"want": json.dumps(want)}).replace("__PICK_JS__", ux_select.PICK_JS)
    try:
        res = cdp.evaluate(ws, js)
    except RuntimeError as e:
        return {"ok": False, "why": f"the page would not answer: {e}"}
    finally:
        try:
            ws.close()
        except Exception:
            pass
    out = json.loads(res) if isinstance(res, str) else (res or {})
    out.setdefault("ok", False)
    out["styled"] = pol["styled"]
    return out


def cmd_pick(a) -> int:
    if getattr(a, "describe", None):
        return _pick_described(a)
    r = subprocess.run([sys.executable, str(HERE / "ux_select.py"), "watch",
                        *(["--timeout", str(a.timeout)] if a.timeout else [])])
    if r.returncode not in (0, 2):
        return r.returncode
    reqs = sorted(REQUESTS.glob("REQ-*.yaml")) if REQUESTS.exists() else []
    if not reqs:
        w("\nNothing was picked, so there is nothing to vary.\n\n")
        return 2
    rec = load(reqs[-1]) or {}
    loc = locate(rec)
    w(f"\n{reqs[-1].stem}  {rec.get('selector', '?')}\n")
    if loc["found"]:
        w(f"  source   {loc['file']}:{loc['line']}  (matched on the {loc['anchor_kind']} "
          f"{loc['anchor']!r})\n")
    else:
        w(f"  source   NOT LOCATED. {loc['why']}\n")
        for t in loc["tried"]:
            w(f"             {t['kind']:<6} {t['anchor'][:44]!r}  {t['hits']} hit(s)\n")
    st = {"id": reqs[-1].stem, "at": now(), "element": rec, "source": loc,
          "variants": [], "accepted": None}
    LIVE.mkdir(parents=True, exist_ok=True)
    session(reqs[-1].stem).write_text(yaml.safe_dump(st, sort_keys=False,
                                                     allow_unicode=True, width=92))
    w(f"\n  next     python3 scripts/ux_live.py vary {reqs[-1].stem}\n\n")
    return 0


def _open_session(rec: dict, how: str) -> int:
    """Write the live session for one resolved element, and say where it is in the source."""
    rid = ux_select.next_id()
    rec = dict(rec)
    rec["id"] = rid
    rec["recorded_at"] = now()
    rec["recorded_by"] = how
    ux_select.REQUESTS.mkdir(parents=True, exist_ok=True)
    (ux_select.REQUESTS / f"{rid}.yaml").write_text(
        yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=92))
    loc = locate(rec)
    w(f"\n{rid}  {rec.get('selector', '?')}\n")
    if loc["found"]:
        w(f"  source   {loc['file']}:{loc['line']}  (matched on the "
          f"{loc['anchor_kind']} {loc['anchor']!r})\n")
    else:
        w(f"  source   NOT LOCATED. {loc['why']}\n")
        for tr in loc["tried"]:
            w(f"             {tr['kind']:<6} {tr['anchor'][:44]!r}  {tr['hits']} hit(s)\n")
    st = {"id": rid, "at": now(), "element": rec, "source": loc,
          "variants": [], "accepted": None}
    LIVE.mkdir(parents=True, exist_ok=True)
    session(rid).write_text(yaml.safe_dump(st, sort_keys=False, allow_unicode=True,
                                          width=92))
    w(f"\n  next     python3 scripts/ux_live.py vary {rid}\n\n")
    return 0


def _pick_described(a) -> int:
    res = resolve_by_name(a.describe)
    if not res.get("ok"):
        if res.get("why"):
            w(f"\n{res['why']}\n\n")
            return 2
        if res.get("candidates"):
            w(f"\n{a.describe!r} matches {res['hits']} elements on this page by "
              f"{res['kind']}, and they are not one group:\n\n")
            for c in res["candidates"]:
                w(f"    {c['selector'][:60]:<60}  {c['text']!r}\n")
            w(f"\n  Nothing was picked. Name one of these, or use "
              f"`ux_live.py pick` and click it.\n\n")
            return 2
        w(f"\nNothing on this page matches {a.describe!r} — not by selector, test id, "
          f"accessible name, visible text or class name.\n"
          f"  The page is whatever the browser has open; check you are on the right "
          f"route.\n\n")
        return 2
    if res.get("styled") is False:
        w("\nnote: this page's CSP refuses an injected <style>, so `show` will not be "
          "able to render the variant switcher here. `pick` and `vary` still work; "
          "compare through `ux_review.py serve` instead.\n")
    w(f"\nresolved by {res['kind']}\n")
    return _open_session(res["el"],
                         f"deuxui/scripts/ux_live.py pick --describe "
                         f"{a.describe!r} -- resolved by {res['kind']}")


def cmd_vary(a) -> int:
    p = session(a.id)
    st = load(p) or {}
    if not st:
        w(f"\nNo live session for {a.id}. `ux_live.py pick` starts one.\n\n")
        return 2
    c = ux_image.load_contract(None)
    if not c.raw:
        w("\nNo .deuxui/design.contract.yaml. Without a declaration there is nothing to "
          "generate conformant variants FROM, and a generator free to propose anything "
          "is the fastest way out of the system. Declare it first: `ux_color`/`ux_type`, "
          "or derive_contract.py --write in an existing project.\n\n")
        return 2
    variants = build_variants(st.get("element") or {}, c, a.count, a.direction)
    if not variants:
        w("\nThe contract declares nothing this element could vary on.\n\n")
        return 2
    st["variants"] = variants
    st["contract_sha"] = c.sha()
    st["varied_at"] = now()
    p.write_text(yaml.safe_dump(st, sort_keys=False, allow_unicode=True, width=92))
    w(f"\n{a.id}  {len(variants)} variant(s), contract {c.sha()}\n")
    for v in variants:
        w(f"\n  {v['id']}  {v['title']}  [{v['axis']}]\n"
          f"      decides: {v['decides']}\n      {v['css']}\n")
    w(f"\n  Every value above is declared. Compare them in the real page:\n"
      f"    python3 scripts/ux_live.py show {a.id}\n\n")
    return 0


def cmd_show(a) -> int:
    st = load(session(a.id)) or {}
    if not st.get("variants"):
        w(f"\n{a.id} has no variants yet. `ux_live.py vary {a.id}` first.\n\n")
        return 2
    res = inject(st["element"], st["variants"], a.id)
    if not res.get("ok"):
        w(f"\nNot shown: {res.get('why')}\n\n")
        return 2
    w(f"\n{a.id} is on the page — {res['variants']} variants plus `current`, bottom "
      f"centre.\n  The page is not modified: this sets an inline style so you can see "
      f"each one\n  in place. Nothing reaches the source until you accept it.\n\n")
    for v in st["variants"]:
        w(f"    {v['id']}  {v['title']}\n")
    w(f"\n  Then:  python3 scripts/ux_live.py accept {a.id} --variant A\n"
      f"         python3 scripts/ux_live.py accept {a.id}        (reads your choice "
      f"from the page)\n\n")
    return 0


def cmd_accept(a) -> int:
    p = session(a.id)
    st = load(p) or {}
    if not st.get("variants"):
        w(f"\n{a.id} has no variants to accept.\n\n")
        return 2
    vid = a.variant or read_choice(a.id)
    if not vid:
        w(f"\nNo variant named, and the page has no choice recorded. Either click one "
          f"in the bar or pass --variant A.\n\n")
        return 2
    variant = next((v for v in st["variants"] if v["id"] == vid.upper()), None)
    if not variant:
        w(f"\n{vid!r} is not one of {', '.join(v['id'] for v in st['variants'])}.\n\n")
        return 2
    if not a.who:
        w("\nAn accepted change needs a person's name on it. This becomes a decision "
          "record that the build gate reads, and a record with no author cannot be "
          "weighed later. Pass --who \"NAME\".\n\n")
        return 2

    root = Path.cwd()
    loc = st.get("source") or {}
    sheet = Path(a.into) if a.into else stylesheet(root)
    if not sheet or not sheet.exists():
        w("\nNo stylesheet found to write into, and this will not create one: a rule in "
          "a file nobody imports is a change that does not happen. Name it with "
          "--into PATH.\n\n")
        return 2
    scope = a.scope or scope_for(st.get("element") or {})
    if not scope:
        w("\nThis element has no class distinctive enough to write a rule against, and "
          "inventing one would leave the change half-applied — in the stylesheet, "
          "absent on the screen. Give it a class, or pass --scope '.selector'.\n\n")
        return 2

    ok, why = phase_permits(sheet)
    if not ok and not a.force:
        w(f"\nThe phase gate refuses this write:\n  {why}\n\n"
          f"  That is the gate doing its job: production UI edits wait until somebody "
          f"has used a prototype and accepted it. `ux_phase.py status` shows what is "
          f"missing.\n\n")
        return 1

    new_text = patch(root, sheet, scope, variant, a.id)
    delta = check_delta(root, sheet, new_text)
    w(f"\n{a.id} → {variant['id']}  {variant['title']}\n")
    w(f"  into     {sheet}  scoped to {scope}\n")
    if delta.get("ran"):
        w(f"  checks   {delta['before']} finding(s) before, {delta['after']} after\n")
        if not delta.get("graded"):
            w("           severity UNRESOLVED — the registry could not be read, so "
              "nothing can be graded blocking and this write is NOT gated.\n")
        for f in delta["introduced"]:
            w(f"             + {f.get('severity') or '--'}  {f.get('detector')}  "
              f"{f.get('file')}:{f.get('line')}\n")
        if delta["blocking"] and not a.force:
            w(f"\n  REFUSED. This variant introduces {len(delta['blocking'])} P0/P1 "
              f"finding(s):\n")
            for f in delta["blocking"]:
                w(f"    {f.get('severity')}  {f.get('detector')}  {f.get('file')}:"
                  f"{f.get('line')}\n      {f.get('snippet')}\n"
                  f"      {str(f.get('fix'))[:160]}\n")
            w("\n  Taste chooses between admissible options. It does not make an "
              "inadmissible one admissible. Pick another variant, or fix the cause.\n\n")
            return 1
    else:
        w(f"  checks   NOT_RUN — {delta.get('why')}\n"
          f"           An unchecked write is not a verified one; this is recorded as "
          f"unchecked rather than as clean.\n")

    diff = "".join(difflib.unified_diff(
        sheet.read_text(errors="replace").splitlines(True), new_text.splitlines(True),
        fromfile=str(sheet), tofile=str(sheet) + " (accepted)", n=2))
    if a.dry_run:
        w(f"\n  --dry-run, nothing written:\n\n{diff}\n")
        return 0
    sheet.write_text(new_text)

    did = _next_id(DECISIONS, "DEC")
    rec = {"id": did, "question": f"Which variant of {st['element'].get('selector')}?",
           "surface": st["element"].get("selector"),
           "chosen": variant["id"], "outcome": f"accept:{variant['id']}",
           "approves_a_build": False,
           "who": a.who, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "recorded_at": now(),
           "rationale": a.why or f"{variant['title']} — {variant['decides']}",
           "contract_sha": st.get("contract_sha"),
           "axis": variant["axis"], "declarations": variant["declarations"],
           # Project-relative where it can be. An absolute path in a decision record
           # names one machine, and the record is meant to outlive the checkout.
           "written_to": {"file": _rel(sheet, root), "scope": scope},
           "element_source": {"file": loc.get("file"), "line": loc.get("line")},
           "checks": {"ran": bool(delta.get("ran")),
                      "before": delta.get("before"), "after": delta.get("after"),
                      "introduced": len(delta.get("introduced") or [])},
           "reviewed": [{"id": v["id"], "kind": "live-variant", "target": v["axis"]}
                        for v in st["variants"]],
           "source": "ux_live.py (variants compared in place on the running app)",
           "recorded_by": "deuxui/scripts/ux_live.py"}
    DECISIONS.mkdir(parents=True, exist_ok=True)
    dp = DECISIONS / f"{did}.yaml"
    dp.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=92))
    try:
        import ux_ledger
        ux_ledger.archive(by="ux_live.py (a variant was accepted into the source)")
    except Exception:
        pass
    st["accepted"] = {"variant": variant["id"], "at": now(), "decision": did}
    p.write_text(yaml.safe_dump(st, sort_keys=False, allow_unicode=True, width=92))
    w(f"\n  written  {sheet}\n  recorded {dp}\n\n{diff}\n"
      f"  The dev server's own reload will show it. `ux_ledger.py show {did}` has the "
      f"contract it was decided against.\n\n")
    return 0


def coupled(root: Path, literal: str, home: Path) -> list:
    """Every OTHER place this exact string appears, with whether it looks like a key.

    Visible copy is often also a lookup key -- an object property, an icon map, an
    analytics label, a translation id. Renaming the rendered text and leaving the key
    breaks the thing the key was pointing at, and the breakage shows up somewhere
    that has nothing to do with the edit.

    Deliberately searches WIDER than `locate` does. `locate` only looks at component
    source, and it already guaranteed the string appears exactly once there -- so
    restricted to the same file set this function could never find anything, which is
    how it was first written and it was very nearly dead code. The occurrences that
    actually matter are in the files `locate` never opens: `en.json` and its
    siblings, a YAML content file, a Markdown table, a server-side constant. A
    translation catalogue keyed on the English string is the single most common
    coupling there is.

    It does not rename them. Deciding that a second occurrence is coincidence is a
    judgement about somebody's codebase, and a tool that quietly edits six files
    because one word matched is doing something it was not asked to do."""
    out = []
    for q in (list(iter_files(root, SRC_EXT)) + list(iter_files(root, STYLE_EXT))
              + list(iter_files(root, COUPLED_EXT))):
        if q.resolve() == home.resolve():
            continue
        try:
            body = q.read_text(errors="replace")
        except OSError:
            continue
        for m in re.finditer(re.escape(literal), body):
            line = body[:m.start()].count("\n") + 1
            ctx = body[max(0, m.start() - 40):m.end() + 12].replace("\n", " ")
            looks_key = bool(re.search(re.escape(literal) + r"\s*['\"]?\s*:", body[m.start():m.end() + 6]))
            out.append({"file": str(q.relative_to(root)), "line": line,
                        "key_like": looks_key, "context": ctx.strip()[:80]})
            if len(out) >= 12:
                return out
    return out


def cmd_text(a) -> int:
    """Rewrite the visible copy of a picked element, in the source, or refuse.

    This is the half of the live loop that was missing. `accept` moves declared
    values -- a size, a role, a radius -- by writing one rule into the stylesheet.
    It cannot change what a thing SAYS, and "this label is wrong" is the single most
    common thing a person says while looking at a real screen.

    The rule is the same as everywhere else in this file: the string has to resolve
    to exactly one place in the source, by an anchor from the element itself, or
    nothing is written. A copy edit applied to the wrong line still reads as
    success, and the wrong line is usually another component rendering the same word.
    """
    st = load(session(a.id)) or {}
    if not st:
        w(f"\nNo live session for {a.id}. `ux_live.py pick` starts one.\n\n")
        return 2
    rec = st.get("element") or {}
    root = Path.cwd()

    if not a.who:
        w("\nA copy change needs a person's name on it — it becomes a decision record "
          "the build gate reads. Pass --who \"NAME\".\n\n")
        return 2

    loc = st.get("source") or {}
    if not loc.get("found") or loc.get("anchor_kind") != "text":
        w(f"\nREFUSED. This element's source location "
          f"{'was matched on its ' + str(loc.get('anchor_kind')) if loc.get('found') else 'was never resolved'}"
          f", not on its text, so there is no known string in the source to replace.\n"
          f"  Rewriting the line this element was located BY would change something "
          f"else — a class name, a container — and a copy edit that hits the wrong "
          f"token still looks like it worked.\n"
          f"  Edit the file yourself: {loc.get('file') or 'unknown'}"
          f"{':' + str(loc['line']) if loc.get('line') else ''}\n\n")
        return 2

    old = str(loc["anchor"])
    new = a.to
    if new == old:
        w(f"\nThe new text is identical to {old!r}. Nothing to do.\n\n")
        return 0
    if not new.strip():
        w("\nREFUSED. Empty copy is not a copy edit — a label with no text has no "
          "accessible name either (A11Y-007, COMP-002). Delete the element instead, "
          "knowingly.\n\n")
        return 2

    f = root / loc["file"]
    try:
        body = f.read_text(errors="replace")
    except OSError as e:
        w(f"\nCould not read {f}: {e}\n\n")
        return 2
    n = body.count(old)
    if n == 0:
        w(f"\nREFUSED. {old!r} is no longer in {loc['file']} — the file changed since "
          f"this element was picked. Pick it again.\n\n")
        return 2
    if n > 1:
        w(f"\nREFUSED. {old!r} appears {n} times in {loc['file']} alone, so there is no "
          f"single occurrence to rewrite. Edit the file directly, or pick a child "
          f"element whose text is unique.\n\n")
        return 2

    new_text = body.replace(old, new, 1)
    line = body[:body.index(old)].count("\n") + 1
    also = coupled(root, old, f)

    ok, why = phase_permits(f)
    if not ok and not a.force:
        w(f"\nThe phase gate refuses this write:\n  {why}\n\n")
        return 1

    delta = check_delta(root, f, new_text)
    w(f"\n{a.id}  copy edit in {loc['file']}:{line}\n")
    w(f"  from     {old!r}\n  to       {new!r}\n")
    if delta.get("ran"):
        w(f"  checks   {delta['before']} finding(s) before, {delta['after']} after\n")
        if not delta.get("graded"):
            w("           severity UNRESOLVED — the registry could not be read, so "
              "nothing can be graded blocking and this write is NOT gated.\n")
        for x in delta["introduced"]:
            w(f"             + {x.get('severity') or '--'}  {x.get('detector')}  "
              f"{x.get('file')}:{x.get('line')}\n")
        if delta["blocking"] and not a.force:
            w(f"\n  REFUSED. This wording introduces {len(delta['blocking'])} P0/P1 "
              f"finding(s):\n")
            for x in delta["blocking"]:
                w(f"    {x.get('severity')}  {x.get('detector')}  {x.get('file')}:"
                  f"{x.get('line')}\n      {x.get('snippet')}\n")
            w("\n  Copy is checked like anything else — a label that says nothing, or "
              "an error message that blames the user, is a finding with a rule behind "
              "it.\n\n")
            return 1
    else:
        w(f"  checks   NOT_RUN — {delta.get('why')}\n"
          f"           Recorded as unchecked rather than as clean.\n")

    if also:
        w(f"\n  ALSO     {old!r} appears in {len(also)} other place(s). Nothing here "
          f"touches them:\n")
        for x in also:
            w(f"             {x['file']}:{x['line']}"
              f"{'  LOOKS LIKE A KEY' if x['key_like'] else ''}\n"
              f"               {x['context']}\n")
        w("           If any of those is a lookup key for this same string — an icon "
          "map,\n           a translation id, an analytics label — it still points at "
          "the old\n           wording and will now miss. Check them before you "
          "ship.\n")

    diff = "".join(difflib.unified_diff(
        body.splitlines(True), new_text.splitlines(True),
        fromfile=str(f), tofile=str(f) + " (copy edit)", n=2))
    if a.dry_run:
        w(f"\n  --dry-run, nothing written:\n\n{diff}\n")
        return 0
    f.write_text(new_text)

    did = _next_id(DECISIONS, "DEC")
    drec = {"id": did, "question": f"What should {rec.get('selector')} say?",
            "surface": rec.get("selector"),
            "chosen": "copy", "outcome": "accept:copy",
            "approves_a_build": False,
            "who": a.who, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "recorded_at": now(),
            "rationale": a.why or f"copy changed from {old!r} to {new!r}",
            "contract_sha": st.get("contract_sha"),
            "axis": "copy",
            "declarations": {"from": old, "to": new},
            # Project-relative, not absolute: a record that names
            # /home/someone/checkout/... cannot be read on any other machine, and a
            # decision is supposed to outlive the checkout it was made in.
            "written_to": {"file": loc["file"], "line": line},
            "element_source": {"file": loc.get("file"), "line": loc.get("line")},
            "checks": {"ran": bool(delta.get("ran")),
                       "before": delta.get("before"), "after": delta.get("after"),
                       "introduced": len(delta.get("introduced") or [])},
            "coupled_occurrences": also,
            "reviewed": [],
            "source": "ux_live.py text (copy rewritten in the source from a picked "
                      "element)",
            "recorded_by": "deuxui/scripts/ux_live.py"}
    DECISIONS.mkdir(parents=True, exist_ok=True)
    dp = DECISIONS / f"{did}.yaml"
    dp.write_text(yaml.safe_dump(drec, sort_keys=False, allow_unicode=True, width=92))
    try:
        import ux_ledger
        ux_ledger.archive(by="ux_live.py text (copy accepted into the source)")
    except Exception:
        pass
    st.setdefault("copy_edits", []).append(
        {"at": now(), "from": old, "to": new, "decision": did})
    session(a.id).write_text(yaml.safe_dump(st, sort_keys=False, allow_unicode=True,
                                            width=92))
    w(f"\n  written  {f}\n  recorded {dp}\n\n{diff}\n")
    return 0


def cmd_status(a) -> int:
    rows = sorted(LIVE.glob("*.yaml")) if LIVE.exists() else []
    if not rows:
        w("\nNo live session. `ux_live.py pick` starts one.\n\n")
        return 0
    w(f"\n{len(rows)} live session(s)\n")
    for p in rows:
        d = load(p) or {}
        acc = d.get("accepted")
        loc = d.get("source") or {}
        w(f"\n  {d.get('id', p.stem)}  {str((d.get('element') or {}).get('selector'))[:46]}\n"
          f"      source   {loc.get('file', 'NOT LOCATED')}"
          f"{':' + str(loc['line']) if loc.get('line') else ''}\n"
          f"      variants {len(d.get('variants') or [])}\n"
          f"      state    {'accepted ' + acc['variant'] + ' → ' + acc['decision'] if acc else 'open'}\n")
    w("\n")
    return 0


def cmd_discard(a) -> int:
    p = session(a.id)
    if not p.exists():
        w(f"\nNo session {a.id}.\n\n")
        return 2
    p.unlink()
    w(f"\n{a.id} discarded. Any rule already written to the stylesheet stays — this "
      f"only forgets the session, it does not revert the source. Use git for that.\n\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pick", help="point at an element and find it in the source")
    s.add_argument("--describe", metavar="WORDS",
                   help="name the element instead of clicking it: a CSS selector, a "
                        "test id, an accessible name, its visible text, or words from "
                        "its class. Resolves to exactly one element or refuses with "
                        "the candidates.")
    s.add_argument("--timeout", type=int)
    s.set_defaults(fn=cmd_pick)

    s = sub.add_parser("vary", help="variants, every value taken from the contract")
    s.add_argument("id")
    s.add_argument("--count", type=int, default=3)
    s.add_argument("--direction", help="a plain-language steer: bolder, quieter, "
                                       "tighter, roomier, lift, flatter")
    s.set_defaults(fn=cmd_vary)

    s = sub.add_parser("show", help="all of them in the real page, with a switcher")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("accept", help="check it, write it, record it")
    s.add_argument("id")
    s.add_argument("--variant")
    s.add_argument("--who", help="the person accepting it, by name")
    s.add_argument("--why")
    s.add_argument("--into", help="the stylesheet to write into")
    s.add_argument("--scope", help="the selector to write the rule against")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--force", action="store_true",
                   help="write despite a blocking finding or a closed phase gate. "
                        "Recorded in the decision either way.")
    s.set_defaults(fn=cmd_accept)

    s = sub.add_parser("text", help="rewrite what the picked element says, in the source")
    s.add_argument("id")
    s.add_argument("--to", required=True, metavar="COPY", help="the new wording")
    s.add_argument("--who", help="the person deciding, by name")
    s.add_argument("--why")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--force", action="store_true",
                   help="write despite a blocking finding or a closed phase gate. "
                        "Recorded in the decision either way.")
    s.set_defaults(fn=cmd_text)

    s = sub.add_parser("status", help="what is open")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("discard", help="forget a session")
    s.add_argument("id")
    s.set_defaults(fn=cmd_discard)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
