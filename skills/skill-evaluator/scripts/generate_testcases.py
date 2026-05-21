#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Auto-generate challenging eval test cases UNIQUE to the target skill.

Reads the target SKILL.md, extracts triggers, capabilities, examples, gotchas,
and referenced scripts/assets, then synthesizes test cases that hit:

  - phrasing variety   (formal / casual / typos / abbrev)
  - detail variety     (terse one-liners vs. context-heavy multi-paragraph)
  - explicitness       (names domain directly vs. buries it)
  - edge cases         (malformed input, ambiguity, capability boundaries)
  - near-miss negative (one should-not-trigger prompt — overlapping keywords,
                       different intent)

Uses an LLM when ANTHROPIC_API_KEY or the `claude` CLI is available, falling
back to a deterministic template generator that is still skill-unique
(seeded by the SKILL.md fingerprint, never a generic boilerplate).

Usage:
  uv run generate_testcases.py --skill <skill-path> --count 6 --out <out-path>
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

# allow `from _lib import ...` when invoked via uv/python from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    LLMUnavailable,
    ParsedSkill,
    call_anthropic,
    die,
    extract_json_block,
    parse_skill,
    slugify,
    write_json,
)

PROMPT_TEMPLATE = """\
You are designing an evaluation set for an Agent Skill. The skill is below
inside <skill></skill>. Produce {count} challenging, REALISTIC test prompts
that probe whether the skill produces high-quality outputs.

Hard requirements for the set as a whole:
  - About {pos_count} prompts SHOULD activate the skill (`should_trigger: true`).
  - About {neg_count} prompts should NOT activate the skill (`should_trigger: false`)
    but must be NEAR-MISSES — share keywords or concepts with the skill yet
    actually need something different. No trivial negatives.
  - At least {edge_count} prompts must hit an edge case: malformed/missing
    inputs, ambiguous wording, a capability boundary, an unusual combination
    not shown in the skill's own examples, or a request that mixes the skill's
    domain with an unrelated one.
  - Vary phrasing (formal, casual, with typos/abbreviations), vary detail
    (terse vs. context-heavy multi-paragraph), vary explicitness (names the
    domain directly vs. buries it). Include realistic context (file paths,
    column names, personal context like "my manager asked me to…").
  - DO NOT just reuse the skill's own example prompts. Push beyond them.

For each test case provide:
  - "id": short kebab-case slug (unique)
  - "prompt": the exact user prompt
  - "should_trigger": bool
  - "expected_output": one-sentence human description of what success looks like
  - "assertions": 3-6 specific, observable, programmatically- or
    LLM-checkable assertions. NO vague "looks good" assertions. Prefer
    "the output contains X", "the file at Y has Z rows", "valid JSON",
    "labelled axes", "exactly N items".
  - "files" (optional): list of input file paths the test would supply

Reply ONLY with a JSON array of test cases inside a ```json fenced block.
Do not include commentary outside the fence.

<skill>
name: {name}
description: {description}

{body_excerpt}
</skill>
"""


def build_prompt(skill: ParsedSkill, count: int, edge_fraction: float) -> str:
    pos_count = max(1, round(count * 0.75))
    neg_count = max(1, count - pos_count)
    edge_count = max(1, round(count * edge_fraction))
    excerpt = _excerpt_body(skill.body, max_chars=5500)
    return PROMPT_TEMPLATE.format(
        count=count,
        pos_count=pos_count,
        neg_count=neg_count,
        edge_count=edge_count,
        name=skill.name,
        description=skill.description,
        body_excerpt=excerpt,
    )


def _excerpt_body(body: str, max_chars: int) -> str:
    if len(body) <= max_chars:
        return body
    # Keep the first part (intro/usage) and a tail snippet (gotchas often live near end)
    head = body[: int(max_chars * 0.75)]
    tail = body[-int(max_chars * 0.25) :]
    return head + "\n\n[…truncated…]\n\n" + tail


def llm_generate(skill: ParsedSkill, count: int, edge_fraction: float) -> list[dict]:
    prompt = build_prompt(skill, count, edge_fraction)
    resp = call_anthropic(
        system=(
            "You design rigorous evaluations for AI agent skills. You are "
            "creative, specific, and never produce generic boilerplate. You "
            "always reply with the JSON block requested — nothing else."
        ),
        user=prompt,
        max_tokens=8000,
    )
    try:
        cases = extract_json_block(resp["text"])
    except Exception as e:
        raise RuntimeError(
            f"LLM returned non-JSON or malformed JSON. First 400 chars:\n{resp['text'][:400]}"
        ) from e
    if not isinstance(cases, list):
        raise RuntimeError("LLM response was not a JSON array of test cases")
    return cases


# -- deterministic fallback --------------------------------------------------


_FALLBACK_TEMPLATES_POS = [
    "I'm trying to {capability} — can you walk me through it for {topic}?",
    "hey can you {capability} for me real quick, files are in ~/work/{topic}",
    "I need to {capability}. Specifically: {detail}. What's the right approach?",
    "{capability} please. Context: I'm working on {topic} and my lead asked for a quick turnaround.",
    "Help — {capability} for {topic}. Bonus: handle {edge}.",
    "Walk me through {capability} step by step. The data lives in {detail}.",
]

_FALLBACK_TEMPLATES_NEG = [
    "What's the difference between {topic} and {decoy_topic}? Just curious.",
    "Write a python script that does {decoy_capability} — totally unrelated to {topic}.",
    "Can you explain how {decoy_topic} relates to {topic} historically?",
]

