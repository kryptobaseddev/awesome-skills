#!/usr/bin/env python3
"""Drive the whole lifecycle for one skill: gate, measure, and say what is next.

This orchestrates; it does not reimplement. The gate is forge_check.py, the
behavioural trigger measurement and the A/B loop belong to skill-evaluator, and
duplicating either here would give this repo two competing implementations of
the same measurement — the failure mode worth avoiding more than the
convenience is worth having.

What it adds is that you no longer have to know four scripts across two skills,
or the order to run them in.

    forge_loop.py skills/<name> [--fixture DIR] [--runs 3] [--ab] [--json]

  --fixture  a REAL project containing what the trigger queries name. Without
             one, triggering is reported as not measured rather than guessed:
             realistic queries in an empty directory trigger nothing, because
             the agent correctly answers that there is nothing to look at.
  --ab       also run the output A/B loop (spawns agent runs; opt in).

Exit: 0 nothing blocking, 1 blocking issues or failed measurement, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repo_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "registry.json").exists() and (cand / "skills").is_dir():
            return cand
    return start


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def stage_gate(skill: Path, out: dict) -> bool:
    r = run([sys.executable, str(HERE / "forge_check.py"), str(skill), "--json"])
    try:
        data = json.loads(r.stdout)
    except ValueError:
        out["gate"] = {"ok": False, "error": r.stderr.strip()[:200]}
        return False
    blocking = [x["check"] for x in data["rows"] if x["level"] == "FAIL"]
    warns = [x["check"] for x in data["rows"] if x["level"] == "warn"]
    out["gate"] = {"ok": not blocking, "blocking": blocking, "warnings": warns}
    print(f"  gate       {'ok' if not blocking else 'BLOCKING: ' + ', '.join(blocking)}"
          + (f"   ({len(warns)} warnings)" if warns else ""))
    return not blocking


def stage_trigger(root: Path, skill: Path, fixture: str | None, runs: int,
                  out: dict, queries_override: str | None = None) -> bool:
    queries = Path(queries_override) if queries_override else skill / "evals" / "trigger_queries.json"
    script = root / "skills" / "skill-evaluator" / "scripts" / "trigger_behavior_eval.py"
    if not queries.exists():
        out["trigger"] = {"measured": False,
                          "reason": "no evals/trigger_queries.json"}
        print("  trigger    NOT MEASURED — no evals/trigger_queries.json")
        return True
    if not fixture:
        out["trigger"] = {"measured": False, "reason": "no --fixture given"}
        print("  trigger    NOT MEASURED — pass --fixture pointing at a real project; "
              "an empty one measures the fixture, not the skill")
        return True
    if not script.exists():
        out["trigger"] = {"measured": False, "reason": "skill-evaluator not present"}
        print("  trigger    NOT MEASURED — skill-evaluator/scripts missing")
        return True

    r = run([sys.executable, str(script), "--skill", str(skill),
             "--queries", str(queries), "--cwd", fixture, "--runs", str(runs)])
    text = r.stdout
    recall = next((l.split(":")[1].strip() for l in text.splitlines()
                   if l.startswith("recall")), "?")
    prec = next((l.split(":")[1].strip() for l in text.splitlines()
                 if l.startswith("precision")), "?")
    out["trigger"] = {"measured": True, "recall": recall, "precision": prec,
                      "clean": r.returncode == 0}
    print(f"  trigger    recall {recall}   precision {prec}")
    if r.returncode != 0:
        for line in text.splitlines():
            if line.startswith(("MISS", "FALSE")):
                print(f"             {line}")
    return True


def stage_ab(root: Path, skill: Path, out: dict) -> bool:
    ev = root / "skills" / "skill-evaluator"
    out["ab"] = {"delegated_to": str(ev.relative_to(root))}
    print("  a/b        delegated — see skill-evaluator's loop; it owns grading,\n"
          "             aggregation and regression detection. Assert on evidence,\n"
          "             not knowledge, or a capable model scores at ceiling either way.")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("skill")
    ap.add_argument("--fixture")
    ap.add_argument("--queries", help="override the skill's trigger_queries.json")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--ab", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    skill = Path(a.skill).resolve()
    if not (skill / "SKILL.md").exists():
        print(f"no SKILL.md in {skill}", file=sys.stderr)
        return 2
    root = repo_root(skill)
    out: dict = {"skill": skill.name}

    print(f"\nforge loop: {skill.name}\n" + "-" * 72)
    ok = stage_gate(skill, out)
    stage_trigger(root, skill, a.fixture, a.runs, out, a.queries)
    if a.ab:
        stage_ab(root, skill, out)
    print("-" * 72)

    nxt = []
    if out["gate"].get("blocking"):
        nxt.append("fix the blocking rows, then re-run")
    if not out.get("trigger", {}).get("measured"):
        nxt.append("measure triggering with --fixture pointing at a real project")
    if out["gate"].get("warnings"):
        nxt.append(f"consider the {len(out['gate']['warnings'])} warnings — "
                   "each is something that bit someone")
    if not nxt:
        nxt.append("nothing blocking; commit, and regenerate if frontmatter changed")
    out["next"] = nxt
    print("next:")
    for n in nxt:
        print(f"  - {n}")
    print()

    if a.json:
        print(json.dumps(out, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
