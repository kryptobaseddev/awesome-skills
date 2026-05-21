#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Extract actionable patterns from a graded iteration.

Surfaces five categories of signal:

  1. always_pass_in_both       — assertions that pass with-skill AND without-skill
                                 (these inflate scores without measuring skill value)
  2. always_fail_in_both       — assertions that fail in both configs
                                 (broken assertion, impossible test, or fundamental gap)
  3. skill_dependent           — assertions that pass with-skill but fail without
                                 (this is where the skill is earning its keep)
  4. flaky                     — assertions whose result varies across repeated runs
                                 (sensitive to model randomness or skill ambiguity)
  5. cost_outliers             — cases where with-skill tokens or duration are >25%
                                 above the cohort mean

Reads the per-run grading.json and timing.json files produced by run_eval.py
and grade_assertions.py.

Usage:
  uv run analyze_patterns.py --workspace <iter-dir>
                             [--benchmark <iter-dir>/benchmark.json]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import die, read_json, write_json  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--benchmark", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    iter_dir = Path(args.workspace).expanduser().resolve()
    if not iter_dir.exists():
        die(f"workspace {iter_dir} does not exist")

    # (case_id, assertion_text) -> {config: [pass_bool, …]}
    assertion_outcomes: dict[tuple[str, str], dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    # (case_id, config) -> list of timing dicts
    case_timings: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for case_dir in sorted(iter_dir.glob("eval-*")):
        case_id = case_dir.name[len("eval-"):]
        for cfg_dir in sorted(case_dir.iterdir()):
            if not cfg_dir.is_dir() or cfg_dir.name == "inputs":
                continue
            for run_dir in sorted(cfg_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                grading_f = run_dir / "grading.json"
                if not grading_f.exists():
                    continue
                g = read_json(grading_f)
                if g.get("skipped"):
                    continue
                for a in g.get("assertion_results", []):
                    key = (case_id, a["text"])
                    assertion_outcomes[key][cfg_dir.name].append(bool(a["passed"]))
                t = run_dir / "timing.json"
                if t.exists():
                    case_timings[(case_id, cfg_dir.name)].append(read_json(t))

    if not assertion_outcomes:
        die("no graded assertions found; run grade_assertions.py first")

    always_pass_both: list[dict] = []
    always_fail_both: list[dict] = []
    skill_dependent: list[dict] = []
    flaky: list[dict] = []

    for (case_id, atext), per_cfg in assertion_outcomes.items():
        with_results = per_cfg.get("with_skill", [])
        wo_results = per_cfg.get("without_skill", [])

        def rate(rs: list[bool]) -> float:
            return (sum(rs) / len(rs)) if rs else float("nan")

        w_rate = rate(with_results)
        wo_rate = rate(wo_results)

        # Flaky: any config with mixed PASS/FAIL across runs
        is_flaky = any(0 < sum(rs) < len(rs) for rs in per_cfg.values())
        if is_flaky:
            flaky.append({
                "case": case_id, "assertion": atext,
                "per_config_rate": {k: rate(v) for k, v in per_cfg.items()},
            })
            # flaky cases can also fit other buckets — don't continue

        if with_results and wo_results:
            if w_rate == 1.0 and wo_rate == 1.0:
                always_pass_both.append({"case": case_id, "assertion": atext})
            elif w_rate == 0.0 and wo_rate == 0.0:
                always_fail_both.append({"case": case_id, "assertion": atext})
            elif w_rate > wo_rate and w_rate >= 0.5:
                skill_dependent.append({
                    "case": case_id, "assertion": atext,
                    "with_rate": w_rate, "without_rate": wo_rate,
                    "lift": w_rate - wo_rate,
                })

    # Cost outliers
    cost_outliers: list[dict] = []
    with_tokens = [
        statistics.fmean([t["total_tokens"] for t in ts if t.get("total_tokens", 0) > 0]) if ts else 0
        for (cid, cfg), ts in case_timings.items() if cfg == "with_skill"
    ]
    if with_tokens:
        mean_t = statistics.fmean(with_tokens)
        for (cid, cfg), ts in case_timings.items():
            if cfg != "with_skill" or not ts:
                continue
            mean_case = statistics.fmean(t.get("total_tokens", 0) for t in ts)
            if mean_t > 0 and mean_case > mean_t * 1.25:
                cost_outliers.append({"case": cid, "mean_tokens": int(mean_case), "cohort_mean": int(mean_t)})

    patterns = {
        "iteration_dir": str(iter_dir),
        "always_pass_in_both": sorted(always_pass_both, key=lambda d: (d["case"], d["assertion"])),
        "always_fail_in_both": sorted(always_fail_both, key=lambda d: (d["case"], d["assertion"])),
        "skill_dependent": sorted(skill_dependent, key=lambda d: -d["lift"]),
        "flaky": sorted(flaky, key=lambda d: (d["case"], d["assertion"])),
        "cost_outliers": cost_outliers,
    }
    out_path = Path(args.out) if args.out else (iter_dir / "patterns.json")
    write_json(out_path, patterns)

    print(f"\npatterns → {out_path}")
    print(f"  always_pass_in_both : {len(patterns['always_pass_in_both'])} (drop these)")
    print(f"  always_fail_in_both : {len(patterns['always_fail_in_both'])} (broken or impossible)")
    print(f"  skill_dependent     : {len(patterns['skill_dependent'])} (where the skill earns its keep)")
    print(f"  flaky               : {len(patterns['flaky'])} (tighten ambiguity)")
    print(f"  cost_outliers       : {len(patterns['cost_outliers'])} (investigate transcripts)")
    if patterns["skill_dependent"]:
        print("\nTop skill-dependent assertions (largest lift):")
        for a in patterns["skill_dependent"][:5]:
            print(f"  +{a['lift']:.2f}  {a['case']} :: {a['assertion'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
