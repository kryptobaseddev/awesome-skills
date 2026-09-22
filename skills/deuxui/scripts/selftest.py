#!/usr/bin/env python3
"""Prove each static check fires on known-bad source and stays quiet on good.

A check that cannot fail its own negative case is not a check, it is a comment.
Run this before trusting any report.
"""
from __future__ import annotations
import shutil, subprocess, sys, tempfile, json
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


def contract_checks():
    """Invariants the check corpus cannot catch on its own."""
    fails = []

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


def main():
    contract = contract_checks()
    wiring = config_wiring()
    bytecode = no_shipped_bytecode()
    with tempfile.TemporaryDirectory() as d:
        bad = run(Path(tempfile.mkdtemp(dir=d)), "bad")
    with tempfile.TemporaryDirectory() as d:
        good = run(Path(tempfile.mkdtemp(dir=d)), "good")

    missed = [d for d in EXPECT if d not in bad]
    leaked = sorted(good)
    for d in EXPECT:
        mark = "ok  " if d in bad and d not in good else "FAIL"
        if mark == "FAIL":
            why = "silent on bad" if d not in bad else "fires on good"
            print(f"  {mark} {d:<22} {why}")
    print(f"\nfired on bad:  {len(bad)}")
    print(f"expected but silent: {missed or 'none'}")
    print(f"false positives on good: {leaked or 'none'}")
    print(f"contract invariants: {'all ok' if not contract else str(len(contract)) + ' FAILING'}")
    print(f"config wiring:       {'all ok' if not wiring else str(len(wiring)) + ' FAILING'}")
    print(f"shipped bytecode:    {'none' if not bytecode else str(len(bytecode)) + ' FOUND'}")
    ok = not missed and not leaked and not contract and not wiring and not bytecode
    print("\nSELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
