#!/usr/bin/env python3
"""Prove each static check fires on known-bad source and stays quiet on good.

A check that cannot fail its own negative case is not a check, it is a comment.
Run this before trusting any report.

    python3 selftest.py                  every group
    python3 selftest.py --group spans    one group, and the rest report NOT RUN
    python3 selftest.py --list           the group names

`--help` returns immediately and runs nothing. That is not a courtesy: this file had
no argument parsing at all, so `--help` ran the entire suite -- and `parity.py --deep`
runs `--help` on every script it cites, including this one. Once a group in here
called `parity.audit(deep=True)`, each run spawned a run which spawned a run. The
front door of a test suite has to be answerable without running the suite.
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys, tempfile, json, io, contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml

# Do not leave .pyc files beside the checks. A directory-source plugin install
# copies the working tree verbatim, so stray bytecode ships to the consumer
# despite being gitignored. Costs ~15ms per run, which nothing here notices.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
FIX = HERE / "checks" / "fixtures"

# Detectors that must fire on bad.* and must not fire on good.*
EXPECT = [
    "S-A11Y-ALT", "S-A11Y-ICONBTN", "S-A11Y-PLACEHOLDER", "S-A11Y-DIVCLICK",
    "S-A11Y-HREFHASH", "S-A11Y-TABINDEX", "S-A11Y-HEADING",
    "S-FOCUS-OUTLINE", "S-CONTRAST-PAIR", "S-TARGET-SIZE",
    "S-FORM-AUTOCOMPLETE", "S-FORM-INPUTTYPE", "S-FORM-VALIDATION",
    "S-STATE-EMPTY", "S-RESP-VH", "S-RESP-SAFEAREA", "S-RESP-TABLE",
    "S-MOTION-REDUCE", "S-HOVER-ONLY", "S-MODAL-NATIVE",
    "S-SLOP-EMOJI", "S-SLOP-COPY", "S-TOKEN-HEX", "S-TOKEN-ARBITRARY",
    "S-DS-NEWDEP", "S-CONTENT-ERRORTEXT", "S-PERF-IMGDIM",
    "S-CANVAS-A11Y", "S-3D-PERF", "S-MEDIA-CAPTIONS", "S-COLOR-ONLY",
    # craft floor
    "S-CRAFT-HERO-SCALE", "S-CRAFT-FAMILIES", "S-CRAFT-HALO", "S-CRAFT-HARD-SHADOW",
    "S-CRAFT-CARD-RADIUS", "S-CRAFT-HIDDEN-AT-REST", "S-CRAFT-EASING",
    "S-CRAFT-SECTION-NUMBERS", "S-CRAFT-ICON-TILE", "S-CRAFT-STRIPES",
    "S-CRAFT-GRADIENT-TEXT", "S-CRAFT-ZINDEX", "S-CRAFT-GRAY-ON-COLOR",
    "S-CRAFT-TYPE-FLAT", "S-CRAFT-BALANCE", "S-CRAFT-SURFACES",
    # visual contract conformance
    "S-STATE-DUPE", "S-TRUST-DESTRUCT", "S-COMP-DISABLED-MUTE",
    "S-CONTRACT-FAMILY", "S-CONTRACT-RADIUS", "S-CONTRACT-RAMP",
    "S-CONTRACT-FONT-AVAIL",
    # P0 family
    "S-PRIVACY-URL", "S-SECRET-LOG", "S-PASSWORD-HANDLING", "S-PERM-ONMOUNT",
    "S-DARK-PATTERN", "S-FAKE-STATS", "S-STATE-PREMATURE", "S-DRAFT-BOUNDARY",
    "S-RETRY-SAFETY", "S-COMMIT-DISCLOSURE", "S-COMMIT-REVIEW", "S-AI-PROVENANCE",
    "S-TYPE-LEADING", "S-TYPE-MEASURE", "S-NAV-ERROR-ROUTE",
    # reading quality + visual craft
    "S-TYPE-TINY", "S-TYPE-LEADING", "S-TYPE-ALLCAPS", "S-TYPE-JUSTIFY",
    "S-TYPE-TRACKING-WIDE", "S-TYPE-CRAMPED", "S-SLOP-EYEBROW",
    "S-CRAFT-DEPTH", "S-CRAFT-TYPESYSTEM", "S-CRAFT-DECOR", "S-CRAFT-PALETTE-WARM",
    "S-CRAFT-MOTION", "S-CRAFT-RHYTHM", "S-CRAFT-VOICE",
    # native platform -- iOS
    "S-IOS-SAFEAREA", "S-IOS-NAVSTRUCTURE", "S-IOS-EDGESWIPE", "S-IOS-DYNAMICTYPE",
    "S-IOS-SYSTEMFONT", "S-IOS-MINSIZE", "S-IOS-TARGET44", "S-IOS-SEMANTICCOLOR",
    "S-IOS-DARKMODE", "S-IOS-TINT", "S-IOS-MATERIALS", "S-IOS-NATIVECONTROLS",
    "S-IOS-SFSYMBOLS", "S-IOS-MODALITY", "S-IOS-GROUPEDLIST", "S-IOS-TRANSITION",
    "S-IOS-REDUCEMOTION", "S-IOS-LARGETITLE",
    # native platform -- Android
    "S-AND-ADAPTIVENAV", "S-AND-SYSTEMBACK", "S-AND-INSETS", "S-AND-TYPESCALE",
    "S-AND-SYSTEMFONT", "S-AND-SP", "S-AND-ROLETOKENS", "S-AND-DYNAMICCOLOR",
    "S-AND-DARKTHEME", "S-AND-ELEVATION", "S-AND-MATERIAL", "S-AND-FAB",
    "S-AND-TOAST", "S-AND-REDUCEMOTION", "S-AND-TARGET48",
]


def run(tmp: Path, which: str) -> set[str]:
    for name in ("package.json", "theme.css"):
        shutil.copy(FIX / name, tmp / name)
    # The visual contract lives where a real project keeps it, so the conformance
    # checks exercise the same discovery path they use in the field.
    (tmp / ".deuxui").mkdir(exist_ok=True)
    shutil.copy(FIX / "design.contract.yaml", tmp / ".deuxui" / "design.contract.yaml")
    # S-NAV-ERROR-ROUTE reads the route tree on disk, so the good fixture has to
    # be a project that actually handles a bad URL and a failed load. The bad one
    # deliberately does not.
    if which == "good":
        app = tmp / "app"
        app.mkdir(exist_ok=True)
        (app / "not-found.tsx").write_text(
            "export default function NotFound() {\n"
            "  return <main><h1>Not found</h1><a href=\"/\">Go home</a></main>;\n}\n")
        # The copy has to survive S-CONTENT-ERRORTEXT too: name what failed and
        # what the reader can do, rather than gesturing at it.
        (app / "error.tsx").write_text(
            "'use client';\nexport default function Error({ reset }) {\n"
            "  return (\n    <main>\n"
            "      <h1>We could not load your projects</h1>\n"
            "      <p>The server did not answer. Your work is saved.</p>\n"
            "      <button onClick={reset}>Retry loading projects</button>\n"
            "    </main>\n  );\n}\n")
    for suf in (".tsx", ".css"):
        shutil.copy(FIX / f"{which}{suf}", tmp / f"sample{suf}")
    # Native platform fixtures. The ios/ and android/ directories are what
    # detect_platforms() reads, so the platform families are applicable here for
    # the same reason they would be in a real app -- the tree says so.
    (tmp / "ios").mkdir(exist_ok=True)
    (tmp / "android").mkdir(exist_ok=True)
    for extra, dest in ((f"{which}-ios.swift", "ios/ContentView.swift"),
                        (f"{which}-android.kt", "android/HomeScreen.kt"),
                        (f"{which}-native.tsx", "Toolbar.native.tsx")):
        src = FIX / extra
        if src.exists():
            shutil.copy(src, tmp / dest)
    # Field-reported cases, each in its own file. A ±2000-character evidence window
    # means an unrelated "Confirm" elsewhere in a crowded fixture decides the
    # outcome, so these cannot share one.
    for extra, dest in ((f"{which}-peer.tsx", "peer-commit.tsx"),
                        (f"{which}-peer2.tsx", "peer-dupe.tsx"),
                        (f"{which}-peer3.tsx", "peer-destruct.tsx"),
                        (f"{which}-peer4.tsx", "peer-disabled.tsx")):
        src = FIX / extra
        if src.exists():
            shutil.copy(src, tmp / dest)
    for extra, dest in ((f"{which}-p0.tsx", "checkout.tsx"),
                        (f"{which}-craft.tsx", "landing.tsx"),
                        (f"{which}-craft.css", "landing.css"),
                        (f"{which}-craftfloor.tsx", "hero.tsx"),
                        (f"{which}-craftfloor.css", "hero.css")):
        src = FIX / extra
        if src.exists():
            shutil.copy(src, tmp / dest)
    out = subprocess.run([sys.executable, str(HERE / "ux_check.py"), str(tmp), "--json"],
                         capture_output=True, text=True)
    data = json.loads(out.stdout)
    return {f["detector"] for f in data["findings"]}


CFG_PROBE = """
export const Probe = () => (
  <div>
    <button className="h-8 w-8">a</button>
    <div className="p-[7px]">b</div>
    <span className="h-2 w-2 rounded-full bg-green-500" />
  </div>
);
"""


def _scan(target, config=None, extra=()):
    cmd = [sys.executable, str(HERE / "ux_check.py"), str(target), "--json", *extra]
    if config:
        cmd += ["--config", str(config)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip() else {}


def config_wiring():
    """Prove every key in the shipped ux.config.yaml template changes something.

    This is the gap that let four documented keys sit inert. The old selftest
    exercised detectors against fixtures and never once loaded a config, so
    `features`, `disabled_checks`, `thresholds` and `app.*` could all be parsed,
    validated and then ignored while every test stayed green. Each assertion here
    is a positive control: set the key, and require the observable result to move.
    """
    fails = []
    tmpl = yaml.safe_load((HERE.parent / "assets" / "templates" / "ux.config.yaml").read_text())

    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        (proj / "package.json").write_text(
            '{"name":"p","dependencies":{"react":"^18","tailwindcss":"^3.4.0"}}')
        (proj / "Probe.tsx").write_text(CFG_PROBE)
        sub = proj / "nested"; sub.mkdir()
        (sub / "Other.tsx").write_text(CFG_PROBE)
        cfgdir = proj / ".deuxui"; cfgdir.mkdir()
        cfg = cfgdir / "ux.config.yaml"

        def write(text):
            cfg.write_text(text)
            return cfg

        # --- <dir> must scope to that directory, not walk up to package.json
        whole = _scan(proj)
        part = _scan(sub)
        if not whole.get("findings"):
            fails.append("fixture produced no findings; the wiring tests cannot run")
        elif len(part["findings"]) >= len(whole["findings"]):
            fails.append("a subdirectory scan is not narrower than the whole project: "
                         "the directory argument is being discarded")
        if part.get("scanned", "").rstrip("/") != str(sub):
            fails.append(f"scanned {part.get('scanned')!r}, asked for {str(sub)!r}")

        # --- disabled_checks must move a rule to NOT_RUN, never leave it PASS
        base = _scan(proj)
        write("disabled_checks: [S-TARGET-SIZE, S-COLOR-ONLY]\n")
        off = _scan(proj, cfg)
        for did in ("S-TARGET-SIZE", "S-COLOR-ONLY"):
            was = base["detectors"].get(did, {}).get("status")
            now = off["detectors"].get(did, {}).get("status")
            if now != "NOT_RUN":
                fails.append(f"disabled_checks is inert: {did} is {now}, expected NOT_RUN")
            if was == now == "PASS":
                fails.append(f"disabled_checks turned {did} into a PASS")

        # --- thresholds must reach the check that reads them
        write("thresholds:\n  target_size:\n    web_coarse_min_px: 20\n")
        loose = _scan(proj, cfg)
        n_base = sum(1 for f in base["findings"] if f["detector"] == "S-TARGET-SIZE")
        n_loose = sum(1 for f in loose["findings"] if f["detector"] == "S-TARGET-SIZE")
        if not (n_base > 0 and n_loose < n_base):
            fails.append(f"thresholds are inert: S-TARGET-SIZE gave {n_base} findings at "
                         f"the 44px default and {n_loose} at an overridden 20px")

        # --- a STANDARD value may not be lowered by config
        write("thresholds:\n  contrast:\n    normal_text_min: 1.0\n")
        bad = _scan(proj, cfg)
        if not bad["config"]["refused_overrides"]:
            fails.append("config lowered a STANDARD contrast threshold without refusal")

        # --- exclude must keep a directory out of the report
        write("exclude: [nested]\n")
        ex = _scan(proj, cfg)
        if any("nested" in f["file"] for f in ex["findings"]):
            fails.append("exclude is inert: findings still come from the excluded directory")

        # --- features must gate from the file, not only from --feature
        write("features: [forms, charts]\n")
        rep = subprocess.run(
            [sys.executable, str(HERE / "ux_report.py"), "--merge",
             "--static", "/dev/null", "--config", str(cfg)],
            capture_output=True, text=True, cwd=str(proj))
        doc = yaml.safe_load(rep.stdout) if rep.stdout.strip() else {}
        if sorted(doc.get("declared_features") or []) != ["charts", "forms"]:
            fails.append("features in the config do not reach the applicability gate "
                         f"(got {doc.get('declared_features')!r})")

        # --- app.* must reach the runtime driver
        write("app:\n  dev_url: http://127.0.0.1:9/\n  api_pattern: '**/x/**'\n"
              "  routes: ['/a']\n  viewports: [360]\n")
        for key, want in (("app.dev_url", "http://127.0.0.1:9/"),
                          ("app.api_pattern", "**/x/**"),
                          ("app.routes", "/a"), ("app.viewports", "360")):
            got = subprocess.run([sys.executable, str(HERE / "uxconfig.py"),
                                  "--get", key, "--config", str(cfg)],
                                 capture_output=True, text=True).stdout.strip()
            if got != want:
                fails.append(f"{key} is not readable by the shell driver "
                             f"(got {got!r}, want {want!r})")

        # --- and every key the template ships must be one this test covers
        covered = {"app", "features", "thresholds", "disabled_checks", "exclude"}
        stray = set(tmpl or {}) - covered
        if stray:
            fails.append(f"ux.config.yaml documents {sorted(stray)}, which no wiring "
                         "test covers -- either wire it or remove it from the template")

    for f in fails:
        print(f"  FAIL {f}")
    return fails


def no_shipped_bytecode():
    """No .pyc anywhere in the skill tree.

    A directory-source plugin install copies the working tree verbatim, so stray
    bytecode ships to consumers despite being gitignored. Every entry point sets
    sys.dont_write_bytecode, but that cannot protect a module from its own .pyc --
    the importer writes that before the module body ever runs -- so any bare
    `python3 -c "from checks import ..."` reintroduces it. Catch it here, loudly,
    rather than discovering it in somebody's installed plugin."""
    strays = sorted(p.relative_to(HERE.parent).as_posix()
                    for p in HERE.parent.rglob("__pycache__"))
    if strays:
        print(f"  FAIL bytecode present, which a plugin install would ship: "
              f"{', '.join(strays)}")
        print(f"       remove it: find {HERE.parent} -name __pycache__ -prune "
              f"-exec rm -rf {{}} +")
    return strays