_EDGE_FRAGMENTS = [
    "the file is malformed",
    "some rows are missing values",
    "the input contains a unicode BOM",
    "the schema isn't documented",
    "I'm not sure if this is the right format",
    "the dataset is much larger than usual",
]


def _extract_capabilities(skill: ParsedSkill) -> list[str]:
    """Best-effort capability extraction from the description and body."""
    text = f"{skill.description} {skill.body}"
    # Verbs followed by noun phrases — heuristic
    candidates: list[str] = []
    for m in re.finditer(
        r"\b("
        r"analyze|build|create|deploy|generate|process|extract|merge|convert|"
        r"validate|review|test|optimize|migrate|debug|fix|configure|integrate"
        r")\s+([a-zA-Z][a-zA-Z0-9 \-]{2,40})",
        text,
        re.IGNORECASE,
    ):
        candidates.append(f"{m.group(1).lower()} {m.group(2).strip().lower()}")
    # Dedup, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= 10:
            break
    if not out:
        out = [f"use the {skill.name} skill"]
    return out


def deterministic_generate(skill: ParsedSkill, count: int, edge_fraction: float) -> list[dict]:
    rng = random.Random(skill.fingerprint)  # deterministic per skill
    capabilities = _extract_capabilities(skill)
    pos_count = max(1, round(count * 0.75))
    neg_count = max(1, count - pos_count)
    edge_count = max(1, round(count * edge_fraction))

    cases: list[dict] = []
    edge_indices = set(rng.sample(range(pos_count), min(edge_count, pos_count)))
    for i in range(pos_count):
        cap = rng.choice(capabilities)
        edge = rng.choice(_EDGE_FRAGMENTS) if i in edge_indices else ""
        topic = re.sub(r"^\w+\s+", "", cap)  # capability minus the leading verb
        detail = rng.choice([
            "I'd like a structured summary with clear next steps",
            f"output should include at least 3 concrete examples from {topic}",
            f"keep the response under 200 lines",
            f"highlight any risks specific to {topic}",
        ])
        tmpl = rng.choice(_FALLBACK_TEMPLATES_POS)
        prompt = tmpl.format(capability=cap, topic=topic, detail=detail, edge=edge or "the common edge cases")
        cases.append({
            "id": slugify(f"{skill.name}-pos-{i+1}-{cap}", maxlen=48),
            "prompt": prompt,
            "should_trigger": True,
            "expected_output": (
                f"A clear, accurate, on-task response that demonstrates the {skill.name} workflow "
                f"for: {cap}. Includes concrete steps and references the skill's bundled resources where relevant."
            ),
            "assertions": [
                f"The response addresses the requested capability ({cap}) directly",
                "The response is grounded in the skill's documented workflow, not generic advice",
                "The response includes at least one concrete, actionable step",
                "The response stays within scope of the user's request",
            ] + ([f"The response handles the edge condition: {edge}"] if edge else []),
            "files": [],
        })

    decoy_topics = ["sql tuning", "kubernetes scaling", "react performance", "DNS propagation"]
    decoy_capabilities = ["upload csv rows to postgres", "render markdown", "compress images"]
    for i in range(neg_count):
        tmpl = rng.choice(_FALLBACK_TEMPLATES_NEG)
        topic = re.sub(r"^\w+\s+", "", capabilities[0])
        decoy_topic = rng.choice(decoy_topics)
        decoy_capability = rng.choice(decoy_capabilities)
        prompt = tmpl.format(
            topic=topic, decoy_topic=decoy_topic, decoy_capability=decoy_capability
        )
        cases.append({
            "id": slugify(f"{skill.name}-neg-{i+1}", maxlen=48),
            "prompt": prompt,
            "should_trigger": False,
            "expected_output": (
                "The agent should NOT load this skill. It should answer with general knowledge "
                "or a different specialty. The output is graded only on whether the skill triggers."
            ),
            "assertions": [
                "The skill is NOT invoked (negative test)",
            ],
            "files": [],
        })

    return cases


# -- CLI ---------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", required=True, help="path to the target skill directory")
    ap.add_argument("--count", type=int, default=6, help="number of test cases to generate")
    ap.add_argument("--edge-fraction", type=float, default=0.35,
                    help="fraction of positive cases that hit an edge condition (0..1)")
    ap.add_argument("--out", default=None,
                    help="output path. defaults to <skill>/evals/evals.json")
    ap.add_argument("--force-deterministic", action="store_true",
                    help="skip LLM and use deterministic generation only")
    args = ap.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    try:
        skill = parse_skill(skill_path)
    except Exception as e:
        die(str(e))

    used_llm = False
    cases: list[dict] = []
    if not args.force_deterministic:
        try:
            cases = llm_generate(skill, args.count, args.edge_fraction)
            used_llm = True
        except LLMUnavailable as e:
            print(f"warn: LLM unavailable — falling back to deterministic generator ({e})",
                  file=sys.stderr)
        except Exception as e:
            print(f"warn: LLM generation failed ({type(e).__name__}: {e}) — falling back",
                  file=sys.stderr)

    if not cases:
        cases = deterministic_generate(skill, args.count, args.edge_fraction)

    out_path = Path(args.out) if args.out else (skill_path / "evals" / "evals.json")
    payload = {
        "skill_name": skill.name,
        "skill_fingerprint": skill.fingerprint,
        "generated_by": "llm" if used_llm else "deterministic",
        "evals": cases,
    }
    write_json(out_path, payload)
    print(f"wrote {len(cases)} test cases to {out_path} ({'llm' if used_llm else 'deterministic'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
