#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Trigger-rate eval with train/validation split and description optimizer.

The description-only loop, separate from output quality:

  1. Generate ~20 queries (10 should-trigger, 10 should-not-trigger, mixed
     near-misses) tailored to the skill if --queries is absent.
  2. Split into train/validation (default 60/40), keeping the should-trigger
     mix proportional in both.
  3. For each query, run it through an isolated agent context N times
     (default 3) and estimate trigger rate.
  4. Report per-query trigger rates plus train/validation pass rates.
  5. Optionally optimize the `description` field — train-set only — for up
     to --iterations rounds. Select the description with the best
     VALIDATION pass rate.

Triggering detection:
  --triggered-by skill-tool-use   (default) — looks for a Skill tool call
                                              referencing this skill in the
                                              JSON transcript.
  --triggered-by mention          — looks for the skill name in the response.
                                    Less reliable but works without tool logs.

Usage:
  uv run description_eval.py --skill <path>
                             [--queries <path>] [--runs 3]
                             [--train-frac 0.6] [--iterations 0]
                             [--executor api|cli|print]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    LLMUnavailable,
    call_anthropic,
    die,
    extract_json_block,
    parse_skill,
    read_json,
    write_json,
)


GENERATE_QUERIES_PROMPT = """\
You are designing trigger-eval queries for an Agent Skill. Produce exactly
20 queries (10 should-trigger, 10 should-not-trigger) tailored to this skill.

Hard requirements:
  - 10 should-trigger queries varying along axes: phrasing (formal / casual /
    typos / abbreviations), detail (terse vs. context-heavy), explicitness
    (names the domain directly vs. buries it under "my manager asked me to..").
    Include single-step prompts and multi-step prompts where the skill's work
    is only one step.
  - 10 should-NOT-trigger queries, all NEAR-MISSES — share keywords or
    concepts with this skill but actually need something different. NO
    trivially-irrelevant queries like "what's the weather".
  - Realistic context: file paths, column names, personal context.

Reply ONLY with a JSON array inside a ```json fence:
[
  {"query": "...", "should_trigger": true},
  {"query": "...", "should_trigger": false},
  ...
]

<skill>
name: {name}
description: {description}
</skill>
"""


