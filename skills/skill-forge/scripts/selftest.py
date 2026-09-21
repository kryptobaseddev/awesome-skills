#!/usr/bin/env python3
"""Prove forge_check fires on a broken skill and stays quiet on a sound one.

The repo-wide generated-files check is environmental rather than a property of
the skill under test, so it is excluded here.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
ENVIRONMENTAL = {"generated files"}

MUST_FAIL_ON_BAD = {"progressive disclosure", "category"}
MUST_WARN_ON_BAD = {"description trigger", "description boundary", "evals"}


def check(path: Path) -> dict[str, str]:
    r = subprocess.run([sys.executable, str(HERE / "forge_check.py"), str(path), "--json"],
                       capture_output=True, text=True)
    data = json.loads(r.stdout)
    return {row["check"]: row["level"] for row in data["rows"]
            if row["check"] not in ENVIRONMENTAL}


def main() -> int:
    bad, good = check(FIX / "bad-skill"), check(FIX / "good-skill")
    problems = []

    for c in sorted(MUST_FAIL_ON_BAD):
        got = bad.get(c)
        print(f"  {'ok  ' if got == 'FAIL' else 'FAIL'} bad-skill  {c:<26} -> {got}")
        if got != "FAIL":
            problems.append(f"{c} did not fail on the bad fixture (got {got})")
    for c in sorted(MUST_WARN_ON_BAD):
        got = bad.get(c)
        print(f"  {'ok  ' if got in ('warn', 'FAIL') else 'FAIL'} bad-skill  {c:<26} -> {got}")
        if got not in ("warn", "FAIL"):
            problems.append(f"{c} was silent on the bad fixture (got {got})")

    noisy = sorted(c for c, lvl in good.items() if lvl != "ok")
    print(f"\n  {'ok  ' if not noisy else 'FAIL'} good-skill non-ok rows -> {noisy or 'none'}")
    if noisy:
        problems.append(f"fired on the good fixture: {', '.join(noisy)}")

    print()
    for p in problems:
        print(f"  problem: {p}")
    print("SELFTEST", "PASS" if not problems else "FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