def overlay_policy():
    """A page's CSP must change the tool's behaviour, in both directions.

    Two silent failures lived here. `ux_review.py serve` drops the
    `Content-Security-Policy` *header* on the way through, but a policy delivered
    as `<meta http-equiv>` sits in the body and survived, so the inline selection
    overlay was refused by the browser and the refusal went to the framed page's
    console -- not to the terminal the reviewer was watching. And `ux_select.py`
    appends a `<style>` element, which is inline style whatever world created it,
    so a strict `style-src` produced an overlay that was present and invisible.

    Both are now reported. These are the controls that keep them reported: each
    case asserts the detection fires, and each has a negative case that must NOT
    fire, because a matcher that flags every `<meta>` tag would "fix" this by
    breaking every page."""
    import re as _re
    fails = []
    sys.path.insert(0, str(HERE))
    import ux_review, cdp                                          # noqa: E402

    # --- meta CSP: positive cases -----------------------------------------
    positives = [
        '<meta http-equiv="Content-Security-Policy" content="script-src \'self\'">',
        "<meta http-equiv='content-security-policy' content=\"default-src 'none'\">",
        '<meta http-equiv=Content-Security-Policy-Report-Only content="x">',
    ]
    for src in positives:
        out, found = ux_review.strip_meta_csp(src)
        if len(found) != 1:
            fails.append(f"meta CSP not detected: {src[:60]}")
        elif "deuxui review" not in out:
            fails.append(f"meta CSP detected but not replaced: {src[:60]}")

    # --- meta CSP: negative cases (the thing an over-broad matcher breaks) --
    negatives = [
        '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="description" content="content-security-policy">',
        '<meta http-equiv="refresh" content="0;url=/x">',
    ]
    for src in negatives:
        out, found = ux_review.strip_meta_csp(src)
        if found or out != src:
            fails.append(f"a non-CSP meta tag was rewritten: {src[:60]}")

    # --- the overlay still reaches the document after neutralising ---------
    doc = ('<!doctype html><html><head>'
           '<meta http-equiv="Content-Security-Policy" content="script-src \'self\'">'
           '</head><body><h1>x</h1></body></html>').encode()
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out = ux_review.inject_into(doc, "__selftest__").decode()
    if "<script" not in out:
        fails.append("inject_into stopped injecting the overlay")
    if _re.search(r"http-equiv", out, _re.I):
        fails.append("inject_into left the document CSP in place")
    if "meta tag" not in err.getvalue():
        fails.append("inject_into neutralised a CSP without telling the operator")

    # --- the style probe is a real probe, not a constant -------------------
    class _Fake:
        def __init__(self, rules, width): self.r = {"rules": rules, "width": width}
        def call(self, *a, **k): return {"result": {"value": json.dumps(self.r)}}
        def close(self): pass
    if cdp.style_policy(_Fake(1, "123px"))["styled"] is not True:
        fails.append("style_policy calls a page that DID apply the rule unstyled")
    if cdp.style_policy(_Fake(0, "0px"))["styled"] is not False:
        fails.append("style_policy calls a page that refused the rule styled")
    if cdp.style_policy(_Fake(1, "0px"))["styled"] is not False:
        fails.append("style_policy trusts the rule count without measuring the effect")

    # --- the opt-in suspension: asked for, measured, and put back ----------
    #
    # This flag stands a page's Content-Security-Policy down, so the controls are
    # about restraint rather than capability: that it is never used unasked, that
    # asking for it is never mistaken for it having worked, and that enforcement is
    # always put back before the run ends.
    REFUSED, APPLIED = {"rules": 0, "width": "0px"}, {"rules": 1, "width": "123px"}

    class _Ws:
        """A page that answers the style probe, and records what was asked of it."""

        def __init__(self, *answers):
            self.answers, self.calls = list(answers), []

        def call(self, method, params=None):
            self.calls.append((method, (params or {}).get("enabled")))
            if method == "Runtime.evaluate":
                a = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
                return {"result": {"value": json.dumps(a)}}
            return {}

        def close(self):
            pass

        def asked(self):
            return [en for m, en in self.calls if m == "Page.setBypassCSP"]

    ws = _Ws(REFUSED)
    pol = cdp.overlay_policy(ws, False)
    if ws.asked():
        fails.append("overlay_policy stood a page's CSP down without being asked")
    if pol["styled"] is not False or pol["bypassed"]:
        fails.append("overlay_policy without the flag changed the measured answer")

    ws = _Ws(APPLIED)
    cdp.overlay_policy(ws, True)
    if ws.asked():
        fails.append("overlay_policy touched the policy of a page that was already "
                     "permitting the stylesheet -- nothing needed standing down")

    ws = _Ws(REFUSED, APPLIED)
    pol = cdp.overlay_policy(ws, True)
    if pol["styled"] is not True or not pol["bypassed"]:
        fails.append("overlay_policy did not report a suspension that demonstrably "
                     "worked")
    if ws.asked() != [True]:
        fails.append(f"a working suspension made the wrong calls: {ws.asked()}")
    ws2 = _Ws(REFUSED, APPLIED)
    cdp.restore_csp(ws2, cdp.overlay_policy(ws2, True))
    if ws2.asked() != [True, False]:
        fails.append(f"enforcement was not restored after the run: {ws2.asked()}")

    # Asking is not evidence that it worked. If styling still fails, something other
    # than this page's CSP is refusing the stylesheet, and leaving enforcement off
    # would have weakened the page for nothing.
    ws = _Ws(REFUSED, REFUSED)
    pol = cdp.overlay_policy(ws, True)
    if pol["styled"] is True or pol["bypassed"]:
        fails.append("overlay_policy reported styled because the flag was PASSED, "
                     "not because a stylesheet was observed to apply")
    if ws.asked() != [True, False]:
        fails.append(f"a suspension that did not help was left in place: {ws.asked()}")

    ws = _Ws(APPLIED)
    cdp.restore_csp(ws, {"styled": True, "bypassed": False})
    if ws.asked():
        fails.append("restore_csp touched the policy of a page this run never changed")

    for f in fails:
        print(f"  FAIL {f}")
    return fails