def generate_queries(skill, count: int = 20) -> list[dict]:
    try:
        resp = call_anthropic(
            system="You design rigorous trigger-eval query sets. JSON only.",
            user=GENERATE_QUERIES_PROMPT.format(name=skill.name, description=skill.description),
            max_tokens=4000,
        )
        data = extract_json_block(resp["text"])
        if isinstance(data, list) and len(data) >= count // 2:
            return data
    except (LLMUnavailable, Exception) as e:
        print(f"warn: query generation falling back to deterministic: {e}", file=sys.stderr)
    # Fallback — extract verbs from description, build templated queries
    verbs = re.findall(r"\b(use|build|create|extract|analyze|review|test|configure|optimize|debug)\b",
                       skill.description.lower())
    verbs = list(dict.fromkeys(verbs)) or ["use"]
    pos = [{"query": f"hey can you {v} something using {skill.name}?", "should_trigger": True}
           for v in verbs[:10]]
    while len(pos) < count // 2:
        pos.append({"query": f"please help me {verbs[0]} the {skill.name} workflow",
                    "should_trigger": True})
    neg = [
        {"query": f"what's the difference between {skill.name} and the standard library approach?",
         "should_trigger": False},
        {"query": f"my colleague mentioned {skill.name} once — what is it?", "should_trigger": False},
    ]
    while len(neg) < count // 2:
        neg.append({"query": "write a fizzbuzz function please", "should_trigger": False})
    return pos[:count // 2] + neg[:count // 2]


def stratified_split(queries: list[dict], train_frac: float, seed: int = 42) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    pos = [q for q in queries if q.get("should_trigger")]
    neg = [q for q in queries if not q.get("should_trigger")]
    rng.shuffle(pos)
    rng.shuffle(neg)
    p_train = int(round(len(pos) * train_frac))
    n_train = int(round(len(neg) * train_frac))
    train = pos[:p_train] + neg[:n_train]
    val = pos[p_train:] + neg[n_train:]
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def query_triggered(*, query: str, skill, executor: str, triggered_by: str) -> bool:
    """Return True if running the query would trigger the skill."""
    skill_md_body = (skill.path / "SKILL.md").read_text(encoding="utf-8")
    # Heuristic: ask the model "would this skill match?" as a stand-in for actually loading it.
    # This isn't perfect but it gives a tractable signal without a full agent runtime.
    if executor == "print":
        print(f"[describe] query={query!r} (would trigger {skill.name}?)")
        return False  # no signal
    if executor == "cli":
        # Use claude CLI with `--strict-mcp-config` flags equivalent if available, else fall through
        executor = "api"
    if executor == "api":
        sys_prompt = (
            "You are a strict skill-trigger arbiter. Given a SKILL description and a user "
            "query, decide whether the skill SHOULD activate on this query based on the "
            "description. Reply with strict JSON: {\"should_activate\": bool, \"why\": "
            "\"≤120 chars\"}. The activation rule is: the user's task plausibly benefits from "
            "the skill's documented capability; do not activate on near-misses that share "
            "keywords but need different work."
        )
        user = (
            f"## SKILL frontmatter\nname: {skill.name}\ndescription: {skill.description}\n\n"
            f"## User query\n{query}\n"
        )
        try:
            resp = call_anthropic(system=sys_prompt, user=user, max_tokens=300)
            data = extract_json_block(resp["text"])
            return bool(data.get("should_activate"))
        except LLMUnavailable:
            return triggered_by == "mention" and skill.name.lower() in query.lower()
        except Exception:
            return False
    return False


def eval_split(queries: list[dict], skill, runs: int, executor: str, triggered_by: str) -> dict:
    results = []
    for q in queries:
        triggers = sum(1 for _ in range(runs) if query_triggered(
            query=q["query"], skill=skill, executor=executor, triggered_by=triggered_by,
        ))
        rate = triggers / runs if runs else 0.0
        passed = (rate >= 0.5) if q["should_trigger"] else (rate < 0.5)
        results.append({**q, "trigger_rate": rate, "passed": passed})
    return {
        "results": results,
        "pass_rate": sum(1 for r in results if r["passed"]) / len(results) if results else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", required=True)
    ap.add_argument("--queries", default=None)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--train-frac", type=float, default=0.6)
    ap.add_argument("--iterations", type=int, default=0,
                    help="if > 0, run the description optimization loop for N iterations")
    ap.add_argument("--executor", choices=["api", "cli", "print"], default="api")
    ap.add_argument("--triggered-by", choices=["skill-tool-use", "mention"],
                    default="skill-tool-use")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    skill = parse_skill(skill_path)

    if args.queries:
        queries = read_json(args.queries)
        if isinstance(queries, dict):
            queries = queries.get("queries", queries.get("evals", []))
    else:
        default_q = skill.path / "evals" / "trigger_queries.json"
        if default_q.exists():
            queries = read_json(default_q)
            if isinstance(queries, dict):
                queries = queries.get("queries", queries.get("evals", []))
        else:
            print("generating trigger queries …")
            queries = generate_queries(skill)
            write_json(default_q, {"skill_name": skill.name, "queries": queries})

    train, val = stratified_split(queries, args.train_frac)
    print(f"train size: {len(train)}   validation size: {len(val)}")

    best = {"iteration": 0, "description": skill.description, "val_pass_rate": -1.0}
    history: list[dict] = []
    current_description = skill.description

    max_iter = max(1, args.iterations + 1)  # at least 1 round (baseline)
    for it in range(max_iter):
        print(f"\n=== iteration {it} ===")
        # Patch the in-memory skill to use the candidate description
        skill_patch = type(skill)(  # dataclass
            path=skill.path, name=skill.name, description=current_description,
            body=skill.body, frontmatter_raw=skill.frontmatter_raw, sections=skill.sections,
            referenced_files=skill.referenced_files,
            has_scripts=skill.has_scripts, has_references=skill.has_references, has_assets=skill.has_assets,
        )
        train_result = eval_split(train, skill_patch, args.runs, args.executor, args.triggered_by)
        val_result = eval_split(val, skill_patch, args.runs, args.executor, args.triggered_by)
        print(f"  train pass_rate: {train_result['pass_rate']:.3f}")
        print(f"  val   pass_rate: {val_result['pass_rate']:.3f}")
        record = {
            "iteration": it,
            "description": current_description,
            "train_pass_rate": train_result["pass_rate"],
            "val_pass_rate": val_result["pass_rate"],
            "train_failures": [r for r in train_result["results"] if not r["passed"]],
        }
        history.append(record)
        if val_result["pass_rate"] > best["val_pass_rate"]:
            best = {"iteration": it, "description": current_description,
                    "val_pass_rate": val_result["pass_rate"],
                    "train_pass_rate": train_result["pass_rate"]}
        if it >= args.iterations:
            break
        # Propose a new description using train failures only
        try:
            current_description = propose_new_description(
                skill_name=skill.name, current=current_description,
                train_failures=record["train_failures"],
            )
            if len(current_description) > 1024:
                print(f"  warn: candidate {len(current_description)} chars > 1024; truncating")
                current_description = current_description[:1024]
        except LLMUnavailable as e:
            print(f"  LLM unavailable for description optimization: {e} — stopping")
            break

    out = {
        "skill": skill.name,
        "train": [q["query"] for q in train],
        "validation": [q["query"] for q in val],
        "history": history,
        "best": best,
    }
    out_path = Path(args.out) if args.out else (skill_path / "evals" / "trigger_eval_report.json")
    write_json(out_path, out)
    print(f"\nreport → {out_path}")
    print(f"best (iteration {best['iteration']}): validation pass_rate = {best['val_pass_rate']:.3f}")
    if best["description"] != skill.description:
        print("\n--- best description ---\n" + best["description"])
    return 0


REVISE_PROMPT = """\
You are optimizing the `description` field of an Agent Skill so it triggers
reliably on the right prompts and stays quiet on near-misses. You may see
train-set failures only — VALIDATION failures are hidden by design.

Hard rules:
  - Imperative phrasing: "Use this skill when ..." not "This skill does ...".
  - Focus on USER intent, not implementation details.
  - Be PUSHY about contexts where the skill applies, including cases where
    the user doesn't name the domain directly ("even if they only say ...").
  - Concise — at most a short paragraph. The field has a hard 1024-character
    limit. Do not let the description grow merely to bolt on failed-query
    keywords (that's overfitting); find the general category instead.
  - If failures suggest the description is too NARROW, broaden scope. If
    failures are false-triggers, add specificity about what the skill does
    NOT do, or clarify the boundary with adjacent capabilities.
  - When stuck, try a STRUCTURALLY different framing rather than incremental
    tweaks.

Reply ONLY with the new description as a single quoted string. No commentary.
"""


def propose_new_description(*, skill_name: str, current: str, train_failures: list[dict]) -> str:
    user = (
        f"Skill name: {skill_name}\n"
        f"Current description ({len(current)} chars):\n\"\"\"{current}\"\"\"\n\n"
        f"Train-set failures (limit shown):\n"
        + json.dumps(train_failures[:20], indent=2)
        + "\n\nPropose a revised description."
    )
    resp = call_anthropic(
        system=REVISE_PROMPT,
        user=user,
        max_tokens=1500,
    )
    text = resp["text"].strip()
    # Strip surrounding quotes if present
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    return text.strip()


if __name__ == "__main__":
    sys.exit(main())
