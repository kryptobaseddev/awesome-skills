#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Grade per-run outputs against the assertions in evals.json.

Hybrid grader:
  - Programmatic checks for assertions that look mechanical:
    * "valid JSON" / "is valid YAML"
    * "file exists at ..." / "no file named ..."
    * "the output contains 'literal'" / "matches regex /.../"
    * "exit code 0" / "the run did not error"
    * "exactly N <noun>" counts (rough heuristic)
  - LLM judge for everything else, with REQUIRED evidence per assertion.

Writes <case-dir>/<config>/<run>/grading.json. Always records evidence,
never an opinion. PASS requires concrete textual or file-based support.

Usage:
  uv run grade_assertions.py --workspace <iter-dir> --evals <evals.json>
                             [--judge hybrid|llm|script]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    LLMUnavailable,
    call_anthropic,
    die,
    extract_json_block,
    read_json,
    slugify,
    write_json,
)


PROGRAMMATIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("valid_json", re.compile(r"\bvalid\s+JSON\b", re.IGNORECASE)),
    ("valid_yaml", re.compile(r"\bvalid\s+YAML\b", re.IGNORECASE)),
    ("file_exists", re.compile(r"\bfile\s+(?:named\s+)?[\"'`]?([\w./\-]+\.[\w]+)[\"'`]?\s+exists", re.IGNORECASE)),
    ("contains_literal", re.compile(r"contains\s+(?:the\s+(?:literal\s+)?string\s+|the\s+phrase\s+)?[\"`']([^\"`']{2,80})[\"`']", re.IGNORECASE)),
    ("regex_match", re.compile(r"matches\s+regex\s+/([^/]+)/", re.IGNORECASE)),
    ("not_invoked", re.compile(r"\b(?:skill|it)\s+is\s+not\s+(?:invoked|triggered|loaded|activated)\b", re.IGNORECASE)),
    ("invoked", re.compile(r"\b(?:skill|it)\s+is\s+invoked\b", re.IGNORECASE)),
    ("count_exactly", re.compile(r"\b(?:exactly|precisely)\s+(\d+)\b", re.IGNORECASE)),
    ("at_least", re.compile(r"\bat\s+least\s+(\d+)\b", re.IGNORECASE)),
]


def gather_outputs(run_dir: Path) -> tuple[str, dict[str, str]]:
    """Return (concatenated_text, per_filename_text) for files in outputs/."""
    out_dir = run_dir / "outputs"
    if not out_dir.exists():
        return "", {}
    per_file: dict[str, str] = {}
    chunks: list[str] = []
    for f in sorted(out_dir.rglob("*")):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = f"<binary {f.name} {f.stat().st_size}b>"
        rel = str(f.relative_to(out_dir))
        per_file[rel] = text
        chunks.append(f"--- {rel} ---\n{text}")
    return "\n\n".join(chunks), per_file


def programmatic_check(assertion: str, *, output_text: str, per_file: dict[str, str],
                      run_dir: Path, should_trigger: bool, transcript_text: str) -> dict | None:
    """Try to grade an assertion purely programmatically. Return None if not applicable."""
    a_lower = assertion.lower()

    for kind, pat in PROGRAMMATIC_PATTERNS:
        m = pat.search(assertion)
        if not m:
            continue
        if kind == "valid_json":
            for fname, content in per_file.items():
                if fname.endswith(".json"):
                    try:
                        json.loads(content)
                        return {"text": assertion, "passed": True, "method": "script:valid_json",
                                "evidence": f"{fname} parses as JSON"}
                    except json.JSONDecodeError as e:
                        return {"text": assertion, "passed": False, "method": "script:valid_json",
                                "evidence": f"{fname} failed to parse: {e}"}
            return {"text": assertion, "passed": False, "method": "script:valid_json",
                    "evidence": "no .json file produced in outputs/"}
        if kind == "valid_yaml":
            try:
                import yaml  # type: ignore
            except ImportError:
                return None  # fall through to LLM
            for fname, content in per_file.items():
                if fname.endswith((".yaml", ".yml")):
                    try:
                        yaml.safe_load(content)
                        return {"text": assertion, "passed": True, "method": "script:valid_yaml",
                                "evidence": f"{fname} parses as YAML"}
                    except yaml.YAMLError as e:
                        return {"text": assertion, "passed": False, "method": "script:valid_yaml",
                                "evidence": f"{fname} failed to parse: {e}"}
            return None
        if kind == "file_exists":
            target = m.group(1)
            hits = [k for k in per_file if k.endswith(target) or k == target]
            return {
                "text": assertion,
                "passed": bool(hits),
                "method": "script:file_exists",
                "evidence": f"found {hits[0]}" if hits else f"no file matching '{target}' in outputs/",
            }
        if kind == "contains_literal":
            literal = m.group(1)
            ok = literal in output_text
            return {
                "text": assertion, "passed": ok, "method": "script:contains_literal",
                "evidence": f"'{literal}' {'present' if ok else 'absent'} in output",
            }
        if kind == "regex_match":
            try:
                rx = re.compile(m.group(1))
            except re.error as e:
                return {"text": assertion, "passed": False, "method": "script:regex_match",
                        "evidence": f"invalid regex /{m.group(1)}/: {e}"}
            ok = bool(rx.search(output_text))
            return {"text": assertion, "passed": ok, "method": "script:regex_match",
                    "evidence": f"regex /{m.group(1)}/ {'matched' if ok else 'did not match'}"}
        if kind in ("not_invoked", "invoked"):
            # Look for a Skill tool invocation in transcript.jsonl
            invoked = "skill" in transcript_text.lower() and (
                '"tool_use"' in transcript_text or "Skill(" in transcript_text or
                '"name": "Skill"' in transcript_text
            )
            expected_invoked = kind == "invoked"
            passed = invoked == expected_invoked
            return {
                "text": assertion, "passed": passed, "method": f"script:{kind}",
                "evidence": (
                    f"transcript shows skill {'invoked' if invoked else 'not invoked'} "
                    f"(expected: {'invoked' if expected_invoked else 'not invoked'})"
                ),
            }

    return None  # let the LLM grade it


