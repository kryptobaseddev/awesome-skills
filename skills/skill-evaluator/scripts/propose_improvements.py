#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""LLM-driven improvement proposer with regression guardrails.

Feeds the current SKILL.md, failed-assertion details, transcripts of the
worst-performing runs, pattern analysis, regression report, and any human
feedback.json to an LLM along with a strict proposer prompt that:

  - generalises from feedback (no per-case patches)
  - prefers cuts over additions (lean wins)
  - explains *why* in instructions, not just *what*
  - bundles repeated work into scripts/
  - NEVER weakens an instruction known to defeat a previously-fixed regression
    (the prompt is given the regression_report.json as a hard constraint)

Writes <iter-dir>/proposal.md with:
  - A short diagnosis of the problems
  - A concrete diff-like proposal for SKILL.md
  - A list of suggested additions to scripts/ or references/
  - An explicit "Do NOT change" list derived from the regression report

NEVER auto-applies. Review before editing the skill.

Usage:
  uv run propose_improvements.py --skill <path> --workspace <iter-dir>
                                 [--feedback <feedback.json>]
                                 [--out <iter-dir>/proposal.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    LLMUnavailable,
    call_anthropic,
    die,
    parse_skill,
    read_json,
    write_text,
)


SYSTEM = """\
You are a senior skill engineer reviewing an Agent Skill that just ran an
evaluation. You produce a concrete, lean improvement proposal that addresses
the failures in evidence WITHOUT regressing what already works.

Hard rules:
  1. NEVER propose removing or weakening instructions listed in the
     "Do-Not-Weaken" section — those previously defeated regressions.
  2. Generalize fixes: propose changes that broaden the skill's robustness
     across many prompts, not per-case patches for individual failures.
  3. Prefer cuts over additions. Lean skills outperform exhaustive ones.
  4. When you add a rule, explain *why* it matters — reasoning-based
     instructions outperform rigid directives.
  5. If transcripts show the agent independently reinventing the same logic
     (a chart builder, a parser, a validator), recommend bundling a script
     in scripts/ rather than adding more prose.
  6. Keep SKILL.md under 500 lines; move detailed material to references/.
  7. Keep the `description` field under 1024 chars and do not let it grow
     unnecessarily.

Output strictly as Markdown with these sections:
  ## Diagnosis
  ## Proposed changes (SKILL.md)
  ## Proposed additions (scripts/ or references/)
  ## Do-NOT-weaken constraints honored
  ## Risks of this proposal
"""


def collect_failing_assertions(iter_dir: Path, limit: int = 25) -> list[dict]:
    fails: list[dict] = []
    for case_dir in sorted(iter_dir.glob("eval-*")):
        case_id = case_dir.name[len("eval-"):]
        for cfg_dir in sorted(case_dir.iterdir()):
            if not cfg_dir.is_dir() or cfg_dir.name != "with_skill":
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
                    if not a.get("passed"):
                        fails.append({
                            "case": case_id, "config": cfg_dir.name, "run": run_dir.name,
                            "assertion": a["text"], "evidence": a.get("evidence", ""),
                            "method": a.get("method", ""),
                        })
    return fails[:limit]


def collect_transcript_excerpts(iter_dir: Path, limit_per_case: int = 1, max_chars: int = 2000) -> list[dict]:
    excerpts = []
    for case_dir in sorted(iter_dir.glob("eval-*")):
        case_id = case_dir.name[len("eval-"):]
        # Pick the first failing with_skill run if any
        added = 0
        for cfg_dir in [case_dir / "with_skill"]:
            if not cfg_dir.exists():
                continue
            for run_dir in sorted(cfg_dir.iterdir()):
                if added >= limit_per_case:
                    break
                gf = run_dir / "grading.json"
                tf = run_dir / "transcript.jsonl"
                if not (gf.exists() and tf.exists()):
                    continue
                g = read_json(gf)
                if g.get("skipped"):
                    continue
                if any(not a.get("passed") for a in g.get("assertion_results", [])):
                    excerpts.append({
                        "case": case_id, "run": run_dir.name,
                        "transcript_excerpt": tf.read_text(encoding='utf-8', errors='replace')[:max_chars],
                    })
                    added += 1
    return excerpts


