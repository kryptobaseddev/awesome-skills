#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Aggregate per-run grading + timing into a single benchmark.json.

Computes mean and stddev for pass_rate, total_tokens, and duration_ms per
configuration (with_skill / without_skill / old_skill), plus deltas relative
to the chosen baseline.

Usage:
  uv run aggregate_benchmarks.py --workspace <iter-dir>
                                 [--baseline without_skill|old_skill]
                                 [--out benchmark.json]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import die, mean_stddev, read_json, write_json  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True, help="iteration-N directory")
    ap.add_argument("--baseline", default=None,
                    help="baseline config for delta calc; auto-selects without_skill > old_skill")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    iter_dir = Path(args.workspace).expanduser().resolve()
    if not iter_dir.exists():
        die(f"workspace {iter_dir} does not exist")

    # Collect rows: config -> list of (pass_rate, tokens, duration_ms)
    rows: dict[str, list[dict]] = defaultdict(list)
    case_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for case_dir in sorted(iter_dir.glob("eval-*")):
        for cfg_dir in sorted(case_dir.iterdir()):
            if not cfg_dir.is_dir() or cfg_dir.name == "inputs":
                continue
            for run_dir in sorted(cfg_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                grading_f = run_dir / "grading.json"
                timing_f = run_dir / "timing.json"
                if not grading_f.exists():
                    continue
                grading = read_json(grading_f)
                if grading.get("skipped"):
                    continue
                timing = read_json(timing_f) if timing_f.exists() else {}
                row = {
                    "case": case_dir.name[len("eval-"):],
                    "config": cfg_dir.name,
                    "run": run_dir.name,
                    "pass_rate": grading["summary"]["pass_rate"],
                    "total_tokens": timing.get("total_tokens", 0),
                    "duration_ms": timing.get("duration_ms", 0),
                }
                rows[cfg_dir.name].append(row)
                case_rows[(case_dir.name, cfg_dir.name)].append(row)

    if not rows:
        die("no graded runs found in workspace; run grade_assertions.py first")

    # Aggregate per config
    run_summary: dict[str, dict] = {}
    for cfg, items in rows.items():
        run_summary[cfg] = {
            "pass_rate": mean_stddev(r["pass_rate"] for r in items),
            "total_tokens": mean_stddev(r["total_tokens"] for r in items),
            "duration_ms": mean_stddev(r["duration_ms"] for r in items),
            "runs": len(items),
        }

    # Choose baseline
    available_baselines = [c for c in ("without_skill", "old_skill") if c in run_summary]
    chosen_baseline = args.baseline or (available_baselines[0] if available_baselines else None)
    delta: dict | None = None
    if chosen_baseline and chosen_baseline in run_summary and "with_skill" in run_summary:
        w, b = run_summary["with_skill"], run_summary[chosen_baseline]
        delta = {
            "baseline": chosen_baseline,
            "pass_rate": w["pass_rate"]["mean"] - b["pass_rate"]["mean"],
            "total_tokens": w["total_tokens"]["mean"] - b["total_tokens"]["mean"],
            "duration_ms": w["duration_ms"]["mean"] - b["duration_ms"]["mean"],
        }

    # Per-case summary (useful for downstream regression detection)
    per_case = {}
    for (case_dir_name, cfg), items in case_rows.items():
        case_id = case_dir_name[len("eval-"):]
        per_case.setdefault(case_id, {})[cfg] = {
            "pass_rate": mean_stddev(r["pass_rate"] for r in items),
            "total_tokens": mean_stddev(r["total_tokens"] for r in items),
            "duration_ms": mean_stddev(r["duration_ms"] for r in items),
            "runs": len(items),
        }

    out = {
        "iteration_dir": str(iter_dir),
        "run_summary": run_summary,
        "delta": delta,
        "per_case": per_case,
    }
    out_path = Path(args.out) if args.out else (iter_dir / "benchmark.json")
    write_json(out_path, out)

    # Human-readable summary
    print(f"\nbenchmark → {out_path}")
    for cfg, s in run_summary.items():
        print(f"  {cfg:14s}  pass_rate {s['pass_rate']['mean']:.3f} ± {s['pass_rate']['stddev']:.3f}"
              f"   tokens {s['total_tokens']['mean']:7.0f}"
              f"   duration_ms {s['duration_ms']['mean']:7.0f}"
              f"   (n={s['runs']})")
    if delta:
        sign = "+" if delta["pass_rate"] >= 0 else ""
        print(f"\n  delta vs {delta['baseline']}: pass_rate {sign}{delta['pass_rate']:+.3f}"
              f"   tokens {delta['total_tokens']:+.0f}"
              f"   duration_ms {delta['duration_ms']:+.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
