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


def scaffold_roundtrip(problems: list[str]) -> None:
    """A scaffolder that emits something the gate rejects is worse than none.
    Create a throwaway skill, gate it, remove it -- whatever happens."""
    import shutil
    root = HERE.parents[2]
    name = "forge-selftest-tmp"
    dest = root / "skills" / name
    shutil.rmtree(dest, ignore_errors=True)
    try:
        r = subprocess.run(
            [sys.executable, str(HERE / "forge_new.py"), name,
             "--purpose", "A throwaway skill created by the selftest",
             "--category", "helpers", "--trigger", "the selftest runs",
             "--boundary", "anything real", "--casual", "run the selftest",
             "--scripts"], capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"  {'ok  ' if ok else 'FAIL'} scaffold   round-trip exits "
              f"{r.returncode} (generated-files staleness excluded)")
        if not ok:
            problems.append("forge_new produced a skill the gate rejects")
            return
        rows = check(dest)
        bad_rows = sorted(c for c, lvl in rows.items() if lvl == "FAIL")
        print(f"  {'ok  ' if not bad_rows else 'FAIL'} scaffold   gate on fresh "
              f"output -> {bad_rows or 'no blocking rows'}")
        if bad_rows:
            problems.append(f"fresh scaffold fails: {', '.join(bad_rows)}")
    finally:
        shutil.rmtree(dest, ignore_errors=True)


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
    scaffold_roundtrip(problems)

    print()
    for p in problems:
        print(f"  problem: {p}")
    print("SELFTEST", "PASS" if not problems else "FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