def element_spans():
    """Every way a naive `<`/`>` scan gets an element's boundaries wrong.

    Structural edits -- `ux_live.py wrap` and `insert` -- need to know where an element
    opens and closes. Each case below is a `<` or `>` in real code that is not a tag
    boundary, and getting any of them wrong shifts the span by a few characters, which
    is worse than failing: the edit still applies and still looks plausible in a diff.

    The refusal cases matter as much as the matches. A resolver that always answers is
    the thing this must not become."""
    import jsxspan                                                   # noqa: E402
    fails = []
    cases = [
        ("plain jsx", '<div className="c">\n  <h3>Boiler service</h3>\n</div>',
         "Boiler service", "h3", None),
        ("arrow fn in an attribute",
         '<button onClick={() => setOpen(!open)}>Save changes</button>',
         "Save changes", "button", None),
        # Self-closing on purpose: with a real `</Cell>` present this case passed even
        # with brace tracking removed, because the span's outer brackets do not move.
        # It only discriminates when the `>` inside the expression would be mistaken
        # for the tag's end and the element would then look unclosed.
        ("comparison inside a self-closing tag's expression",
         '<div><Cell value={a > b ? a : b} label="Total due amount" /></div>',
         "Total due amount", "Cell", None),
        ("bare > inside an attribute string",
         '<p title="a > b">Read the terms</p>', "Read the terms", "p", None),
        ("typescript generic",
         'const [r] = useState<Row[]>([]);\n<ul><li>First item</li></ul>',
         "First item", "li", None),
        # The commented tag must be UNBALANCED and inside the enclosing element. A
        # commented `<Legacy />` is a self-closing sibling, so the span survives even
        # when comments are not skipped -- that version of this case proved nothing.
        ("unbalanced close tag inside a jsx comment",
         '<div className="w">\n  {/* </div> removed in v2 */}\n  <p>Live copy</p>\n</div>',
         "Live copy", "div", "div"),
        # A commented CLOSE tag, which would pop a real open element and end its span
        # early. A commented OPEN tag only leaves an orphan on the stack, so it proves
        # nothing -- that was the first version of this case.
        ("unbalanced close tag inside a line comment",
         '<section>\n  // </section> old markup\n  <p>Current label</p>\n</section>',
         "Current label", "section", "section"),
        # A close tag inside a JS string, positioned so that failing to skip the string
        # would pop the enclosing element and end its span before the anchor. A string
        # OUTSIDE the markup proves nothing -- the stray close pops an empty stack and
        # is discarded, so that version of this case passed with string skipping removed.
        ("close tag inside a js string, inside the element",
         '<section>\n  const s = "</section>";\n  <p>Kept copy</p>\n</section>',
         "Kept copy", "section", "section"),
        ("tag inside a block comment",
         '/* <Old>x</Old> */\n<div><b>Bold thing</b></div>', "Bold thing", "b", None),
        ("self-closing", '<div><img alt="A chart of revenue" /></div>',
         "A chart of revenue", "img", None),
        ("void element left unclosed",
         '<form><input placeholder="Email address"><button>Go</button></form>',
         "Email address", "input", None),
        ("nested same tag name",
         '<div class="o"><div class="i">Inner text</div></div>', "Inner text",
         "div", None),
        ("a script body is not markup",
         '<body><script>if (a<b){x("H")}</script><h1>Real heading</h1></body>',
         "Real heading", "h1", None),
        ("template literal holding a tag",
         '<div>{`<Fake />`}<em>Emphasis here</em></div>', "Emphasis here", "em", None),
        # the picked tag decides which enclosing element is meant
        ("container picked, not its child",
         '<section class="p">\n  <h1>Plans that scale</h1>\n</section>',
         "Plans that scale", "section", "section"),
        ("child picked, not its container",
         '<section class="p">\n  <h1>Plans that scale</h1>\n</section>',
         "Plans that scale", "h1", "h1"),
    ]
    for label, src, anchor_, want, tag in cases:
        r = jsxspan.find(src, anchor_, tag)
        if not r["found"]:
            fails.append(f"span not resolved ({label}): {r['why']}")
        elif r["name"] != want:
            fails.append(f"span resolved to <{r['name']}>, wanted <{want}> ({label})")
        elif src[r["start"]:r["end"]] != r["source"]:
            fails.append(f"span offsets do not match its own source ({label})")

    # Repeated markup. A structural edit inside a `.map()` is authored once and renders
    # once per row, so "wrapped the element" is really "wrapped every row of the table".
    # This is the one thing a per-framework AST adapter buys that a textual resolver
    # otherwise cannot answer -- and the question that actually decides whether the edit
    # is safe is answerable from the file alone.
    repeats = [
        ("react map", '<ul>{rows.map(r => <li className="row">Row copy</li>)}</ul>',
         "Row copy", True),
        ("forEach", '<div>{rows.forEach(r => <li>Row copy</li>)}</div>', "Row copy", True),
        ("svelte each", '{#each rows as r}\n  <li>Row copy</li>\n{/each}',
         "Row copy", True),
        ("vue v-for", '<ul><li v-for="r in rows">Row copy</li></ul>', "Row copy", True),
        # `\b` before `*ngFor` can never match -- the character before `*` is a space,
        # and two non-word characters have no boundary between them. Angular's form was
        # silently undetectable until the pattern used a lookbehind.
        ("angular ngFor", '<ul><li *ngFor="let r of rows">Row copy</li></ul>',
         "Row copy", True),
        ("alpine x-for", '<template x-for="r in rows"><li>Row copy</li></template>',
         "Row copy", True),
        # Negatives: each one is a way to claim a repeat that is not there.
        ("plain markup", '<ul><li className="row">Row copy</li></ul>', "Row copy", False),
        ("a map named in prose", '<p>call rows.map yourself</p><b>Row copy</b>',
         "Row copy", False),
        ("a map that closes first", '<div>{a.map(x => <i>{x}</i>)}</div><b>Row copy</b>',
         "Row copy", False),
        ("a look-alike attribute", '<li data-v-format="x">Row copy</li>',
         "Row copy", False),
    ]
    for label, src, anchor_, want in repeats:
        r = jsxspan.find(src, anchor_)
        if not r["found"]:
            fails.append(f"span not resolved for the repeat case ({label})")
            continue
        got = bool(r.get("repeated"))
        if got != want:
            fails.append(f"jsxspan repeat detection said {got}, wanted {want} "
                         f"({label}) -- a missed repeat edits every row without "
                         f"saying so, and a false one warns about code that runs once")
    # Following a component boundary -- the one thing a per-framework source adapter
    # buys that a textual resolver otherwise cannot. An element rendered by
    # `<Card title="Starter" />` resolves to the USAGE; somebody who wants every card to
    # change needs Card's own file, and reporting only the usage sends them to edit one
    # call site and wonder why the other eleven did not move.
    with tempfile.TemporaryDirectory() as _d9:
        _r9 = Path(_d9)
        (_r9 / "src").mkdir()
        (_r9 / "src" / "Card.tsx").write_text(
            'export function Card({ title }) {\n'
            '  return <article className="card"><h3>{title}</h3></article>;\n}\n')
        (_r9 / "src" / "Pricing.tsx").write_text(
            'import { Card } from "./Card";\n'
            'export default function Pricing() {\n'
            '  return <div className="grid"><Card title="Starter" /></div>;\n}\n')
        (_r9 / "node_modules").mkdir()
        (_r9 / "node_modules" / "Card.tsx").write_text(
            'export function Card() { return null; }\n')
        _cs = jsxspan.component_source("Card", _r9)
        if not _cs.get("found"):
            fails.append(f"component_source could not find Card: {_cs.get('why')}")
        elif _cs["file"] != "src/Card.tsx":
            fails.append(f"component_source resolved Card to {_cs['file']}; "
                         f"node_modules must never be searched or every third-party "
                         f"component shadows the project's own")
        # Resolving the element INSIDE the definition. I wrote that this needs the
        # render graph; it does not, for the case that comes up. A node picked on screen
        # carries a class, and that class is authored in the component's own file --
        # scoped to one file, a class ambiguous across a project is usually unique.
        # `p-4` appears on two elements and `card-row` on two: a class that is not
        # unique inside the file identifies nothing, and a utility class identifies
        # nothing anywhere. Without both in the fixture, relaxing `n == 1` to `n >= 1`
        # and deleting the utility guard changed no outcome, so those two controls
        # passed with the code removed.
        (_r9 / "src" / "Card.tsx").write_text(
            'export function Card({ title, price }) {\n'
            '  return (\n'
            '    <article className="card p-4">\n'
            '      <h3 className="card-title">{title}</h3>\n'
            '      <p className="card-price p-4">{price}</p>\n'
            '      <span className="card-row">a</span>\n'
            '      <span className="card-row">b</span>\n'
            '    </article>\n  );\n}\n')
        _in = jsxspan.inside_component("Card", _r9,
                                       {"classes": "card-title", "tag": "h3"})
        if not _in.get("found"):
            fails.append(f"inside_component could not place a picked <h3.card-title> "
                         f"in the component that authors that class: {_in.get('why')}")
        elif (_in["file"], _in["name"]) != ("src/Card.tsx", "h3"):
            fails.append(f"inside_component resolved to {_in.get('file')} "
                         f"<{_in.get('name')}>, wanted src/Card.tsx <h3>")
        # It must resolve to the RIGHT sibling, not just into the right file.
        _in2 = jsxspan.inside_component("Card", _r9,
                                        {"classes": "card-price", "tag": "p"})
        if not _in2.get("found") or _in2.get("name") != "p":
            fails.append("inside_component did not distinguish two siblings in the same "
                         "component, so a structural edit would land on whichever came "
                         "first")
        elif _in2["line"] == (_in.get("line") if _in.get("found") else None):
            fails.append("inside_component gave two different elements the same line")
        # No class at all, but the tag is unique in the definition. I wrote this case
        # off with the rest of the classless ones; it is decidable without a render
        # graph, because when there is exactly one element of that tag there is nothing
        # for position to disambiguate.
        with tempfile.TemporaryDirectory() as _da:
            _ra = Path(_da)
            (_ra / "One.tsx").write_text(
                'export function One() {\n'
                '  return <div className="w"><h3>{t}</h3><p>{p}</p></div>;\n}\n')
            (_ra / "Many.tsx").write_text(
                'export function Many() {\n'
                '  return <ul className="l"><span>a</span><span>b</span></ul>;\n}\n')
            _one = jsxspan.inside_component("One", _ra, {"classes": "", "tag": "h3"})
            if not _one.get("found") or _one.get("name") != "h3":
                fails.append(f"inside_component refused a classless element whose tag "
                             f"appears exactly once in the component; there is nothing "
                             f"for position to disambiguate: {_one.get('why')}")
            _many = jsxspan.inside_component("Many", _ra, {"classes": "", "tag": "span"})
            if _many.get("found"):
                fails.append("inside_component picked one of two identical <span>s with "
                             "nothing to tell them apart -- THAT is the case that needs "
                             "the render graph, and guessing lands the edit on the wrong "
                             "one half the time")
            elif "2 <span>" not in str(_many.get("why", "")):
                fails.append("inside_component refused an ambiguous tag without saying "
                             "how many candidates there were")

        # The case that genuinely CANNOT resolve. This used to assert that ANY classless
        # element was undecidable, which stopped being true when the unique-tag fallback
        # landed: `Card` has exactly one `<h3>`, so it resolves now and should. The
        # undecidable case is narrower -- two `card-row` spans with nothing to tell them
        # apart -- and asserting the old limit would have blocked a correct improvement.
        _no = jsxspan.inside_component("Card", _r9, {"classes": "", "tag": "span"})
        if _no.get("found"):
            fails.append("inside_component placed one of two identical <span>s with "
                         "nothing to tell them apart -- that is the case that needs the "
                         "render graph and it must refuse")
        elif "render graph" not in str(_no.get("why", "")):
            fails.append("inside_component refused without saying what would be needed "
                         "to resolve it, so the refusal is a dead end")
        # A utility class is not an identity even when it is UNIQUE in the file. That
        # is the only form of this case that discriminates: with two occurrences, find()
        # refuses on its own and the guard proves nothing. `mt-8` here is on exactly one
        # element, and matching it is still coincidence -- the next sibling to get a
        # margin moves the same pick somewhere else.
        # TWO <b>s, so the tag fallback cannot decide it either and only the class
        # could -- which is the only arrangement where the utility guard is what
        # determines the outcome. With one <b> the element resolves by tag, correctly,
        # and this case proved nothing about the guard.
        (_r9 / "src" / "Solo.tsx").write_text(
            'export function Solo() {\n'
            '  return (\n    <section className="wrap">\n'
            '      <b className="mt-8">x</b>\n      <b>y</b>\n'
            '    </section>\n  );\n}\n')
        _util = jsxspan.inside_component("Solo", _r9, {"classes": "mt-8", "tag": "b"})
        if _util.get("found"):
            fails.append("inside_component located an element by a utility class that "
                         "happened to be unique in the file; `mt-8` says how much margin "
                         "it has, not which element it is")
        for _c in ("p-4", "px-2", "w-full", "flex", "z-10", "h-[42px]"):
            if not jsxspan.UTILITY.match(_c):
                fails.append(f"jsxspan.UTILITY does not recognise {_c!r} as a utility "
                             f"class")
        for _c in ("card-title", "hero-banner", "PricingCard"):
            if jsxspan.UTILITY.match(_c):
                fails.append(f"jsxspan.UTILITY called {_c!r} a utility class, which "
                             f"would throw away the one anchor that identifies it")
        # A class that is in the file TWICE is not a location either.
        _dup = jsxspan.inside_component("Card", _r9,
                                        {"classes": "card-row", "tag": "span"})
        if _dup.get("found"):
            fails.append("inside_component placed an element by a class that appears "
                         "twice in the same component, so the edit lands on whichever "
                         "came first")

        # The four shapes a definition takes.
        for src, how in (('export default function Widget() {}', "export default"),
                         ('function Widget() {}', "function"),
                         ('const Widget = () => null;', "const"),
                         ('class Widget extends React.Component {}', "class")):
            with tempfile.TemporaryDirectory() as _dd:
                _rr = Path(_dd)
                (_rr / "W.tsx").write_text(src + "\n")
                if not jsxspan.component_source("Widget", _rr).get("found"):
                    fails.append(f"component_source missed a component declared as "
                                 f"{how!r}")
        # A lowercase tag is a DOM element, not a component. Asserted on the REASON,
        # not on found/not-found: with the guard removed it searches for `function div`,
        # finds nothing and still returns not-found, so the first version of this case
        # passed with the guard deleted and only the message was lost -- and the message
        # is the whole value, because "no file defines div" sends somebody looking for a
        # file that cannot exist.
        _dv = jsxspan.component_source("div", _r9)
        if _dv.get("found"):
            fails.append("component_source claimed a definition for <div>")
        elif "not a component name" not in str(_dv.get("why", "")):
            fails.append(f"component_source said {str(_dv.get('why'))[:60]!r} for a "
                         f"lowercase tag; it has to say a DOM element has no definition "
                         f"to find, or the refusal reads as a missing file")
        # Two definitions of one name is a real thing, and picking the first is how an
        # edit lands in the wrong package.
        (_r9 / "src" / "legacy").mkdir()
        (_r9 / "src" / "legacy" / "Card.tsx").write_text(
            'export const Card = () => null;\n')
        _amb = jsxspan.component_source("Card", _r9)
        if _amb.get("found"):
            fails.append("component_source picked one of two files defining Card "
                         "instead of refusing; which renders the element is not "
                         "established from the name alone")
        elif len(_amb.get("candidates") or []) < 2:
            fails.append("component_source refused an ambiguous component without "
                         "listing the candidates, so the refusal is a dead end")

    _fe = jsxspan.find('<div>{rows.forEach(r => <li>Row copy</li>)}</div>', "Row copy")
    if "forEach" not in (_fe.get("repeated") or {}).get("kind", ""):
        fails.append("jsxspan reported a .forEach() as a .map(), which is a small lie "
                     "about somebody's code in text they read to decide if an edit is "
                     "safe")

    refusals = [
        ("the anchor appears twice", '<p>Repeat</p><p>Repeat</p>', "Repeat", None),
        ("the anchor is absent", '<p>Something</p>', "Absent text", None),
        ("no closing tag at all", '<div class="x">Dangling copy', "Dangling copy", None),
        ("the picked tag is nowhere around it",
         '<div><h1>Plans that scale</h1></div>', "Plans that scale", "button"),
    ]
    for label, src, anchor_, tag in refusals:
        r = jsxspan.find(src, anchor_, tag)
        if r["found"]:
            fails.append(f"a span was resolved where it must refuse ({label}): "
                         f"<{r['name']}>")

    # `verify` is exercised directly. `find` rejects a non-unique anchor before verify
    # ever sees one, so going through `find` could never test this check -- and a
    # control that cannot fail is the thing this whole skill is about.
    _src = '<ul><li>Repeat</li><li>Repeat</li></ul>'
    _span = {"name": "ul", "start": 0, "end": len(_src), "open_end": 4, "self": False}
    _ok, _why = jsxspan.verify(_src, _span, "Repeat")
    if _ok:
        fails.append("verify() accepted a span containing the anchor twice, so an edit "
                     "would move more than the element that was picked")
    _span2 = {"name": "li", "start": 4, "end": 19, "open_end": 8, "self": False}
    if not jsxspan.verify(_src, _span2, "Repeat")[0]:
        fails.append("verify() rejected a span that contains the anchor exactly once")

    for f in fails:
        print(f"  FAIL {f}")
    return fails


