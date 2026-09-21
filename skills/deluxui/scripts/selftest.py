#!/usr/bin/env python3
"""Prove each static check fires on known-bad source and stays quiet on good.

A check that cannot fail its own negative case is not a check, it is a comment.
Run this before trusting any report.
"""
from __future__ import annotations
import shutil, subprocess, sys, tempfile, json
from pathlib import Path

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
    "S-CANVAS-A11Y", "S-3D-PERF", "S-MEDIA-CAPTIONS",
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
                        (f"{which}-craft.css", "landing.css")):
        src = FIX / extra
        if src.exists():
            shutil.copy(src, tmp / dest)
    out = subprocess.run([sys.executable, str(HERE / "ux_check.py"), str(tmp), "--json"],
                         capture_output=True, text=True)
    data = json.loads(out.stdout)
    return {f["detector"] for f in data["findings"]}


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
    ok = not missed and not leaked and not contract
    print("\nSELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