def collect_do_not_weaken(iter_dir: Path) -> list[str]:
    """Extract do-not-weaken constraints from prior iterations' regression reports."""
    constraints: list[str] = []
    workspace = iter_dir.parent
    for prev in sorted(workspace.glob("iteration-*")):
        if prev == iter_dir:
            continue
        rr = prev / "regression_report.json"
        if not rr.exists():
            continue
        try:
            data = read_json(rr)
            for h in data.get("hard_regressions", []):
                constraints.append(
                    f"[from {prev.name}] {h['case']} :: {h['assertion']} (previously fixed)"
                )
        except Exception:
            pass
    return constraints


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", required=True)
    ap.add_argument("--workspace", required=True, help="iteration-N directory")
    ap.add_argument("--feedback", default=None, help="optional feedback.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    iter_dir = Path(args.workspace).expanduser().resolve()
    if not iter_dir.exists():
        die(f"workspace {iter_dir} does not exist")

    skill = parse_skill(skill_path)
    failures = collect_failing_assertions(iter_dir)
    transcripts = collect_transcript_excerpts(iter_dir)
    patterns = read_json(iter_dir / "patterns.json") if (iter_dir / "patterns.json").exists() else {}
    benchmark = read_json(iter_dir / "benchmark.json") if (iter_dir / "benchmark.json").exists() else {}
    regression = read_json(iter_dir / "regression_report.json") if (iter_dir / "regression_report.json").exists() else {}
    feedback = read_json(Path(args.feedback).expanduser().resolve()) if args.feedback and Path(args.feedback).exists() else {}
    do_not_weaken = collect_do_not_weaken(iter_dir)

    user = (
        f"# Skill: {skill.name}\n\n"
        f"## Current SKILL.md\n```markdown\n{skill.path.joinpath('SKILL.md').read_text(encoding='utf-8')}\n```\n\n"
        f"## Benchmark summary\n```json\n{json.dumps(benchmark.get('run_summary', {}), indent=2)}\n```\n\n"
        f"## Failing assertions ({len(failures)} shown)\n```json\n{json.dumps(failures, indent=2)[:8000]}\n```\n\n"
        f"## Pattern analysis\n```json\n{json.dumps(patterns, indent=2)[:4000]}\n```\n\n"
        f"## Regression report\n```json\n{json.dumps(regression, indent=2)[:4000]}\n```\n\n"
        f"## Human feedback (may be empty)\n```json\n{json.dumps(feedback, indent=2)[:2000]}\n```\n\n"
        f"## Transcript excerpts of failing runs\n```\n"
        + "\n\n".join(f"### {e['case']} / {e['run']}\n{e['transcript_excerpt']}" for e in transcripts[:5])
        + "\n```\n\n"
        f"## Do-NOT-weaken constraints (from prior regressions)\n"
        + ("\n".join(f"- {c}" for c in do_not_weaken) if do_not_weaken else "(none yet)")
        + "\n\nWrite the proposal now."
    )

    try:
        resp = call_anthropic(system=SYSTEM, user=user, max_tokens=6000)
        proposal_md = resp["text"]
    except LLMUnavailable as e:
        proposal_md = (
            f"# Proposal (LLM unavailable: {e})\n\n"
            "## Diagnosis\n\n"
            f"Could not synthesize an LLM proposal. {len(failures)} failing assertions "
            f"were collected from {iter_dir.name}; review them manually:\n\n"
            + "\n".join(f"- **{f['case']}**: {f['assertion']} — {f['evidence']}" for f in failures[:20])
            + "\n\n## Do-NOT-weaken constraints honored\n\n"
            + ("\n".join(f"- {c}" for c in do_not_weaken) if do_not_weaken else "(none yet)\n")
        )

    out_path = Path(args.out) if args.out else (iter_dir / "proposal.md")
    write_text(out_path, proposal_md)
    print(f"\nproposal → {out_path}")
    print(f"  failing assertions surveyed : {len(failures)}")
    print(f"  do-not-weaken constraints   : {len(do_not_weaken)}")
    print(f"  transcripts inspected       : {len(transcripts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