def llm_grade(*, assertion: str, output_text: str, expected_output: str,
              case_prompt: str) -> dict:
    if not output_text.strip():
        return {"text": assertion, "passed": False, "method": "llm",
                "evidence": "no output produced (empty outputs/)"}
    system = (
        "You are a rigorous grader of LLM agent outputs. For each assertion, you "
        "decide PASS or FAIL based ONLY on evidence in the agent's output. You "
        "NEVER give the benefit of the doubt — a label without substance is FAIL. "
        "You quote or reference the output as evidence. You reply with strict JSON."
    )
    truncated_out = output_text[:6000]
    user = (
        f"## Case prompt\n{case_prompt}\n\n"
        f"## Expected output (human summary)\n{expected_output}\n\n"
        f"## Assertion to grade\n{assertion}\n\n"
        f"## Agent output\n```\n{truncated_out}\n```\n\n"
        "Reply in this exact JSON shape:\n"
        '{ "passed": true|false, "evidence": "concrete quote or reference, max 240 chars" }'
    )
    try:
        resp = call_anthropic(system=system, user=user, max_tokens=800)
    except LLMUnavailable as e:
        return {"text": assertion, "passed": False, "method": "llm-unavailable",
                "evidence": f"LLM grading unavailable: {e}"}
    try:
        data = extract_json_block(resp["text"])
    except Exception:
        return {"text": assertion, "passed": False, "method": "llm",
                "evidence": f"could not parse LLM grading reply: {resp['text'][:200]}"}
    return {
        "text": assertion,
        "passed": bool(data.get("passed")),
        "method": "llm",
        "evidence": str(data.get("evidence", ""))[:500],
    }


def grade_run(*, run_dir: Path, case: dict, judge: str) -> dict:
    output_text, per_file = gather_outputs(run_dir)
    transcript_text = ""
    t_path = run_dir / "transcript.jsonl"
    if t_path.exists():
        transcript_text = t_path.read_text(encoding="utf-8", errors="replace")

    timing = {}
    if (run_dir / "timing.json").exists():
        timing = read_json(run_dir / "timing.json")

    if timing.get("skipped"):
        return {
            "case_id": case["id"],
            "skipped": True,
            "reason": "run was executed in print-mode (executor=print); populate outputs/ then re-grade",
            "assertion_results": [],
            "summary": {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0},
        }

    results: list[dict] = []
    for assertion in case.get("assertions", []):
        out = None
        if judge in ("script", "hybrid"):
            out = programmatic_check(
                assertion, output_text=output_text, per_file=per_file,
                run_dir=run_dir, should_trigger=case.get("should_trigger", True),
                transcript_text=transcript_text,
            )
        if out is None and judge in ("hybrid", "llm"):
            out = llm_grade(
                assertion=assertion, output_text=output_text,
                expected_output=case.get("expected_output", ""),
                case_prompt=case.get("prompt", ""),
            )
        if out is None:
            # script-only judge didn't match
            out = {"text": assertion, "passed": False, "method": "script-skipped",
                   "evidence": "no programmatic rule matched; pass --judge hybrid or llm to grade"}
        results.append(out)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "case_id": case["id"],
        "assertion_results": results,
        "summary": {
            "passed": passed, "failed": total - passed, "total": total,
            "pass_rate": (passed / total) if total else 0.0,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True, help="iteration-N directory")
    ap.add_argument("--evals", required=True)
    ap.add_argument("--judge", choices=["script", "llm", "hybrid"], default="hybrid")
    args = ap.parse_args()

    iter_dir = Path(args.workspace).expanduser().resolve()
    evals = json.loads(Path(args.evals).read_text(encoding="utf-8"))

    case_index = {c["id"]: c for c in evals["evals"]}
    summary_rows: list[dict] = []
    for case_dir in sorted(iter_dir.glob("eval-*")):
        case_slug = case_dir.name[len("eval-"):]
        # Find the matching case (id may have been slugified)
        case = next(
            (c for c in evals["evals"] if slugify(c["id"]) == case_slug),
            None,
        )
        if case is None:
            print(f"warn: no eval case for dir {case_dir.name}", file=sys.stderr)
            continue
        for cfg_dir in sorted(case_dir.iterdir()):
            if not cfg_dir.is_dir() or cfg_dir.name == "inputs":
                continue
            for run_dir in sorted(cfg_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                grading = grade_run(run_dir=run_dir, case=case, judge=args.judge)
                write_json(run_dir / "grading.json", grading)
                summary_rows.append({
                    "case": case["id"], "config": cfg_dir.name, "run": run_dir.name,
                    **grading["summary"],
                })

    write_json(iter_dir / "_grading_summary.json", summary_rows)
    print(f"graded {len(summary_rows)} runs → {iter_dir}/_grading_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
