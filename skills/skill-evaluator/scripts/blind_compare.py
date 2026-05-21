#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Blind A/B holistic-quality judge.

For each test case, pair the with_skill output with the chosen baseline
(without_skill or old_skill), shuffle so the judge can't tell which is
which, and ask an LLM to score them on holistic qualities (organization,
formatting, usability, polish) that assertions miss.

Writes <iter-dir>/blind_comparison.json with per-case results and an
overall winner tally.

Usage:
  uv run blind_compare.py --workspace <iter-dir>
                          [--pairs with_skill,old_skill]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    LLMUnavailable,
    call_anthropic,
    die,
    extract_json_block,
    read_json,
    write_json,
)


JUDGE_PROMPT = """\
You are a rigorous blind judge of LLM agent outputs. You will see two outputs
produced for the same user prompt, labelled "A" and "B". You do NOT know which
agent produced which. Score them on the rubric below, then declare a winner.

Rubric (1-5 each):
  - on_task        : addresses the user's actual request
  - depth          : substantive, specific, not generic
  - structure      : organized, scannable, well-formatted
  - actionability  : clear next steps or usable artifacts
  - correctness    : free from obvious factual or logical errors

Reply with strict JSON only, inside a fenced ```json block:
{
  "A": {"on_task": int, "depth": int, "structure": int, "actionability": int, "correctness": int, "comments": "≤200 chars"},
  "B": {"on_task": int, "depth": int, "structure": int, "actionability": int, "correctness": int, "comments": "≤200 chars"},
  "winner": "A" | "B" | "tie",
  "winner_reason": "≤200 chars"
}
"""


def load_outputs(run_dir: Path) -> str:
    out_dir = run_dir / "outputs"
    if not out_dir.exists():
        return ""
    chunks = []
    for f in sorted(out_dir.rglob("*")):
        if not f.is_file():
            continue
        try:
            chunks.append(f"--- {f.name} ---\n{f.read_text(encoding='utf-8')}")
        except UnicodeDecodeError:
            chunks.append(f"--- {f.name} ---\n<binary>")
    return "\n\n".join(chunks)


def pick_first_run(case_dir: Path, cfg: str) -> Path | None:
    cfg_dir = case_dir / cfg
    if not cfg_dir.exists():
        return None
    runs = sorted(cfg_dir.iterdir())
    return runs[0] if runs else None


def compare_pair(case_id: str, prompt: str, out_a: str, out_b: str) -> dict:
    user = (
        f"## User prompt\n{prompt}\n\n"
        f"## Output A\n```\n{out_a[:5000]}\n```\n\n"
        f"## Output B\n```\n{out_b[:5000]}\n```\n"
    )
    try:
        resp = call_anthropic(system=JUDGE_PROMPT, user=user, max_tokens=1500)
    except LLMUnavailable as e:
        return {"case": case_id, "winner": "unavailable", "error": str(e)}
    try:
        data = extract_json_block(resp["text"])
    except Exception:
        return {"case": case_id, "winner": "parse_error", "raw": resp["text"][:500]}
    data["case"] = case_id
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--pairs", default="with_skill,without_skill",
                    help="comma-separated config pair (default: with_skill,without_skill)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    iter_dir = Path(args.workspace).expanduser().resolve()
    if not iter_dir.exists():
        die(f"workspace {iter_dir} does not exist")

    cfg_a, cfg_b = (s.strip() for s in args.pairs.split(","))
    rng = random.Random(args.seed)

    # Try to load evals.json to grab the prompt
    case_prompts: dict[str, str] = {}
    for ep in iter_dir.parent.glob("**/evals.json"):
        try:
            data = read_json(ep)
            for c in data.get("evals", []):
                case_prompts[c["id"]] = c.get("prompt", "")
        except Exception:
            pass

    comparisons: list[dict] = []
    for case_dir in sorted(iter_dir.glob("eval-*")):
        case_id = case_dir.name[len("eval-"):]
        a_run = pick_first_run(case_dir, cfg_a)
        b_run = pick_first_run(case_dir, cfg_b)
        if not a_run or not b_run:
            continue
        a_out = load_outputs(a_run)
        b_out = load_outputs(b_run)
        if not a_out.strip() or not b_out.strip():
            comparisons.append({"case": case_id, "winner": "skipped", "reason": "missing output"})
            continue
        # Shuffle so judge can't tell which is which
        if rng.random() < 0.5:
            display = (a_out, b_out)
            mapping = {"A": cfg_a, "B": cfg_b}
        else:
            display = (b_out, a_out)
            mapping = {"A": cfg_b, "B": cfg_a}
        prompt = case_prompts.get(case_id, "<prompt not found>")
        verdict = compare_pair(case_id, prompt, display[0], display[1])
        # Map A/B back to config names
        if verdict.get("winner") in ("A", "B"):
            verdict["winner"] = mapping[verdict["winner"]]
        verdict["mapping"] = mapping
        comparisons.append(verdict)

    tally = {"with_skill": 0, "without_skill": 0, "old_skill": 0, "tie": 0, "other": 0}
    for c in comparisons:
        w = c.get("winner", "other")
        tally[w] = tally.get(w, 0) + 1

    out = {
        "iteration_dir": str(iter_dir),
        "pair": [cfg_a, cfg_b],
        "comparisons": comparisons,
        "tally": tally,
    }
    out_path = Path(args.out) if args.out else (iter_dir / "blind_comparison.json")
    write_json(out_path, out)
    print(f"\nblind comparison → {out_path}")
    for k, v in tally.items():
        if v:
            print(f"  {k:14s} : {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
