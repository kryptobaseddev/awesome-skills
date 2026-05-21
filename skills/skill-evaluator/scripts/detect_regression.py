#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Detect regression across two iterations of a skill.

A skill can lift overall pass rate while silently breaking an old behavior.
This script compares per-assertion and per-case outcomes between two
iterations of the same eval set and flags:

  - hard_regressions:   assertion that PASSED before but FAILS now
  - case_regressions:   per-case pass-rate dropped by more than (max(prev_stddev, 0.10))
  - cost_regressions:   per-case mean tokens or duration grew >25% without a
                         matching pass-rate increase
  - blind_regressions:  if a blind_comparison.json is present and the judge
                         preferred the OLD version

A non-empty hard_regressions list should BLOCK declaring the new iteration
an improvement until the regressions are fixed or explicitly accepted.

Usage:
  uv run detect_regression.py --baseline <prev-iter>/benchmark.json \\
                              --current  <curr-iter>/benchmark.json \\
                              [--eval-results <curr-iter-dir>]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import read_json, write_json, die  # noqa: E402


def per_assertion_outcomes(iter_dir: Path) -> dict[tuple[str, str], dict[str, list[bool]]]:
    """case_id, assertion -> {config: [passed_bools]}"""
    out: dict[tuple[str, str], dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for case_dir in sorted(iter_dir.glob("eval-*")):
        case_id = case_dir.name[len("eval-"):]
        for cfg_dir in sorted(case_dir.iterdir()):
            if not cfg_dir.is_dir() or cfg_dir.name == "inputs":
                continue
            for run_dir in sorted(cfg_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                gf = run_dir / "grading.json"
                if not gf.exists():
                    continue
                g = read_json(gf)
                if g.get("skipped"):
                    continue
                for a in g.get("assertion_results", []):
                    out[(case_id, a["text"])][cfg_dir.name].append(bool(a["passed"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baseline", required=True, help="previous iteration's benchmark.json")
    ap.add_argument("--current", required=True, help="current iteration's benchmark.json")
    ap.add_argument("--eval-results", default=None,
                    help="current iteration directory (for per-assertion comparison)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    baseline = read_json(Path(args.baseline).expanduser().resolve())
    current = read_json(Path(args.current).expanduser().resolve())

    # Per-case regressions
    case_regressions: list[dict] = []
    cost_regressions: list[dict] = []
    prev_per_case = baseline.get("per_case", {})
    curr_per_case = current.get("per_case", {})
    for case_id, prev_cfgs in prev_per_case.items():
        curr_cfgs = curr_per_case.get(case_id, {})
        prev_w = prev_cfgs.get("with_skill")
        curr_w = curr_cfgs.get("with_skill")
        if not prev_w or not curr_w:
            continue
        prev_rate = prev_w["pass_rate"]["mean"]
        curr_rate = curr_w["pass_rate"]["mean"]
        prev_std = max(prev_w["pass_rate"]["stddev"], 0.10)  # noise floor
        if (prev_rate - curr_rate) > prev_std:
            case_regressions.append({
                "case": case_id,
                "prev_pass_rate": prev_rate,
                "curr_pass_rate": curr_rate,
                "delta": curr_rate - prev_rate,
                "noise_floor": prev_std,
            })

        # Cost regression: tokens or duration up >25% without matching pass-rate lift
        for axis in ("total_tokens", "duration_ms"):
            prev_v = prev_w[axis]["mean"]
            curr_v = curr_w[axis]["mean"]
            if prev_v > 0 and curr_v > prev_v * 1.25 and curr_rate <= prev_rate + 0.05:
                cost_regressions.append({
                    "case": case_id, "axis": axis,
                    "prev": prev_v, "curr": curr_v,
                    "growth_pct": (curr_v - prev_v) / prev_v * 100,
                    "pass_rate_delta": curr_rate - prev_rate,
                })

    # Per-assertion hard regressions (require --eval-results path on both sides)
    hard_regressions: list[dict] = []
    if args.eval_results:
        curr_dir = Path(args.eval_results).expanduser().resolve()
        # Try to infer the baseline iteration directory from the baseline file location
        baseline_dir = Path(args.baseline).expanduser().resolve().parent
        if baseline_dir.exists():
            prev_outcomes = per_assertion_outcomes(baseline_dir)
            curr_outcomes = per_assertion_outcomes(curr_dir)
            for key, prev_by_cfg in prev_outcomes.items():
                curr_by_cfg = curr_outcomes.get(key, {})
                prev_with = prev_by_cfg.get("with_skill", [])
                curr_with = curr_by_cfg.get("with_skill", [])
                if not prev_with or not curr_with:
                    continue
                prev_rate = sum(prev_with) / len(prev_with)
                curr_rate = sum(curr_with) / len(curr_with)
                if prev_rate >= 0.66 and curr_rate <= 0.34:
                    hard_regressions.append({
                        "case": key[0], "assertion": key[1],
                        "prev_pass_rate": prev_rate, "curr_pass_rate": curr_rate,
                    })

    # Blind regression
    blind_regression = None
    if args.eval_results:
        bc = Path(args.eval_results) / "blind_comparison.json"
        if bc.exists():
            data = read_json(bc)
            old_wins = sum(1 for c in data.get("comparisons", []) if c.get("winner") == "old_skill")
            new_wins = sum(1 for c in data.get("comparisons", []) if c.get("winner") == "with_skill")
            ties = sum(1 for c in data.get("comparisons", []) if c.get("winner") in ("tie", "neither"))
            if old_wins > new_wins:
                blind_regression = {
                    "old_wins": old_wins, "new_wins": new_wins, "ties": ties,
                    "verdict": "blind judge preferred the OLD version more often",
                }

    # Overall delta
    prev_pass = baseline.get("run_summary", {}).get("with_skill", {}).get("pass_rate", {}).get("mean", 0.0)
    curr_pass = current.get("run_summary", {}).get("with_skill", {}).get("pass_rate", {}).get("mean", 0.0)

    report = {
        "baseline_iteration": baseline.get("iteration_dir"),
        "current_iteration": current.get("iteration_dir"),
        "overall": {
            "prev_pass_rate": prev_pass,
            "curr_pass_rate": curr_pass,
            "delta": curr_pass - prev_pass,
        },
        "hard_regressions": hard_regressions,
        "case_regressions": case_regressions,
        "cost_regressions": cost_regressions,
        "blind_regression": blind_regression,
        "blocked": bool(hard_regressions or blind_regression),
    }
    out_path = Path(args.out) if args.out else (
        Path(args.eval_results).expanduser().resolve() / "regression_report.json"
        if args.eval_results else Path("regression_report.json")
    )
    write_json(out_path, report)

    print(f"\nregression report → {out_path}")
    print(f"  overall pass_rate delta : {report['overall']['delta']:+.3f}")
    print(f"  hard_regressions        : {len(hard_regressions)}")
    print(f"  case_regressions        : {len(case_regressions)}")
    print(f"  cost_regressions        : {len(cost_regressions)}")
    print(f"  blind_regression        : {'YES' if blind_regression else 'no'}")
    if report["blocked"]:
        print("\n  ❌ BLOCKED: do not declare this iteration an improvement until "
              "the hard / blind regressions are addressed.")
        return 1
    print("\n  ✅ no hard or blind regressions detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
