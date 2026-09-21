#!/usr/bin/env python3
"""Behavioural trigger measurement — does an agent actually invoke the skill?

`description_eval.py` asks a model to arbitrate whether a description *ought* to
match a query. That measures judged relevance. This measures behaviour: it runs
a real agent against a real project and watches the whole tool sequence for a
`Skill` call or a read of the skill's SKILL.md.

The distinction is not academic. Two ways of measuring this mislead badly:

1. **Judging the first tool call only.** Agents orient before they consult a
   skill -- `ls`, `find`, a couple of `Read`s -- and invoke it several calls
   later. A detector that gives up when call #1 is `Bash` reports 0% for a skill
   that triggers reliably. Measured on a real skill: 0/11 by that method,
   10/11 by scanning the sequence.

2. **Running queries in an empty directory.** A realistic query names files,
   routes or a dev server. In a bare temp dir the agent correctly answers
   "there's nothing here to look at" and never triggers anything. That is a
   property of the fixture, not the description. Point `--cwd` at a project that
   actually contains what the queries talk about.

Trigger rate is also noisy: identical runs of the same 20-query set differed by
two. Use `--runs 3` or more before concluding anything from a delta.

Usage:
  trigger_behavior_eval.py --skill skills/foo --queries evals/trigger_queries.json \\
      --cwd /path/to/realistic/project [--runs 3] [--workers 5] [--out result.json]

Exit: 0 all queries behaved as expected, 1 otherwise, 2 usage error.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import die, parse_skill, write_json  # noqa: E402


def _tool_sequence(stdout: str) -> list[tuple[str, str]]:
    """(tool_name, salient_argument) for every tool call in a stream-json run."""
    seq: list[tuple[str, str]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") != "tool_use":
                continue
            inp = block.get("input", {}) or {}
            arg = str(inp.get("skill") or inp.get("file_path") or inp.get("pattern")
                      or inp.get("command") or "")[:90]
            seq.append((block.get("name", "?"), arg))
    return seq


def run_once(query: str, skill_name: str, cwd: Path, max_turns: int,
             timeout: int) -> dict:
    try:
        proc = subprocess.run(
            ["claude", "-p", query, "--output-format", "stream-json",
             "--verbose", "--max-turns", str(max_turns)],
            cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"triggered": None, "error": "timeout", "sequence": []}
    except FileNotFoundError:
        die("the `claude` CLI is not on PATH; this evaluator needs a real agent runtime")

    seq = _tool_sequence(proc.stdout)
    triggered = any(
        (name == "Skill" and skill_name in arg)
        or (name == "Read" and f"skills/{skill_name}/SKILL.md" in arg)
        for name, arg in seq)
    return {"triggered": triggered,
            "sequence": [f"{n}({a})" for n, a in seq[:14]],
            "calls_before_trigger": next(
                (i for i, (n, a) in enumerate(seq, 1)
                 if n == "Skill" and skill_name in a), None)}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--skill", required=True)
    ap.add_argument("--queries", required=True,
                    help="JSON array of {query, should_trigger}")
    ap.add_argument("--cwd", required=True,
                    help="a REAL project containing what the queries refer to")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    skill = parse_skill(args.skill)
    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        die(f"--cwd is not a directory: {cwd}")
    queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    if not isinstance(queries, list) or not queries:
        die("--queries must be a non-empty JSON array of {query, should_trigger}")

    jobs = [q for q in queries for _ in range(args.runs)]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        raw = list(ex.map(
            lambda q: (q, run_once(q["query"], skill.name, cwd,
                                   args.max_turns, args.timeout)), jobs))

    agg: dict[str, dict] = {}
    for q, r in raw:
        a = agg.setdefault(q["query"], {
            "query": q["query"], "should_trigger": bool(q.get("should_trigger")),
            "hits": 0, "runs": 0, "errors": 0, "sequence": r["sequence"],
            "calls_before_trigger": []})
        a["runs"] += 1
        if r["triggered"] is None:
            a["errors"] += 1
        elif r["triggered"]:
            a["hits"] += 1
            if r.get("calls_before_trigger"):
                a["calls_before_trigger"].append(r["calls_before_trigger"])

    results = []
    for a in agg.values():
        a["rate"] = a["hits"] / a["runs"] if a["runs"] else 0.0
        a["triggered"] = a["rate"] >= 0.5
        a["passed"] = a["triggered"] == a["should_trigger"]
        results.append(a)

    pos = [r for r in results if r["should_trigger"]]
    neg = [r for r in results if not r["should_trigger"]]
    tp = sum(1 for r in pos if r["triggered"])
    tn = sum(1 for r in neg if not r["triggered"])
    depths = [d for r in results for d in r["calls_before_trigger"]]

    print(f"skill                : {skill.name}")
    print(f"fixture              : {cwd}")
    print(f"recall (positives)   : {tp}/{len(pos)}")
    print(f"precision (negatives): {tn}/{len(neg)}")
    print(f"accuracy             : {tp + tn}/{len(results)}")
    if depths:
        print(f"median tool calls before the skill is invoked: "
              f"{sorted(depths)[len(depths) // 2]}  "
              f"(a first-call-only detector would miss every run above 1)")
    print()
    for r in sorted(results, key=lambda x: (x["should_trigger"], x["rate"])):
        tag = "ok  " if r["passed"] else ("MISS " if r["should_trigger"] else "FALSE")
        print(f"{tag} {r['hits']}/{r['runs']}  {r['query'][:70]}")
        if not r["passed"]:
            for s in r["sequence"][:5]:
                print(f"         {s}")

    if args.out:
        write_json(Path(args.out), {
            "skill": skill.name, "fixture": str(cwd), "runs_per_query": args.runs,
            "recall": [tp, len(pos)], "precision": [tn, len(neg)],
            "results": results})
        print(f"\nwrote {args.out}")

    return 0 if tp == len(pos) and tn == len(neg) else 1


if __name__ == "__main__":
    sys.exit(main())