def capabilities():
    """Do the generators and gates actually DO their job, or only start?

    `parity.py --deep` proves every cited script starts. That is a real check and it is
    a weak one: a generator that runs and emits an off-scale ladder satisfies it, and a
    gate that runs and permits everything satisfies it too. This asserts the property
    each one exists FOR, on the five capabilities that were measurable and unmeasured.

    Each case is the claim the tool makes about itself in SKILL.md, turned into a
    question with an answer."""
    fails = []
    sys.path.insert(0, str(HERE))

    # 1. palette: "every pair contrast-checked". A generated ramp whose roles do not
    #    clear the contrast they owe is the one thing this generator must never emit.
    import palette                                                   # noqa: E402
    try:
        pal = palette.build(hue=250)
    except Exception as e:
        pal = None
        fails.append(f"palette.build raised {type(e).__name__}: {e}")
    if isinstance(pal, dict):
        need = {"canvas", "surface", "ink", "muted", "interactive"}
        missing = need - set(pal.get("roles") or {})
        if missing:
            fails.append(f"palette.build omitted the role(s) {sorted(missing)}, which "
                         f"every contract declares")
        # The generator reports the pairs it measured. A pair it emits below the ratio
        # that pair owes is the one thing this generator must never produce.
        owed = {"ink on canvas": 4.5, "muted on canvas": 4.5}
        got = dict(pal.get("pairs") or [])
        for pair, floor in owed.items():
            v = got.get(pair)
            if v is None:
                fails.append(f"palette.build did not report the pair {pair!r}, so "
                             f"nothing establishes that it clears {floor}:1")
            elif v < floor:
                fails.append(f"palette.build emitted {pair} at {v}:1, below the "
                             f"{floor}:1 it exists to guarantee")

    # 2. typescale: rungs that carry different jobs. Two adjacent steps a reader cannot
    #    tell apart are not a hierarchy, whatever the ratio claims.
    import typescale                                                 # noqa: E402
    try:
        ladder = typescale.build(body=17, ratio=1.25)
        px = [r["px"] for r in ladder["rungs"] if isinstance(r, dict) and r.get("px")]
        if len(px) < 4:
            fails.append(f"typescale produced {len(px)} rung(s); a ladder that short "
                         f"cannot carry display, heading, body and caption")
        flat = [(a, b) for a, b in zip(px, px[1:]) if a and b and max(a, b) / min(a, b) < 1.12]
        if flat:
            fails.append(f"typescale produced adjacent steps under 1.12x apart "
                         f"({flat[:2]}), which read as the same size")
    except Exception as e:
        fails.append(f"typescale.build raised {type(e).__name__}: {e}")

    # 3. comp_spec provenance: "records an asset's provenance INSIDE the PNG". An
    #    asset whose origin lives only in a chat message cannot be regenerated.
    import pngread                                                   # noqa: E402
    # A fixture that ships, so this case is never silently skipped. The first version
    # pointed at a PNG that does not exist in this tree, so the whole provenance check
    # was a no-op that reported "all ok" -- a check that cannot run is the thing this
    # skill is about, and it managed to be one.
    shot = FIX / "provenance.png"
    if not shot.exists():
        fails.append(f"{shot.name} is missing, so the provenance round-trip cannot be "
                     f"checked at all")
    else:
        with tempfile.TemporaryDirectory() as d:
            q = Path(d) / "a.png"
            q.write_bytes(shot.read_bytes())
            note = "selftest: written by capabilities()"
            if not pngread.add_text(q, "deuxui-provenance", note):
                fails.append("pngread.add_text could not write provenance into a PNG")
            elif pngread.text_chunks(q).get("deuxui-provenance") != note:
                fails.append("provenance written into a PNG did not read back, so an "
                             "asset's origin is not actually recorded in the file")
            try:
                pngread.rows(q)
            except Exception as e:
                fails.append(f"a PNG carrying provenance no longer decodes: "
                             f"{type(e).__name__}: {e}")

    # 4. the phase gate: "refuses production UI edits before a direction is approved",
    #    and is opt-in -- with no phase.yaml nothing is refused.
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        (r / "app").mkdir()
        target = r / "app" / "page.tsx"
        target.write_text("export default () => <div>x</div>;\n")
        cwd = os.getcwd()
        try:
            os.chdir(r)
            opt_in = subprocess.run(
                [sys.executable, str(HERE / "ux_phase.py"), "gate", "write",
                 str(target)], capture_output=True, text=True)
            if opt_in.returncode != 0:
                fails.append("the phase gate refused a write in a project with no "
                             "phase.yaml; it is opt-in, and refusing by default would "
                             "block every project that never asked for it")
            subprocess.run([sys.executable, str(HERE / "ux_phase.py"), "init"],
                           capture_output=True, text=True)
            closed = subprocess.run(
                [sys.executable, str(HERE / "ux_phase.py"), "gate", "write",
                 str(target)], capture_output=True, text=True)
            if closed.returncode == 0:
                fails.append("the phase gate PERMITTED a production UI edit in a "
                             "freshly initialised project, where nobody has approved "
                             "anything -- the gate is the whole argument and it was open")
        finally:
            os.chdir(cwd)

    # 5. ux_proto: "conformant by construction, so running the checks over its output
    #    is a positive control on the generator".
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        (r / ".deuxui").mkdir()
        shutil.copy(FIX / "design.contract.yaml", r / ".deuxui" / "design.contract.yaml")
        out = r / "proto.html"
        cwd = os.getcwd()
        try:
            os.chdir(r)
            g = subprocess.run([sys.executable, str(HERE / "ux_proto.py"),
                                "--write", str(out), "--title", "Selftest"],
                               capture_output=True, text=True)
        finally:
            os.chdir(cwd)
        if not out.exists() or out.stat().st_size < 2000:
            fails.append(f"ux_proto wrote no usable prototype (exit {g.returncode})")
        else:
            body = out.read_text(errors="replace")
            for must, why in (("<dialog", "a dialog that traps focus"),
                              ("<table", "a table"),
                              ("aria-", "any ARIA at all")):
                if must not in body:
                    fails.append(f"the generated prototype contains no {must!r} -- it "
                                 f"is advertised as having {why}")

    # 6. fontindex.classify: which family class a declared face belongs to. Two bugs,
    #    both reachable from `--pair` and from `pairing()`, which classify raw input:
    #    a STACK is not a face, and `sans-serif` contains `serif` -- with serif ordered
    #    before sans in the token table, the commonest generic in CSS classified as a
    #    serif and then drove pairing advice about a clash that did not exist.
    import fontindex                                                 # noqa: E402
    for face, want in (("ui-sans-serif, system-ui, sans-serif", "sans"),
                       ("sans-serif", "sans"),
                       ("ui-serif, Georgia, serif", "serif"),
                       ("ui-monospace, SFMono-Regular, Menlo, monospace", "mono"),
                       ("Inter", "sans"),
                       ("Playfair Display", "serif"),
                       # Stacks whose PRIMARY disagrees with what the whole string
                       # matches. Without these, dropping `primary()` from classify
                       # changed nothing measurable -- every other case here happens to
                       # land the same either way, so the control passed with the
                       # resolution deleted.
                       ("Inter, Georgia, serif", "sans"),
                       ("Georgia, Inter, sans-serif", "serif")):
        got = fontindex.classify(face)
        if got != want:
            fails.append(f"fontindex.classify({face[:34]!r}) said {got!r}, wanted "
                         f"{want!r}")

    # 7. fontindex.analyse: "refuses to treat the build host's own fonts as evidence
    #    about a visitor". A generic stack needs no file and must not read as missing.
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        (r / "app.css").write_text(
            "body{font-family:ui-sans-serif,system-ui,sans-serif}\n"
            "h1{font-family:'Nonexistent Face',serif}\n")
        a = fontindex.analyse(r, {"type": {"families": {
            "body": "ui-sans-serif, system-ui, sans-serif",
            "display": "Nonexistent Face, serif"}}})
        blob = json.dumps(a)
        if "Nonexistent Face" not in blob:
            fails.append("fontindex.analyse did not mention a declared face that is "
                         "nowhere in the project, so a contract can name a typeface "
                         "no visitor will ever render")

    # 8. comp_spec.analyse: the measurement comp_diff is built on. A flat single-colour
    #    image must read as one flat region, not as imagery.
    import comp_spec, pngread                                        # noqa: E402
    if (FIX / "provenance.png").exists():
        s = comp_spec.analyse(pngread.rows(FIX / "provenance.png"))
        if s["counts"]["plate"]:
            fails.append("comp_spec called a flat single-colour image photographic, "
                         "which would ship a solid fill as a raster")
        if not s.get("canvas"):
            fails.append("comp_spec reported no canvas colour for an image that is "
                         "entirely one colour")

    # 9. derive_contract: brownfield's first move. It has to find values that ARE in
    #    the code and must not invent ones that are not.
    import derive_contract                                           # noqa: E402
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        (r / "s.css").write_text(
            ":root{--x:1}\n.a{border-radius:10px;font-size:17px}\n"
            ".b{border-radius:10px;font-size:27px}\n.c{border-radius:10px}\n")
        got = json.dumps(derive_contract.build(derive_contract.scan(r)))
        if "10" not in got:
            fails.append("derive_contract did not derive a radius that appears three "
                         "times in the stylesheet it was pointed at")

    # 10. ux_question: with nothing recorded it must SAY so rather than print something
    #     that reads as a clean pass. The first version of this case asserted it should
    #     exit non-zero -- wrong, and the tool was right: `check` verifies the decisions
    #     that exist, and having none to verify is not a failure of the verifier. The
    #     NOT_RUN belongs to the rules that need an approval, which is doctor's row and
    #     ux_report's status, so that is what gets asserted.
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        cwd = os.getcwd()
        try:
            os.chdir(r)
            q = subprocess.run([sys.executable, str(HERE / "ux_question.py"), "check"],
                               capture_output=True, text=True)
        finally:
            os.chdir(cwd)
        said = (q.stdout + q.stderr).lower()
        if "no decision" not in said:
            fails.append(f"ux_question check said {said.strip()[:60]!r} in a project "
                         f"with no decisions; it has to state that there are none, or "
                         f"its silence reads as everything being in order")
        doc0 = subprocess.run([sys.executable, str(HERE / "doctor.py"), str(r)],
                              capture_output=True, text=True)
        if "GOV-011" not in (doc0.stdout + doc0.stderr):
            fails.append("doctor did not name the rules that stay NOT_RUN when nobody "
                         "has approved a direction, so the cost of the gap is invisible")

    # 11. doctor: "names every tier that cannot run, and what it costs in rules". A
    #     project with no contract must be TOLD that every S-CONTRACT-* rule is NOT_RUN.
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        (r / "app.tsx").write_text("export default () => <div>x</div>;\n")
        doc = subprocess.run([sys.executable, str(HERE / "doctor.py"), str(r)],
                             capture_output=True, text=True)
        out = doc.stdout + doc.stderr
        if "contract" not in out.lower():
            fails.append("doctor said nothing about the missing visual contract, so a "
                         "reader cannot tell that every conformance rule is NOT_RUN")
        if doc.returncode == 0:
            fails.append("doctor exited 0 in a project missing its contract and its "
                         "manual sheet; exit 2 is what stops CI going green on a "
                         "fraction of the rules")

    # 12. ux_browser.sh -- the runtime driver's ORCHESTRATION, which nothing tested.
    #     `browsertest.py` runs the probe JS directly against a fixture with known
    #     defects, so the numbers are checked against real pixels; the shell that reads
    #     the config, walks the viewports and decides what to write was never exercised.
    #     What matters about it is not the happy path: it is that when the tier cannot
    #     run, it says so in a form `ux_report` can read as NOT_RUN. A driver that exits
    #     quietly leaves a report with no runtime section at all, which reads as though
    #     the runtime rules were fine.
    drv = HERE / "ux_browser.sh"
    if not drv.exists():
        fails.append("ux_browser.sh is missing; the whole runtime tier has no driver")
    else:
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            cwd = os.getcwd()
            try:
                os.chdir(r)
                # No base URL and no config: must refuse with usage, not proceed.
                nourl = subprocess.run(["bash", str(drv)], capture_output=True,
                                       text=True, timeout=120)
                if nourl.returncode == 0:
                    fails.append("ux_browser.sh exited 0 with no base URL and no "
                                 "app.dev_url, so a run that measured nothing would "
                                 "look like a run that passed")
                if "usage" not in (nourl.stdout + nourl.stderr).lower():
                    fails.append("ux_browser.sh refused without a base URL but did not "
                                 "say how to give it one")
                # A browser that is not installed: must WRITE the unavailable record
                # and exit 3, the documented "runtime tier unavailable".
                # PATH with agent-browser's directory removed, rather than a bogus
                # PATH: the script needs bash, python3 and coreutils to reach the check
                # at all, and emptying PATH just made it fail to start, which proved
                # nothing about the branch under test.
                ab = shutil.which("agent-browser")
                keep = [x for x in os.environ.get("PATH", "").split(os.pathsep)
                        if x and (not ab or not ab.startswith(x.rstrip("/") + "/"))]
                env = dict(os.environ, PATH=os.pathsep.join(keep))
                gone = subprocess.run(
                    ["bash", str(drv), "http://127.0.0.1:1", "--out", "rt"],
                    capture_output=True, text=True, env=env, timeout=120)
                rec = r / "rt" / "runtime.json"
                if gone.returncode != 3:
                    fails.append(f"ux_browser.sh exited {gone.returncode} with no "
                                 f"agent-browser on PATH; 3 is the documented code for "
                                 f"an unavailable runtime tier and the callers branch "
                                 f"on it")
                if not rec.exists():
                    fails.append("ux_browser.sh wrote no runtime.json when the browser "
                                 "was unavailable, so the merged report has no runtime "
                                 "section at all -- which reads as the runtime rules "
                                 "being fine rather than unrun")
                else:
                    try:
                        got = json.loads(rec.read_text())
                    except ValueError as e:
                        got = {}
                        fails.append(f"ux_browser.sh wrote unreadable runtime.json: {e}")
                    if got.get("available") is not False:
                        fails.append("runtime.json does not say `available: false` when "
                                     "the browser is missing, so nothing downstream can "
                                     "tell an unavailable tier from an empty one")
                    if not str(got.get("reason") or "").strip():
                        fails.append("runtime.json records no reason for the tier being "
                                     "unavailable, so the report can say NOT_RUN but not "
                                     "why")
            finally:
                os.chdir(cwd)

    # 8. the parity matrix's own two refusals. The rule that a `mapped` row may not
    #    carry a `gap` is what caught a too-generous claim of mine in v5.10.0, and it
    #    had never been exercised -- with one matrix in the tree there was nothing to
    #    hand it that breaks the rule. Both directions, plus the real file resolving,
    #    because a rule that refuses everything is no better than one that refuses
    #    nothing.
    import parity
    with tempfile.TemporaryDirectory() as td:
        _m = Path(td) / "m.yaml"
        _head = "source: {project: t}\ncommands:\n  - name: t\n    here: y\n"
        for _body, _want, _why in (
                ("    status: mapped\n    gap: something is missing\n", False,
                 "a `mapped` row carrying a gap was accepted, so a row can read as "
                 "complete while something in it says otherwise"),
                ("    status: partial\n", False,
                 "a `partial` row with no gap was accepted, which is how this file "
                 "rots: a status softens and nobody can see what is still missing"),
                ("    status: mapped\n", True,
                 "a well-formed mapped row was refused, so the rule refuses "
                 "everything and proves nothing")):
            _m.write_text(_head + _body + "    evidence: [script:parity.py]\n")
            if parity.audit(False, _m)["ok"] is not _want:
                fails.append(_why)

    # 9. `--deep` names the row it is talking about. The first version bound `name`
    #    inside the evidence loop, three lines below the row's own `name`, so every row
    #    in the report read `None` -- a report that cannot say WHICH claim failed is not
    #    a report. Asserted against deep, because shallow never had the bug.
    #    Wrapped, because reinstating the shadow does not produce a nameless row -- it
    #    produces a TypeError deep inside `audit`, where `sorted()` meets a None among
    #    the names. A traceback is detection of a sort and a terrible report: it names a
    #    sort, not the claim that lost its name. Both outcomes say so by name now.
    try:
        _deep = parity.audit(True)
    except Exception as _e:
        _deep = {}
        fails.append(f"parity --deep raised {type(_e).__name__}: {_e} -- the rows it "
                     f"builds are malformed, most likely one with no name")
    if _deep and not _deep.get("scripts_run"):
        fails.append("parity --deep ran no scripts, so nothing was actually executed "
                     "and `deep` means nothing")
    _nameless = [i for i, x in enumerate(_deep.get("rows") or [])
                 if not str(x.get("name") or "").strip()]
    if _nameless:
        fails.append(f"parity --deep produced {len(_nameless)} row(s) with no name, so "
                     f"the report cannot say which claim it is describing")

    # 10. the negative half of the collapse case. `contract invariants` already
    #     asserts that two comp colours landing on one built colour is reported as a
    #     lost tonal step; nothing asserted the other direction, so a `collapsed` that
    #     fired on every faithful build would have passed. One colour matching one
    #     colour must stay silent. (Not a second copy of the positive case -- writing
    #     one was how I noticed the first was already there.)
    import comp_diff
    _fine = comp_diff.palette_diff(
        {"semantic": {"palette": [{"hex": "#1f5eff", "coverage_pct": 30.0}]}},
        {"semantic": {"palette": [{"hex": "#1f5eff", "coverage_pct": 31.0}]}})
    if _fine["collapsed"] or _fine["verdict"] != "AGREES":
        fails.append("comp_diff reports a collapsed tonal step when one comp colour "
                     "matched one built colour, so the finding fires on a faithful build")

    # 11. the defect ledger's own refusals. `references/defects.yaml` is the claim that
    #     every defect this skill has shipped is fixed AND guarded, and a list like that
    #     is the easiest document in a repository to stop believing. So the rules that
    #     keep it honest are exercised the same way parity's are: by handing the checker
    #     a file that breaks each one, and one that breaks none.
    import defects
    _good = {"id": "DEF-01", "title": "t", "class": "wrong-result",
             "found_in": "5.0.0", "fixed_in": "5.0.0", "surface": "scripts/selftest.py",
             "symptom": "s", "consequence": "c", "fix": "f",
             "guard": [{"file": "scripts/selftest.py", "text": "def capabilities"}],
             "control": [{"file": "scripts/selftest.py", "text": "def capabilities"}]}
    _bad_control = dict(_good, control=[{"file": "references/index.md", "text": "#"}])
    # Built by concatenation on purpose: written as one literal it would appear in THIS
    # file, which is the file the citation points at, and the case would pass while
    # proving nothing. The first version did exactly that.
    _absent = "def " + "no_such_" + "function_9f3a1c"
    _stale = dict(_good, guard=[{"file": "scripts/selftest.py", "text": _absent}])
    _future = dict(_good, fixed_in="99.0.0")
    _silent = {k: v for k, v in _good.items() if k != "control"}
    with tempfile.TemporaryDirectory() as td:
        _p = Path(td) / "d.yaml"
        for _row, _want, _why in (
                (_good, True, "a well-formed defect row was refused, so the ledger's "
                              "rules refuse everything and prove nothing"),
                (_bad_control, False,
                 "a reference document was accepted as a control -- a document cannot "
                 "catch a regression, which is the whole distinction this file draws"),
                (_stale, False,
                 "a guard citation that no longer resolves was accepted, so the ledger "
                 "can describe a fix that is no longer in the tree"),
                (_future, False,
                 "a fix claimed in a release that does not exist was accepted"),
                (_silent, False,
                 "a row with no control and no reason for having none was accepted, so "
                 "an unguarded fix can hide inside the total")):
            _p.write_text(yaml.safe_dump({"scope": "t", "defects": [_row]}))
            if defects.audit(_p)["ok"] is not _want:
                fails.append(_why)
    # 12. this file's own front door. It had no argument parsing, so `--help` ran the
    #     whole suite -- and `parity.py --deep` runs `--help` on every script it cites,
    #     this one included. The moment a group in here called `parity.audit(deep=True)`,
    #     one run spawned another, each with its own 60s timeout. Asserted rather than
    #     remembered: `--help` must answer immediately and must not run anything.
    try:
        _hr = subprocess.run([sys.executable, str(HERE / "selftest.py"), "--help"],
                             capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        # The shape the defect actually takes when reinstated. Caught and named rather
        # than raised: a traceback here reads as a broken test, not as the finding.
        _hr = None
        fails.append("selftest.py --help did not answer inside 25s, so it is running "
                     "the suite rather than describing it -- which is how `parity "
                     "--deep` came to spawn a run inside a run")
    if _hr is not None and _hr.returncode != 0:
        fails.append(f"selftest.py --help exits {_hr.returncode}, so every tool that "
                     f"probes a script by asking for help reports this one as broken")
    if _hr is not None and "SELFTEST" in (_hr.stdout + _hr.stderr):
        fails.append("selftest.py --help ran the suite instead of describing it, which "
                     "is how `parity --deep` came to spawn a run inside a run")

    _led = defects.audit()
    if not _led["ok"]:
        fails.append(f"the defect ledger does not resolve: {_led['problems'][:1]}")
    elif _led["counts"]["unguarded"]:
        # Not a failure -- an unguarded fix is allowed to exist and required to be
        # declared. It is surfaced here so it cannot sit in a file nobody reads.
        print(f"  note {_led['counts']['unguarded']} defect fix(es) are UNGUARDED; "
              f"python3 scripts/defects.py --unguarded")

    for f in fails:
        print(f"  FAIL {f}")
    return fails


def contract_checks():
    """Invariants the check corpus cannot catch on its own."""
    fails = []

    # Every count this skill states about ITSELF, checked against the thing counted.
    # These had drifted three separate ways at once: SKILL.md advertised 183 static
    # checks against 184, "one of the 30 operations" two lines above "all thirty-five",
    # and "213 of the 235 rules have an automated detector; the other 21" -- where the
    # two numbers do not even add up to 235, and the real split is 215 and 20.
    #
    # A number in prose is a claim like any other. Nobody recounts them by hand, so
    # they are recounted here.
    from collections import defaultdict
    _reg = yaml.safe_load((HERE.parent / "references/rules/registry.yaml").read_text())
    _det = yaml.safe_load((HERE.parent / "references/rules/detectors.yaml").read_text())
    _rules = _reg["rules"] if "rules" in _reg else _reg
    _dets = _det["detectors"] if "detectors" in _det else _det
    _items = (_dets.items() if isinstance(_dets, dict)
              else ((d["id"], d) for d in _dets))
    _by_rule, _eng = defaultdict(set), []
    for _k, _v in _items:
        _v = _v or {}
        _eng.append(_v.get("engine"))
        for _r in (_v.get("rules") or []):
            _by_rule[_r].add(_v.get("engine"))
    _ids = [r["id"] for r in _rules]
    facts = {
        "rules": len(_ids),
        # "static" is the TIER, not one engine: the engine table maps `source` and
        # `element` onto it. Counting `engine == "source"` gave 143 and would have
        # "corrected" a correct number in SKILL.md down to a wrong one -- a control
        # that enforces its own miscount is worse than no control.
        "static": sum(1 for e in _eng
                      if (_det.get("engines", {}).get(e) or {}).get("tier") == "static"),
        "automated": sum(1 for i in _ids if _by_rule.get(i, set()) - {"manual"}),
        "manual_only": sum(1 for i in _ids
                           if _by_rule.get(i) and not (_by_rule[i] - {"manual"})),
        "ops": len([q for q in (HERE.parent / "references/ops").glob("*.md")
                    if q.stem != "index"]),
        "workflows": len(list((HERE.parent / "references/workflows").glob("*.md"))),
    }
    skill = (HERE.parent / "SKILL.md").read_text()
    opsidx = (HERE.parent / "references/ops/index.md").read_text()
    _WORDS = {33: "thirty-three", 34: "thirty-four", 35: "thirty-five",
              36: "thirty-six", 37: "thirty-seven"}
    claims = [
        (skill, "SKILL.md", f"{facts['static']} source checks",
         r"(\d+) source checks"),
        (skill, "SKILL.md", f"{facts['automated']} of the {facts['rules']} rules",
         r"(\d+) of the \d+ rules have an automated detector"),
        (skill, "SKILL.md", f"the other {facts['manual_only']} are the manual tier",
         r"the other (\d+) are the manual tier"),
        (skill, "SKILL.md", f"one of the {facts['ops']} operations",
         r"one of the (\d+) operations"),
        (skill, "SKILL.md", f"The {facts['ops']} operations",
         r"The (\d+) operations"),
        (opsidx, "references/ops/index.md",
         f"{_WORDS.get(facts['ops'], facts['ops']).capitalize()} operations",
         r"^(\w+) operations"),
    ]
    import re as _re2
    for body, where, want, pat in claims:
        if want not in body:
            m = _re2.search(pat, body, _re2.M)
            fails.append(f"{where} does not say {want!r}"
                         + (f" -- it says {m.group(0)!r}" if m else " at all"))

    # Two records in one project, and the one path out of it. `migrate --adopt` MOVES
    # the record you are not keeping; it must then reach a CLEAN state, which the first
    # version did not: the archive it had just created was detected as a new rival, so
    # resolving one conflict manufactured a permanent one and no sequence of commands
    # could ever satisfy the tool.
    import ux_ledger as _ledger                                      # noqa: E402
    import uxconfig as _uc2                                          # noqa: E402
    with tempfile.TemporaryDirectory() as _d5:
        _r5 = Path(_d5)
        _live, _rival = _r5 / _uc2.STATE, _r5 / ".other-record"
        (_live / "contract").mkdir(parents=True)
        (_live / "design.contract.yaml").write_text("visitor_mode: read\n")
        (_live / "contract" / "lineage.yaml").write_text("- sha: aaa\n  at: x\n")
        (_live / "contract" / "aaa.yaml").write_text("visitor_mode: read\n")
        _rival.mkdir()
        (_rival / "ux.config.yaml").write_text("x: 1\n")
        if len(_uc2.state_candidates(_r5)) != 1:
            fails.append("state_candidates did not see the second record")
        # The comparison must separate a real history from a scaffold on record
        # content, not on which was written last.
        _cmp = _ledger.compare_records([_live, _rival])
        if _cmp["richest"] != _uc2.STATE:
            fails.append(f"compare_records called {_cmp['richest']} the most complete "
                         f"record, but it has no archived contract and no lineage")
        # A directory marked set aside is archived, not a rival.
        (_rival / _uc2.SET_ASIDE).write_text("# set aside\n")
        if _uc2.state_candidates(_r5):
            fails.append(f"a directory carrying {_uc2.SET_ASIDE} is still reported as a "
                         f"live record, so archiving one can never resolve a conflict")
        (_rival / _uc2.SET_ASIDE).unlink()
        if len(_uc2.state_candidates(_r5)) != 1:
            fails.append(f"removing {_uc2.SET_ASIDE} did not bring the record back, so "
                         f"the marker is not what decides it")

    # The in-page copy editor stages edits; `edits apply` writes them. Its value is
    # entirely in what it refuses, and one refusal was missing from the first version:
    # `locate` resolves on progressively shorter PREFIXES of the captured text, so the
    # anchor it matched is often not the whole string that was rewritten. Replacing a
    # prefix with the full new wording leaves the tail of the old one behind. The code
    # computed `after[:len(after)]` -- which is `after` -- behind a conditional that
    # made the case look handled.
    import ux_live                                                    # noqa: E402

    class _A:
        who = "Selftest"; why = None; dry_run = True; force = False
        what = "apply"; url = None; timeout = 1
    with tempfile.TemporaryDirectory() as _d7:
        _r7 = Path(_d7)
        (_r7 / "src").mkdir()
        (_r7 / "src" / "Hero.tsx").write_text(
            'export const Hero = () => (\n'
            '  <section>\n'
            '    <h1 className="t">Plans that scale with your team</h1>\n'
            '    <div className="offer"><h3>Boiler service</h3><p>Due Friday</p></div>\n'
            '    <p className="dup">Shared label</p>\n'
            '  </section>\n);\n')
        (_r7 / "src" / "Foot.tsx").write_text(
            'export const Foot = () => <p className="dup">Shared label</p>;\n')
        _e = _r7 / ".deuxui" / "edits"
        _e.mkdir(parents=True)
        _stage = [
            ("EDIT-001", "Plans that scale with your team", "Pricing that grows", "t"),
            ("EDIT-002", "Boiler service Due Friday", "Boiler service Monday", "offer"),
            ("EDIT-003", "Shared label", "New label", "dup"),
            ("EDIT-004", "Unchanged", "Unchanged", ""),
        ]
        for _rid, _b, _af, _cls in _stage:
            (_e / f"{_rid}.yaml").write_text(yaml.safe_dump(
                {"id": _rid, "before": _b, "after": _af, "selector": _cls,
                 "tag": "p", "classes": _cls}, sort_keys=False))
        # A batch spanning several files has to be scanned AS a batch. The first
        # version ran `check_delta` in a loop, one file per copy of the tree: each scan
        # saw a tree carrying one edit rather than the batch that would actually ship,
        # and the loop variable was overwritten so the decision record described the
        # LAST file rather than the batch it claims to summarise.
        with tempfile.TemporaryDirectory() as _db:
            _rb = Path(_db)
            (_rb / "src").mkdir()
            (_rb / "src" / "A.tsx").write_text(
                'export const A = () => <p className="a">Alpha copy here</p>;\n')
            (_rb / "src" / "B.tsx").write_text(
                'export const B = () => <p className="b">Beta copy here</p>;\n')
            _many = ux_live.check_delta_many(_rb, {
                _rb / "src" / "A.tsx":
                    'export const A = () => <p className="a">Alpha reworded</p>;\n',
                _rb / "src" / "B.tsx":
                    'export const B = () => <p className="b">Beta reworded</p>;\n'})
            if not _many.get("ran"):
                fails.append(f"check_delta_many did not run: {_many.get('why')}")
            elif _many.get("files") != 2:
                fails.append(f"check_delta_many reported {_many.get('files')} file(s) "
                             f"for a two-file batch, so a record built from it describes "
                             f"something other than what shipped")
            # A blocking finding in the FIRST file must be caught -- under the old loop
            # the last iteration's result was what survived.
            _first = ux_live.check_delta_many(_rb, {
                _rb / "src" / "A.tsx":
                    'export const A = () => <div onClick={go}>Alpha</div>;\n',
                _rb / "src" / "B.tsx":
                    'export const B = () => <p className="b">Beta reworded</p>;\n'})
            if not _first.get("blocking"):
                fails.append("check_delta_many missed a P0/P1 introduced by the FIRST "
                             "file of a batch; a per-file loop that overwrites its "
                             "result reports only the last one")
            # And `check_delta` must be the same implementation, not a second copy.
            _one = ux_live.check_delta(
                _rb, _rb / "src" / "A.tsx",
                'export const A = () => <div onClick={go}>Alpha</div>;\n')
            if _one.get("files") != 1 or not _one.get("blocking"):
                fails.append("check_delta and check_delta_many disagree; two copies of "
                             "the tree-copy-and-scan is how the batch path came to scan "
                             "a tree that never held more than one edit")

        # A prefix anchor has two causes, and naming the wrong one is a WRONG
        # explanation rather than a vague one: the text was reworded after staging, or
        # it always spanned more than one source string. In both the full run is absent
        # now, so the current file cannot tell them apart -- only what resolved AT
        # STAGING time can, which is why the edit record carries it.
        for _contig, _need in ((True, "reworded since"),
                               (False, "spans more than one source string"),
                               (None, "neither is claimed")):
            with tempfile.TemporaryDirectory() as _dp:
                _rp = Path(_dp)
                (_rp / "H.tsx").write_text(
                    'export const H = () => <b className="c">Plans that scale</b>;\n')
                _pe = _rp / ".deuxui" / "edits"
                _pe.mkdir(parents=True)
                _row = {"id": "EDIT-001", "before": "Plans that scale with your team",
                        "after": "Pricing", "selector": "b", "tag": "b", "classes": "c"}
                if _contig is not None:
                    _row["staged_contiguous"] = _contig
                (_pe / "EDIT-001.yaml").write_text(yaml.safe_dump(_row, sort_keys=False))
                _c2, _e2 = os.getcwd(), io.StringIO()
                try:
                    os.chdir(_rp)
                    with contextlib.redirect_stderr(_e2):
                        ux_live._edits_apply(_A())
                finally:
                    os.chdir(_c2)
                if _need not in _e2.getvalue():
                    fails.append(f"edits apply did not say {_need!r} for a prefix "
                                 f"anchor staged with contiguous={_contig}; naming the "
                                 f"wrong cause tells somebody their markup is split "
                                 f"when it was merely reworded")

        # Two writers over one queue resolve against the same pre-edit text and the
        # second overwrites the first. Not impeccable's lease -- one machine, one lock.
        with tempfile.TemporaryDirectory() as _dl:
            _rl = Path(_dl)
            _c3 = os.getcwd()
            try:
                os.chdir(_rl)
                _ok1, _w1 = ux_live.edits_lock(True)
                _ok2, _w2 = ux_live.edits_lock(True)
                if not _ok1:
                    fails.append("edits_lock could not take a free lock")
                if _ok2:
                    fails.append("edits_lock granted the same lock twice, so two applies "
                                 "can write over each other")
                elif "another apply holds" not in _w2:
                    fails.append("edits_lock refused without saying what holds it, so "
                                 "the only way past is deleting a file nobody explained")
                ux_live.edits_lock(False)
                if not ux_live.edits_lock(True)[0]:
                    fails.append("edits_lock did not release, so one run blocks every "
                                 "later one")
                ux_live.edits_lock(False)
            finally:
                os.chdir(_c3)

        _cwd = os.getcwd()
        _err = io.StringIO()
        try:
            os.chdir(_r7)
            with contextlib.redirect_stderr(_err):
                _rc = ux_live._edits_apply(_A())
        finally:
            os.chdir(_cwd)
        _out = _err.getvalue()
        # One clean edit applies; three refuse, each for its own stated reason.
        if "Pricing that grows" not in _out:
            fails.append("edits apply refused an edit whose text is unique in the "
                         "source and fully matched")
        for _rid, _need in (("EDIT-002", "prefix"),
                            ("EDIT-003", "no single place"),
                            ("EDIT-004", "empty or unchanged")):
            if _rid not in _out or _need not in _out:
                fails.append(f"edits apply did not refuse {_rid} with the reason "
                             f"{_need!r}; without it a copy edit lands on the wrong "
                             f"string and still looks like it worked")
        if _rc != 0:
            fails.append(f"edits apply returned {_rc} on a batch with one applicable "
                         f"edit; a batch is not all-or-nothing and a refusal on one "
                         f"must not discard the rest")

    # When an element's text is nowhere in the markup, "no anchor resolved" is true and
    # useless -- it sends somebody grepping components for a string that was never in
    # one. In a component-based app the text usually lives in data the markup reads:
    # a mapped constant, a translation catalogue, a fixture. Naming that file is the
    # difference between a dead end and a next step.
    with tempfile.TemporaryDirectory() as _d8:
        _r8 = Path(_d8)
        (_r8 / "src").mkdir()
        (_r8 / "locales").mkdir()
        (_r8 / "src" / "P.tsx").write_text(
            'export const P = () => <li className="plan">{t("plan.starter")}</li>;\n')
        (_r8 / "locales" / "en.json").write_text(
            '{ "plan.starter": "Starter plan for small teams" }\n')
        _loc = ux_live.locate({"text": "Starter plan for small teams",
                               "classes": "plan"}, _r8)
        if _loc["found"]:
            fails.append("locate claimed a source location for text that is only in a "
                         "JSON catalogue, which a copy edit would then write into "
                         "markup that does not contain it")
        if "locales/en.json" not in str(_loc.get("data") or ""):
            fails.append("locate did not name the data file the text actually lives in, "
                         "so its refusal is a dead end rather than a next step")
        # And it must NOT invent a data source for text that is genuinely absent.
        _none = ux_live.locate({"text": "No such copy anywhere at all",
                                "classes": "plan"}, _r8)
        if _none.get("data"):
            fails.append("locate reported a data source for text that is not in the "
                         "project at all")

    # comp_diff compares a build to the comp somebody approved. Every other check in
    # this skill compares an artefact to the CONTRACT, which catches a build that left
    # the system and cannot catch one that stayed inside it and is not the thing that
    # was chosen. Three real bugs lived in the first version, and all three made it
    # report confidently about something it could not see.
    import comp_diff as _cdiff                                       # noqa: E402

    # (1) contrast was read as `spec["ink_on_canvas"]["ratio"]`; comp_spec reports a
    # bare float. Every image returned None and the dimension said NOT_RUN on input it
    # could measure perfectly -- laundering, in the code that exists to prevent it.
    _same = {"canvas": "#f7f6f3", "ink": "#16181c", "ink_on_canvas": 15.8,
             "palette": [{"hex": "#f7f6f3", "coverage_pct": 80.0},
                         {"hex": "#16181c", "coverage_pct": 12.0}]}
    _g = _cdiff.ground_diff({"semantic": _same}, {"semantic": _same})
    if _g["verdict"] != "AGREES":
        fails.append(f"comp_diff.ground_diff says {_g['verdict']} comparing an image "
                     f"with itself: {_g['why']}")
    _dark = dict(_same, canvas="#0b0d10", ink="#e8eaed", ink_on_canvas=14.9)
    if _cdiff.ground_diff({"semantic": _same}, {"semantic": _dark})["verdict"] != "DIFFERS":
        fails.append("comp_diff.ground_diff did not notice the ground inverting")

    # (2) two comp colours matching the SAME built colour is a lost tonal step. It was
    # reported as two rows carrying the same built percentage, which reads as a display
    # bug rather than a finding.
    _c = {"semantic": {"palette": [{"hex": "#ffffff", "coverage_pct": 40.0},
                                   {"hex": "#f7f6f3", "coverage_pct": 35.0}]}}
    _b = {"semantic": {"palette": [{"hex": "#fdfdfd", "coverage_pct": 75.0}]}}
    _pd = _cdiff.palette_diff(_c, _b)
    if not _pd["collapsed"] or _pd["verdict"] != "DIFFERS":
        fails.append("comp_diff.palette_diff did not report two comp colours collapsing "
                     "to one in the build as a lost tonal step")

    # (3) hue is meaningless on a grey; comparing it there rejects matching greys.
    # `#808080` and `#818080` are the same grey to anyone, and OKLCH puts their hues
    # 73 degrees apart -- hue is numerically unstable as chroma approaches zero. The
    # first version of this case used two warm greys whose hues happened to agree, so
    # it passed with the grey guard deleted and proved nothing.
    if not _cdiff.near("#808080", "#818080"):
        fails.append("comp_diff.near rejected two greys that are the same colour -- "
                     "hue is unstable at zero chroma and must not decide it")
    if not _cdiff.near("#f7f6f3", "#f8f8f8"):
        fails.append("comp_diff.near rejected two near-identical off-whites")
    if _cdiff.near("#1f5eff", "#22c55e"):
        fails.append("comp_diff.near called blue and green the same colour")

    # A photographic band rebuilt as flat is the headline finding, not a rounding.
    _sp = {"regions": [{"kind": "flat"}, {"kind": "plate"}, {"kind": "flat"}]}
    _sf = {"regions": [{"kind": "flat"}, {"kind": "flat"}, {"kind": "flat"}]}
    _sd = _cdiff.structure_diff(_sp, _sf)
    if _sd["verdict"] != "DIFFERS" or "photographic" not in _sd["why"]:
        fails.append("comp_diff.structure_diff did not flag a photographic region "
                     "rebuilt as flat")

    # A WIREFRAME settles structure and nothing about colour. Deriving that from the
    # pixels was wrong -- a hatched plate placeholder has high edge density and FEW
    # colours, so comp_spec calls it `mixed`, and an exclusion keyed on `plate` skipped
    # the one band it existed for. The rendered sheet says so itself.
    with tempfile.TemporaryDirectory() as _d6:
        _r6 = Path(_d6)
        _wf = _r6 / "a.svg"
        _wf.write_text('<svg xmlns="http://www.w3.org/2000/svg"><desc>'
                       + _cdiff.WIREFRAME_MARK + ' rendered</desc></svg>\n')
        if not _cdiff.is_wireframe(_wf):
            fails.append("comp_diff.is_wireframe missed the marker ux_image.py writes "
                         "into every rendered sheet")
        _plain = _r6 / "b.svg"
        _plain.write_text('<svg xmlns="http://www.w3.org/2000/svg"><desc>a photograph'
                          '</desc></svg>\n')
        if _cdiff.is_wireframe(_plain):
            fails.append("comp_diff.is_wireframe called a finished comp a wireframe, "
                         "which would stand down the colour comparison silently")

    # And the marker has to actually be in what ux_image renders, or the detection above
    # is testing a string nothing writes.
    import ux_image as _uxi                                          # noqa: E402
    if _cdiff.WIREFRAME_MARK not in (HERE / "ux_image.py").read_text():
        fails.append(f"ux_image.py does not write {_cdiff.WIREFRAME_MARK!r}, so "
                     f"comp_diff can never recognise a rendered wireframe")

    # The CSP scanner. What it gets wrong is not "misses a policy" -- it is reading a
    # policy and reporting the WRONG verdict, which sends somebody to loosen a config
    # that was never the problem, or tells them nothing is wrong when the overlay
    # cannot work. Two real bugs lived here: the value pattern excluded single quotes,
    # so every CSP value came back as `' '` (a CSP value is almost entirely
    # single-quoted keywords); and directives were scanned FORWARD from the header
    # mention, while the commonest shape in the wild defines the policy in a template
    # literal above the `headers()` call that sets it.
    import csp as _csp                                               # noqa: E402
    _NEXT = """const csp = `
  default-src 'self';
  script-src 'self' 'nonce-abc';
  style-src 'self'%s;
`;
export default { async headers() { return [{ source: "/(.*)",
  headers: [{ key: "Content-Security-Policy", value: csp }] }]; } };
"""
    _csp_cases = [
        ("", False, "style-src 'self' forbids inline style"),
        (" 'unsafe-inline'", True, "'unsafe-inline' permits it"),
        # A nonce or hash beside 'unsafe-inline' makes browsers IGNORE the keyword.
        (" 'unsafe-inline' 'nonce-xyz'", False,
         "a nonce beside 'unsafe-inline' voids it"),
    ]
    for _extra, _want, _why in _csp_cases:
        with tempfile.TemporaryDirectory() as _d3:
            _r3 = Path(_d3)
            (_r3 / "next.config.mjs").write_text(_NEXT % _extra)
            _res = _csp.scan(_r3)
            if not _res["any"]:
                fails.append(f"csp.scan found no policy in a next.config.mjs that "
                             f"declares one ({_why})")
                continue
            _got = _res["policies"][0]["style_inline_allowed"]
            if _got is not _want:
                fails.append(f"csp.scan says style_inline_allowed={_got}, wanted "
                             f"{_want}: {_why}")
            if not _res["policies"][0]["directives"].get("style-src"):
                fails.append(f"csp.scan read the policy but captured no style-src "
                             f"value ({_why})")
    with tempfile.TemporaryDirectory() as _d4:
        _r4 = Path(_d4)
        (_r4 / "src").mkdir()
        (_r4 / "src" / "App.tsx").write_text("export default () => <div>hi</div>;\n")
        if _csp.scan(_r4)["any"]:
            fails.append("csp.scan invented a policy in a project that declares none")

    # A record of ours under a name this version does not use has to be FOUND, and
    # found by its contents. The first version of this check hardcoded the one name the
    # skill used before it was renamed, which identified a record by the least reliable
    # thing about it: it saw exactly one spelling, missed a directory somebody had
    # copied or renamed by hand, and left a dead string in the source describing a
    # decision nobody could act on. These cases pin the behaviour that replaced it --
    # including the two refusals, because a migration that guesses which of two
    # histories is real destroys one of them.
    import uxconfig as _uc2                                          # noqa: E402
    with tempfile.TemporaryDirectory() as _d:
        _r = Path(_d)
        # This case used to create a directory under the skill's own pre-rename name and
        # assert that it was found. That was the right test of the OLD design, which
        # matched one hardcoded name, and it is redundant against this one: the detector
        # reads contents and never looks at the name, so a directory called `.anything`
        # exercises exactly the same code path. Keeping the old name here proved nothing
        # the case below does not, while leaving the one string in the tree that the
        # rename was supposed to remove. Two arbitrary names, neither of them ours:
        (_r / ".some-old-dir").mkdir()
        (_r / ".some-old-dir" / "ux.config.yaml").write_text("x: 1\n")
        if _uc2.legacy_state(_r) is None:
            fails.append("legacy_state missed a state directory identified by its "
                         "contents")
        # Asserted against `legacy_state`, not only `state_candidates`: the first
        # version of this case checked the candidate LIST, which reads contents either
        # way, so it passed with `legacy_state` reverted to a hardcoded name -- the
        # exact design it is here to rule out.
        with tempfile.TemporaryDirectory() as _d2:
            _r2 = Path(_d2)
            (_r2 / ".hand-copied-ux").mkdir()
            (_r2 / ".hand-copied-ux" / "phase.yaml").write_text("phase: build\n")
            _got = _uc2.legacy_state(_r2)
            if _got is None or _got.name != ".hand-copied-ux":
                fails.append("legacy_state did not find a record under an arbitrary "
                             "directory name, which is the whole reason it reads "
                             "contents instead of a remembered name")
        (_r / ".hand-copied-ux").mkdir()
        (_r / ".hand-copied-ux" / "phase.yaml").write_text("phase: build\n")
        if len(_uc2.state_candidates(_r)) != 2:
            fails.append("state_candidates did not list both records")
        # A hidden directory that is NOT ours must never be a candidate.
        (_r / ".github").mkdir()
        (_r / ".github" / "workflows.yml").write_text("name: ci\n")
        if any(q.name == ".github" for q in _uc2.state_candidates(_r)):
            fails.append("state_candidates claimed .github/ as a record of ours")
        # Once STATE exists, nothing is invisible, so legacy_state must stay quiet --
        # the conflict is doctor's row, not a missing history.
        (_r / _uc2.STATE).mkdir()
        (_r / _uc2.STATE / "ux.config.yaml").write_text("x: 1\n")
        if _uc2.legacy_state(_r) is not None:
            fails.append("legacy_state reports a missing history while STATE is live, "
                         "which would send a migration at a directory already in use")
        if len(_uc2.state_candidates(_r)) != 2:
            fails.append("state_candidates stopped listing rivals once STATE existed, "
                         "so a second record beside the live one goes unreported")

    # `ux_live.py text` rewrites visible copy in the source. Its whole value is in
    # what it REFUSES, and one of its two safety features was very nearly dead code:
    # `coupled()` searched the same file set as `locate()`, which had already proved
    # the string appears exactly once there -- so it could never report anything, and
    # a translation catalogue keyed on the English string would go unmentioned.
    import ux_live                                                   # noqa: E402
    if ux_live.COUPLED_EXT & ux_live.SRC_EXT:
        fails.append("ux_live.COUPLED_EXT overlaps SRC_EXT, so coupled() re-searches "
                     "files locate() already proved unique -- it can only report noise")
    if not (ux_live.COUPLED_EXT & {".json", ".yaml"}):
        fails.append("ux_live.COUPLED_EXT does not cover .json/.yaml, where an i18n "
                     "catalogue keyed on the visible English string lives -- the most "
                     "common coupling there is")
    with tempfile.TemporaryDirectory() as _d:
        _r = Path(_d)
        (_r / "Page.tsx").write_text('<h1>Plans that scale</h1>\n')
        (_r / "en.json").write_text('{"Plans that scale": "Plans that scale"}\n')
        (_r / "notes.md").write_text("nothing relevant here\n")
        hits = ux_live.coupled(_r, "Plans that scale", _r / "Page.tsx")
        if not any(h["file"] == "en.json" for h in hits):
            fails.append("coupled() missed a lookup key in en.json")
        if not any(h["key_like"] for h in hits):
            fails.append("coupled() found the occurrence but did not mark it key-like, "
                         "which is the part that tells a reader it will now miss")
        if any(h["file"] == "Page.tsx" for h in hits):
            fails.append("coupled() reported the file being edited as a coupling")
        if ux_live.coupled(_r, "no such string anywhere", _r / "Page.tsx"):
            fails.append("coupled() reports hits for a string that is not present")

    # cdp.connect_page returns (ws, info-or-reason). Two call sites in ux_live.py
    # bound it to ONE name, so `ws` was the tuple: always truthy, so the
    # "no page is open" guard never fired, and `ws.call` raised AttributeError one
    # line later. `ux_live.py show` could not work at all, in any project, and the
    # symptom was a traceback rather than the guard's own message.
    #
    # Nothing in the check corpus can see this -- it is this tool's own code, not a
    # project's -- so it is asserted here, over every caller, by shape.
    import ast as _ast
    for q in sorted(HERE.glob("*.py")):
        try:
            tree = _ast.parse(q.read_text())
        except SyntaxError as e:
            fails.append(f"{q.name} does not parse: {e}")
            continue
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Assign):
                continue
            call = node.value
            if not isinstance(call, _ast.Call):
                continue
            fn = call.func
            nm = (fn.attr if isinstance(fn, _ast.Attribute) else
                  getattr(fn, "id", None))
            if nm != "connect_page":
                continue
            tgt = node.targets[0]
            if not isinstance(tgt, _ast.Tuple) or len(tgt.elts) != 2:
                fails.append(
                    f"{q.name}:{node.lineno} binds connect_page() to a single name. "
                    f"It returns (ws, info-or-reason), so that name is a tuple: the "
                    f"None guard cannot fire and the next .call() raises")

    # ux_check.py duplicates the extension set in HOOK_EXT so the PostToolUse
    # fast path can bail before importing yaml and the check modules. If the two
    # drift, the hook silently stops seeing a whole file type.
    import ux_check
    from checks._util import NATIVE_EXT, SOURCE_EXT, STYLE_EXT
    drift = ux_check.HOOK_EXT ^ (SOURCE_EXT | STYLE_EXT | NATIVE_EXT)
    if drift:
        fails.append("HOOK_EXT has drifted from SOURCE_EXT|STYLE_EXT|NATIVE_EXT: "
                     f"{sorted(drift)}")

    # S-CONTRACT-RAMP measured against a ramp, both directions, on its own subject.
    # The corpus can only show it firing: the good fixtures contain no raw colour at
    # all (S-TOKEN-HEX would fire if they did), so "silent on good" there proves the
    # check had nothing to look at rather than that it can pass. One colour ON the
    # ramp and one OFF it, in the same project, is the control that distinguishes a
    # working check from one that reports everything -- or nothing.
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / ".deuxui").mkdir(parents=True)
        (proj / ".deuxui" / "design.contract.yaml").write_text(
            "color:\n  ramp_steps: [0.985, 0.922, 0.715, 0.574, 0.371, 0.209]\n")
        (proj / "theme.css").write_text(":root { --x: 1 }\n")
        (proj / "on.css").write_text(".a { color: #e5e5e3 }\n")     # L 0.9213
        (proj / "off.css").write_text(".b { color: #9a9a98 }\n")    # L 0.6856
        hits = _scan(proj, extra=("--detector", "S-CONTRACT-RAMP")).get("findings", [])
        files = {Path(h["file"]).name for h in hits}
        if "off.css" not in files:
            fails.append("S-CONTRACT-RAMP did not fire on a colour off the declared "
                         "ramp, so the ramp is declared and never measured")
        if "on.css" in files:
            fails.append("S-CONTRACT-RAMP fired on a colour ON the declared ramp, so "
                         "it reports conformance as a violation")

    # DeuxUI's own surfaces, measured against DeuxUI's own contract, with the same
    # detectors it points at everybody else. A tool that asks every project to declare
    # its system before building, and then themes its own pages from hardcoded hex, has
    # an argument it does not believe -- and it did: this found 12 findings on the
    # review page, including three literal warm greys in the dark block, two font sizes
    # off the ladder, four repeated family literals and two colours off the ramp.
    #
    # It also found two defects in the DETECTORS, which is the part worth keeping the
    # test for: S-CONTRACT-FONT-AVAIL read a declared stack as one opaque face name, so
    # `ui-sans-serif, system-ui, sans-serif` was reported as a missing typeface; and the
    # composed dark theme was mixed rather than taken off the declared ramp.
    brand = HERE.parent / "assets" / "brand" / "brand.contract.yaml"
    if brand.exists():
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            (proj / ".deuxui").mkdir()
            shutil.copy(brand, proj / ".deuxui" / "design.contract.yaml")
            here = Path.cwd()
            try:
                os.chdir(proj)
                sys.path.insert(0, str(HERE))
                import ux_review
                for n in ("a", "b"):
                    (proj / f"{n}.html").write_text(
                        "<!doctype html><html lang=en><title>x</title>"
                        "<body><main><h1>x</h1></main>")
                rv = ux_review.Review(
                    {"one": {"kind": "file", "target": str(proj / "a.html")},
                     "two": {"kind": "file", "target": str(proj / "b.html")}},
                    "Which layout carries the total?", "checkout")
                (proj / "review.html").write_text(ux_review.page(rv, ux_review.theme()))
            finally:
                os.chdir(here)
            hits = _scan(proj / "review.html").get("findings", [])
            own = [h for h in hits if str(h.get("detector", "")).startswith(
                ("S-CONTRACT-", "S-TOKEN-", "S-CONTRAST-", "S-SLOP-"))]
            for h in own:
                fails.append(f"deuxui's own review page violates deuxui's own contract: "
                             f"{h.get('detector')} at line {h.get('line')} "
                             f"({str(h.get('snippet'))[:40]})")

    # ux_live's accept gate. The bug this is here for: it graded blocking findings by
    # reading `finding["severity"]`, and a finding has no severity -- severity is a
    # property of the RULE, in the registry. So `blocking` was empty every time and the
    # gate accepted a variant putting grey on white at 1.98:1. A check that cannot fail
    # is not a check, which is this skill's own first sentence.
    import ux_live
    sev = ux_live.severity_of()
    if not sev:
        fails.append("ux_live.severity_of() is empty, so nothing can be graded "
                     "blocking and every variant would be accepted")
    for det, want in (("S-CONTRAST-PAIR", ("P0", "P1")), ("S-CONTRACT-COLOR", ("P0", "P1"))):
        if sev.get(det) not in want:
            fails.append(f"ux_live grades {det} as {sev.get(det)!r}, so a variant that "
                         f"introduces it would not be refused")

    # A variant may only propose declared values, and source must resolve to exactly
    # one place or refuse. Both directions on each, in a project laid out like a real
    # one -- an accept that writes to the wrong file still looks like success.
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / ".deuxui").mkdir()
        (proj / "src").mkdir()
        (proj / ".deuxui" / "design.contract.yaml").write_text(
            "visitor_mode: operate\nworld: Warm paper, one serif voice, ink text.\n"
            "type: {families: {display: Inter, body: Inter, mono: null},"
            " scale_px: [12, 14, 16, 20, 26]}\n"
            "color: {roles: {canvas: '#fbf9f4', surface: '#ffffff', ink: '#16181d',"
            " muted: '#6b7280', interactive: '#1b5fd9'}}\n"
            "depth: {metaphor: border, elevations: ['1px solid #e7e2d8']}\n"
            "spacing: {base_px: 4, scale: [4, 8, 12, 16, 24]}\n"
            "radius: {control_px: 8, card_px: 20}\n")
        (proj / "src" / "Card.tsx").write_text(
            'export const Card = () => (\n  <article className="job-card">\n'
            '    <h3>Boiler service at 14 Mill Lane</h3>\n  </article>\n);\n')
        rec = {"selector": "article.job-card", "classes": "job-card",
               "text": "Boiler service at 14 Mill Lane",
               "computed": {"fontSize": "16px", "padding": "8px"}}
        here = Path.cwd()
        try:
            os.chdir(proj)
            import ux_image
            import uxconfig as _cfg
            loc = ux_live.locate(rec, proj)
            if not loc.get("found"):
                fails.append("ux_live.locate could not place an element that appears "
                             "exactly once in the source")
            shutil.copy(proj / "src" / "Card.tsx", proj / "src" / "Card2.tsx")
            dup = ux_live.locate(rec, proj)
            if dup.get("found"):
                fails.append(f"ux_live.locate picked one of two identical matches "
                             f"({dup.get('file')}) instead of refusing -- writing to "
                             f"the wrong file still looks like success")
            (proj / "src" / "Card2.tsx").unlink()

            c = ux_image.Contract(_cfg.contract(proj))
            variants = ux_live.build_variants(rec, c, 4, None)
            if len(variants) < 3:
                fails.append(f"ux_live generated {len(variants)} variants, expected 3+")
            declared = {str(v) for v in (c.roles or {}).values()}
            declared |= {f"{s:g}px" for s in c.scale}
            declared |= {f"{c.r_card:g}px", f"{c.r_control:g}px"}
            for s in (c.raw.get("spacing") or {}).get("scale") or []:
                declared.add(f"{float(s):g}px")
            for v in variants:
                for prop, val in v["declarations"].items():
                    val = str(val)
                    if val.startswith("var(") or prop in ("line-height", "box-shadow",
                                                          "border"):
                        continue
                    if val not in declared:
                        fails.append(f"ux_live variant {v['id']} proposes "
                                     f"{prop}: {val} which the contract does not "
                                     f"declare -- the generator is a route out of the "
                                     f"system it is supposed to hold")
        finally:
            os.chdir(here)

    # R-FOCUS-WALK's reading-order rule, in isolation. The probe runs in a browser,
    # so the corpus cannot reach it; the arithmetic is what was wrong. `top` alone
    # read an ordinary column-major footer as scrambled, and the count tracked the
    # grid's column count (1 at 320px, 5 at 1024px) rather than anything about order.
    js = (HERE / "checks" / "browser" / "focus.js").read_text()
    if "ROW_BAND" not in js or "b.left < a.left" not in js:
        fails.append("focus.js no longer compares horizontal position, so a "
                     "multi-column row reads as scrambled focus order")
    if "pos === 'fixed'" not in js:
        fails.append("focus.js no longer excludes fixed/sticky elements, so scrollY "
                     "is added to an element that has no document position")
    if shutil.which("node"):
        probe = """
          const ROW_BAND=24;
          const walk=o=>{let b=0;for(let i=1;i<o.length;i++){const a=o[i-1],c=o[i];
            const same=Math.abs(c.top-a.top)<=ROW_BAND;
            if(same?c.left<a.left-ROW_BAND:c.top<a.top-ROW_BAND)b++;}return b;};
          const row=[];for(let c=0;c<6;c++)row.push({top:900,left:100+c*120});
          console.log(JSON.stringify({
            ordered_row: walk(row),
            scrambled_row: walk([{top:900,left:700},{top:900,left:100}]),
            jump_up: walk([{top:900,left:0},{top:200,left:0}]),
            normal_column: walk([{top:100,left:0},{top:200,left:0},{top:300,left:0}])}));
        """
        r = subprocess.run(["node", "-e", probe], capture_output=True, text=True)
        try:
            v = json.loads(r.stdout)
        except ValueError:
            fails.append("could not evaluate the focus-order rule")
        else:
            if v["ordered_row"] or v["normal_column"]:
                fails.append(f"the focus-order rule reports a backjump in correct "
                             f"order ({v}) -- a multi-column row is not scrambled")
            if not v["scrambled_row"] or not v["jump_up"]:
                fails.append(f"the focus-order rule misses a real backjump ({v})")

    # The forced-state probes must not return a verdict about a condition that was
    # never established. On a server-rendered route there is no client request to
    # intercept, the page renders normally, and every clause of _state then reads
    # that ordinary page as a defect. Four directions, because the dangerous failure
    # is an inert route MASKING a real one in the same run.
    import ux_report
    page = {"probe": "state", "visible_text_length": 900, "mentions_failure": False,
            "mentions_empty": False, "recovery_actions": [], "visible_spinners": 0}
    fn = ux_report._state("abort", "An aborted request", None)
    cases = {
        "server-rendered route": ({
            "_root__apiseen.json": {"probe": "apiseen", "api_seen": False},
            "_root__state_abort.json": dict(page)}, "NOT_RUN"),
        "client fetch, unhandled": ({
            "_jobs__apiseen.json": {"probe": "apiseen", "api_seen": True},
            "_jobs__state_abort.json": dict(page)}, "FAIL"),
        "client fetch, handled": ({
            "_jobs__apiseen.json": {"probe": "apiseen", "api_seen": True},
            "_jobs__state_abort.json": {**page, "mentions_failure": True,
                                        "recovery_actions": ["Try again"]}}, "PASS"),
        "inert route beside a real one": ({
            "_root__apiseen.json": {"probe": "apiseen", "api_seen": False},
            "_root__state_abort.json": dict(page),
            "_jobs__apiseen.json": {"probe": "apiseen", "api_seen": True},
            "_jobs__state_abort.json": dict(page)}, "FAIL"),
    }
    for what, (raws, want) in cases.items():
        got = fn(raws, {})[0]
        if got != want:
            fails.append(f"forced-state verdict for {what} is {got}, expected {want}")

    # A comment must never decide a verdict, and the set-level corpus test cannot
    # see this: S-COMMIT-REVIEW also fires on the P0 fixture, so "it fired somewhere"
    # stays true while this specific case goes silent. Asserted per FILE, both ways.
    # Its own project directory, because the evidence window is 2,000 characters and
    # an unrelated "Confirm" in a neighbouring fixture decides the outcome otherwise.
    for which, want in (("bad", True), ("good", False)):
        src = FIX / f"{which}-peer.tsx"
        if not src.exists():
            continue
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            shutil.copy(FIX / "package.json", proj / "package.json")
            shutil.copy(src, proj / "checkout-commit.tsx")
            hits = _scan(proj, extra=("--detector", "S-COMMIT-REVIEW")).get("findings", [])
            if want and not hits:
                fails.append("S-COMMIT-REVIEW stayed silent on a commitment whose only "
                             "review step is in a comment -- a comment is never shown "
                             "to anyone, so it cannot be the review")
            if not want and hits:
                fails.append("S-COMMIT-REVIEW fired on a commitment that shows a real "
                             "review step in the interface")

    # The ledger's own commands, on a real project laid out the way one is. Only a
    # smoke test -- but `state` reads six surfaces and `show` resolves an archive, so
    # a broken one of those is a traceback rather than a wrong number, and nothing
    # else in this file would have caught it.
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / ".deuxui").mkdir()
        (proj / ".deuxui" / "design.contract.yaml").write_text(
            "visitor_mode: read\nworld: One grotesque voice on cool grey.\n"
            "depth: {metaphor: border}\nradius: {card_px: 12}\n")
        for cmd in (("snapshot",), ("state", "--json"), ("log", "--json"),
                    ("diff",), ("check", "--json"), ("show", "nope")):
            r = subprocess.run([sys.executable, str(HERE / "ux_ledger.py"), *cmd],
                               capture_output=True, text=True, cwd=proj)
            # `diff` with one version and `show` of a missing id refuse with 2; a
            # traceback is what this is looking for.
            if "Traceback" in r.stderr:
                fails.append(f"ux_ledger.py {' '.join(cmd)} raised: "
                             f"{r.stderr.strip().splitlines()[-1]}")
        r = subprocess.run([sys.executable, str(HERE / "ux_ledger.py"), "state", "--json"],
                           capture_output=True, text=True, cwd=proj)
        try:
            st = json.loads(r.stdout)
        except ValueError:
            fails.append("ux_ledger.py state --json did not emit JSON")
        else:
            if not st.get("declaration", {}).get("archived"):
                fails.append("ux_ledger.py snapshot ran and state still reports the "
                             "contract as unarchived")
            if len(st.get("briefs") or []) != 2:
                fails.append("ux_ledger.py state does not report both prose briefs")

    # A contract's identity is what binds a decision to what it approved. Two ways
    # it can silently stop working, both of which shipped: the hash including the
    # file's absolute path (so it changed when the project moved), and the ledger
    # hashing the raw file while every decision hashed the cleaned subset (so no
    # approval ever resolved). Negative control included: two DIFFERENT contracts
    # must not hash the same, or a hash that ignored its input would pass the rest.
    import ux_image, uxconfig
    body = ("visitor_mode: operate\nworld: Warm paper, one serif voice.\n"
            "type: {families: {display: Georgia, body: Inter, mono: null}, "
            "scale_px: [12, 16, 24]}\ncolor: {roles: {canvas: '#fff', ink: '#111'}}\n"
            "depth: {metaphor: border}\nradius: {card_px: 14}\n")
    shas = []
    for sub in ("one", "two/deeper"):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / sub / ".deuxui"
            d.mkdir(parents=True)
            (d / "design.contract.yaml").write_text(body)
            shas.append(ux_image.Contract(
                uxconfig.contract(d.parent)).sha())
    if len(set(shas)) != 1:
        fails.append(f"Contract.sha() depends on where the file lives ({shas}), so a "
                     f"decision recorded on one machine cannot be resolved on another")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / ".deuxui"
        d.mkdir(parents=True)
        (d / "design.contract.yaml").write_text(body)
        loader = ux_image.Contract(uxconfig.contract(d.parent)).sha()
        import ux_ledger
        ledger = ux_ledger.sha_of(yaml.safe_load(body))
        if loader != ledger:
            fails.append(f"the ledger hashes a contract differently from the loader "
                         f"({ledger} vs {loader}), so every recorded approval would "
                         f"report as unresolvable")
        other = ux_ledger.sha_of(yaml.safe_load(
            body.replace("card_px: 14", "card_px: 4")))
        if other == ledger:
            fails.append("two different contracts hash the same, so a version change "
                         "would not be recorded as one")

    # Tokens gate the whole colour family: every check that resolves a colour is
    # `requires=lambda p: bool(p.cssvars)`, so a token collector that returns
    # nothing switches those checks OFF rather than failing them. Both directions,
    # because a collector that returned the entire stylesheet would satisfy the
    # positive case alone and quietly treat every `--x:` anywhere as a theme token.
    from checks._util import theme_blocks, collect_css_vars
    one_line = "@theme { --color-canvas: #fbf9f4; --color-ink: #16181d; }"
    if "--color-ink" not in "".join(theme_blocks(one_line)):
        fails.append("theme_blocks misses a single-line @theme block, which silently "
                     "disables every colour check")
    nested = "@theme {\n  --color-a: 1;\n  @keyframes spin { to { opacity: 1 } }\n}"
    if "--color-a" not in "".join(theme_blocks(nested)):
        fails.append("theme_blocks misses an @theme block containing @keyframes")
    if theme_blocks(":root { --color-ink: #000; }\n.x { --y: 1; }"):
        fails.append("theme_blocks returned a block from a file with no @theme")
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / "app.css").write_text(one_line)
        if "--color-ink" not in collect_css_vars(r):
            fails.append("collect_css_vars found no tokens in a single-line @theme "
                         "project, so the colour checks would not have run")
        (r / "app.css").write_text("/* no theme here */\n.a { color: red }")
        if collect_css_vars(r):
            fails.append("collect_css_vars invented tokens in a project with none")

    # A single-file scan must never report a rule as PASS.
    reg, det = ux_check.load_rules()
    status = {d: ("PASS", "1 files examined") for d in list(det["detectors"])[:20]}
    rolled = ux_check.rollup(reg, det["detectors"], status, single_file=True)
    if any(v[0] == "PASS" for v in rolled.values()):
        fails.append("rollup(single_file=True) emitted PASS")

    for f in fails:
        print(f"  FAIL {f}")
    return fails


