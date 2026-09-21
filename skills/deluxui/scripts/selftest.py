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
    # P0 family
    "S-PRIVACY-URL", "S-SECRET-LOG", "S-PASSWORD-HANDLING", "S-PERM-ONMOUNT",
    "S-DARK-PATTERN", "S-FAKE-STATS", "S-STATE-PREMATURE", "S-DRAFT-BOUNDARY",
    "S-RETRY-SAFETY", "S-COMMIT-DISCLOSURE", "S-COMMIT-REVIEW", "S-AI-PROVENANCE",
    # reading quality + visual craft
    "S-TYPE-TINY", "S-TYPE-LEADING", "S-TYPE-ALLCAPS", "S-TYPE-JUSTIFY",
    "S-TYPE-TRACKING-WIDE", "S-TYPE-CRAMPED", "S-SLOP-EYEBROW",
    "S-CRAFT-DEPTH", "S-CRAFT-TYPESYSTEM", "S-CRAFT-DECOR", "S-CRAFT-PALETTE-WARM",
    "S-CRAFT-MOTION", "S-CRAFT-RHYTHM", "S-CRAFT-VOICE",
]


def run(tmp: Path, which: str) -> set[str]:
    for name in ("package.json", "theme.css"):
        shutil.copy(FIX / name, tmp / name)
    for suf in (".tsx", ".css"):
        shutil.copy(FIX / f"{which}{suf}", tmp / f"sample{suf}")
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
        cfgdir = proj / ".deluxui"; cfgdir.mkdir()
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
    from checks._util import SOURCE_EXT, STYLE_EXT
    drift = ux_check.HOOK_EXT ^ (SOURCE_EXT | STYLE_EXT)
    if drift:
        fails.append(f"HOOK_EXT has drifted from SOURCE_EXT|STYLE_EXT: {sorted(drift)}")

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