GROUPS = {"contract": "contract invariants", "config": "config wiring",
          "bytecode": "shipped bytecode", "csp": "overlay vs page CSP",
          "capabilities": "capabilities", "spans": "element spans",
          "corpus": "the known-bad and known-good fixtures"}

NOT_RUN = "NOT RUN"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", action="append", choices=sorted(GROUPS),
                    help="run only this group; repeatable. Everything else reports "
                         "NOT RUN, which is not a pass")
    ap.add_argument("--list", action="store_true", help="the group names, and exit")
    a = ap.parse_args(argv)
    if a.list:
        for k, v in sorted(GROUPS.items()):
            print(f"  {k:<14} {v}")
        return 0
    want = set(a.group or GROUPS)

    # A skipped group is NOT_RUN, never an empty pass. Same rule this whole skill is
    # built on, applied to its own test runner: `--group spans` must not print a report
    # that reads as though the other six had been checked and found clean.
    def maybe(key, fn):
        return fn() if key in want else NOT_RUN

    contract = maybe("contract", contract_checks)
    wiring = maybe("config", config_wiring)
    bytecode = maybe("bytecode", no_shipped_bytecode)
    overlay = maybe("csp", overlay_policy)
    caps = maybe("capabilities", capabilities)
    spans = maybe("spans", element_spans)
    if "corpus" in want:
        with tempfile.TemporaryDirectory() as d:
            bad = run(Path(tempfile.mkdtemp(dir=d)), "bad")
        with tempfile.TemporaryDirectory() as d:
            good = run(Path(tempfile.mkdtemp(dir=d)), "good")
    else:
        bad, good = set(EXPECT), set()

    missed = [d for d in EXPECT if d not in bad]
    leaked = sorted(good)
    for d in EXPECT:
        mark = "ok  " if d in bad and d not in good else "FAIL"
        if mark == "FAIL":
            why = "silent on bad" if d not in bad else "fires on good"
            print(f"  {mark} {d:<22} {why}")
    def say(label, got, clean="all ok"):
        if got == NOT_RUN:
            return f"{label:<21}{NOT_RUN}"
        return f"{label:<21}{clean if not got else str(len(got)) + ' FAILING'}"

    if "corpus" in want:
        print(f"\nfired on bad:  {len(bad)}")
        print(f"expected but silent: {missed or 'none'}")
        print(f"false positives on good: {leaked or 'none'}")
    else:
        print(f"\nthe known-bad and known-good fixtures: {NOT_RUN}")
    print(say("contract invariants:", contract))
    print(say("config wiring:", wiring))
    print(say("shipped bytecode:", bytecode, clean="none"))
    print(say("overlay vs page CSP:", overlay))
    print(say("element spans:", spans))
    print(say("capabilities:", caps))
    ran = [g for g in (contract, wiring, bytecode, overlay, spans, caps)
           if g != NOT_RUN]
    ok = (not missed and not leaked and not any(ran))
    skipped = sorted(set(GROUPS) - want)
    # Not PASS. Every other part of this skill refuses to let an unrun check round up
    # to a passing one, and its own runner does not get an exemption.
    verdict = "FAIL" if not ok else ("PARTIAL" if skipped else "PASS")
    tail = f" -- {len(skipped)} group(s) NOT RUN: {', '.join(skipped)}" if skipped else ""
    print(f"\nSELFTEST {verdict}{tail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
