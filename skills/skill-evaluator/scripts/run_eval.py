#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Run the A/B eval loop: for each test case, spawn N isolated runs in each
configuration (with_skill, without_skill, optionally old_skill) and capture
outputs, transcripts, and timing.

Executors:
  --executor print   (default) print the prompts and stop. Use this to drive
                                runs through your own orchestrator (e.g.
                                Claude Code Task tool, a CI runner).
  --executor api    call the Anthropic API directly. Requires ANTHROPIC_API_KEY.
                    Skills are passed to the model as a system-prompt prefix.
  --executor cli    shell out to `claude -p` if available.

For `--executor api` and `cli`, the agent has no access to local files —
this is sufficient for prose/decision-quality evals but not for skills that
demand local file I/O. For those, use `--executor print` and run through a
real Claude Code session (subagent isolation gives clean context).

The `--auto-loop` mode runs the full improvement loop:
  generate → run → grade → analyze → check regression → propose → iterate.

Usage:
  uv run run_eval.py --skill <path> --evals <evals.json> --workspace <dir> \\
                     --iteration 1 --runs 3 --executor print
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    LLMUnavailable,
    call_anthropic,
    die,
    iteration_dir,
    parse_skill,
    slugify,
    workspace_for,
    write_json,
    write_text,
)


def make_prompt_for_run(*, skill_path: Path | None, test_case: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for one run.

    When skill_path is None, no skill content is injected (baseline run).
    Otherwise the skill's SKILL.md body is injected as a system-prompt prefix.
    """
    user = test_case["prompt"]
    if skill_path is None:
        system = (
            "You are a helpful assistant. Respond directly to the user's "
            "request using only your built-in knowledge."
        )
        return system, user

    skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    system = (
        "You are a helpful assistant. The user has the following Agent Skill available, "
        "and you should apply it when it is relevant.\n\n"
        "=== BEGIN SKILL.md ===\n"
        f"{skill_md}\n"
        "=== END SKILL.md ===\n\n"
        f"If the skill mentions bundled scripts or references under {skill_path}, "
        "describe how you would invoke them rather than reading them yourself."
    )
    return system, user


def execute_run(
    *,
    config: str,
    skill_path: Path | None,
    test_case: dict,
    out_dir: Path,
    executor: str,
) -> dict:
    """Execute one run and write outputs/transcript.jsonl/timing.json. Return timing dict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "outputs").mkdir(exist_ok=True)
    system, user = make_prompt_for_run(skill_path=skill_path, test_case=test_case)

    write_text(out_dir / "prompt.txt",
               f"# CONFIG: {config}\n# CASE: {test_case['id']}\n\n"
               f"## SYSTEM\n{system}\n\n## USER\n{user}\n")

    started = time.time()
    if executor == "print":
        # Just print what *would* run. The user / orchestrator must populate
        # outputs/ and transcript.jsonl by hand or via a separate runner.
        print(f"[run] config={config} case={test_case['id']} → {out_dir}")
        timing = {"total_tokens": 0, "duration_ms": 0, "executor": "print", "skipped": True}
        write_json(out_dir / "timing.json", timing)
        return timing

    if executor == "api":
        try:
            resp = call_anthropic(system=system, user=user, max_tokens=4096)
        except LLMUnavailable as e:
            die(f"API executor unavailable: {e}")
        duration_ms = int((time.time() - started) * 1000)
        write_text(out_dir / "outputs" / "response.md", resp["text"])
        transcript = [{"role": "system", "content": system},
                      {"role": "user", "content": user},
                      {"role": "assistant", "content": resp["text"]}]
        (out_dir / "transcript.jsonl").write_text(
            "\n".join(json.dumps(r) for r in transcript) + "\n", encoding="utf-8"
        )
        timing = {
            "total_tokens": resp["usage"].get("total_tokens", 0),
            "input_tokens": resp["usage"].get("input_tokens", 0),
            "output_tokens": resp["usage"].get("output_tokens", 0),
            "duration_ms": duration_ms,
            "executor": "api",
        }
        write_json(out_dir / "timing.json", timing)
        return timing

    if executor == "cli":
        cmd = ["claude", "-p", "--output-format", "json"]
        full = f"<system>\n{system}\n</system>\n\n{user}"
        proc = subprocess.run(cmd, input=full, capture_output=True, text=True, timeout=600)
        duration_ms = int((time.time() - started) * 1000)
        if proc.returncode != 0:
            die(f"claude CLI failed for {config}/{test_case['id']}: {proc.stderr[:400]}")
        try:
            data = json.loads(proc.stdout)
            text = data.get("result", proc.stdout)
            usage = data.get("usage", {})
        except json.JSONDecodeError:
            text = proc.stdout
            usage = {}
        write_text(out_dir / "outputs" / "response.md", text)
        (out_dir / "transcript.jsonl").write_text(proc.stdout + "\n", encoding="utf-8")
        timing = {
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "duration_ms": duration_ms,
            "executor": "cli",
        }
        write_json(out_dir / "timing.json", timing)
        return timing

    die(f"unknown executor: {executor}")


def snapshot_skill(skill_path: Path, workspace: Path) -> Path | None:
    """Snapshot the current skill into <workspace>/skill-snapshot/.

    Returns the snapshot path or None if it already exists (snapshots are not
    overwritten — they capture the *previous* skill state).
    """
    dest = workspace / "skill-snapshot"
    if dest.exists():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    # Copy with stdlib to avoid extra deps
    import shutil
    shutil.copytree(skill_path, dest, dirs_exist_ok=True)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", required=True)
    ap.add_argument("--evals", required=False,
                    help="path to evals.json; defaults to <skill>/evals/evals.json")
    ap.add_argument("--evals-auto", action="store_true",
                    help="auto-generate evals.json by invoking generate_testcases.py first")
    ap.add_argument("--workspace", default=None, help="workspace directory")
    ap.add_argument("--iteration", type=int, default=1)
    ap.add_argument("--runs", type=int, default=3, help="repeated runs per case per config")
    ap.add_argument("--executor", choices=["print", "api", "cli"], default="print")
    ap.add_argument("--baseline", choices=["none", "no_skill", "old_skill", "both"],
                    default="no_skill",
                    help="baseline configuration(s) to compare against the with-skill runs")
    ap.add_argument("--auto-loop", action="store_true",
                    help="run the full generate→eval→grade→analyze→regression→propose loop")
    ap.add_argument("--max-iterations", type=int, default=5)
    ap.add_argument("--apply-proposals", action="store_true",
                    help="auto-apply propose_improvements output (NOT recommended)")
    args = ap.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    try:
        skill = parse_skill(skill_path)
    except Exception as e:
        die(str(e))

    workspace = workspace_for(skill_path, args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    print(f"workspace: {workspace}")

    if args.auto_loop:
        return _auto_loop(args, skill, workspace)

    return _single_iteration(args, skill, workspace, args.iteration)


def _ensure_evals(args, skill, workspace: Path) -> Path:
    if args.evals:
        return Path(args.evals).expanduser().resolve()
    default = skill.path / "evals" / "evals.json"
    if default.exists() and not args.evals_auto:
        return default
    # Auto-generate
    print(f"generating evals.json via generate_testcases.py …")
    cmd = [
        sys.executable, str(Path(__file__).parent / "generate_testcases.py"),
        "--skill", str(skill.path),
        "--out", str(default),
        "--count", "6",
    ]
    subprocess.run(cmd, check=True)
    return default


def _single_iteration(args, skill, workspace: Path, iteration: int) -> int:
    evals_path = _ensure_evals(args, skill, workspace)
    evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
    iter_dir = iteration_dir(workspace, iteration)
    iter_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot the previous version on iteration > 1 if no snapshot exists yet
    if iteration > 1 and not (workspace / "skill-snapshot").exists():
        prev_skill_dir = workspace / f"iteration-{iteration-1}" / "skill-as-run"
        if prev_skill_dir.exists():
            import shutil
            shutil.copytree(prev_skill_dir, workspace / "skill-snapshot", dirs_exist_ok=True)

    # Save a copy of the skill as it was run, for reproducibility
    import shutil
    shutil.copytree(skill.path, iter_dir / "skill-as-run", dirs_exist_ok=True)

    # Pick baseline configs
    configs: list[tuple[str, Path | None]] = [("with_skill", skill.path)]
    if args.baseline in ("no_skill", "both"):
        configs.append(("without_skill", None))
    if args.baseline in ("old_skill", "both"):
        snap = workspace / "skill-snapshot"
        if snap.exists():
            configs.append(("old_skill", snap))
        else:
            print("warn: --baseline old_skill requested but no skill-snapshot/ found", file=sys.stderr)

    timings: list[dict] = []
    for case in evals_data["evals"]:
        case_dir = iter_dir / f"eval-{slugify(case['id'])}"
        # Stage input files if present
        for f in case.get("files") or []:
            src = (skill.path / f) if not Path(f).is_absolute() else Path(f)
            if src.exists():
                dst = case_dir / "inputs" / Path(f).name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        for cfg_name, cfg_skill in configs:
            for run_i in range(args.runs):
                out_dir = case_dir / cfg_name / f"run-{run_i+1}"
                t = execute_run(
                    config=cfg_name, skill_path=cfg_skill,
                    test_case=case, out_dir=out_dir, executor=args.executor,
                )
                timings.append({"case": case["id"], "config": cfg_name, "run": run_i + 1, **t})

    write_json(iter_dir / "_timings.json", timings)
    print(f"\nDone. Wrote runs to {iter_dir}")
    print("Next steps:")
    print(f"  uv run grade_assertions.py --workspace {iter_dir} --evals {evals_path}")
    print(f"  uv run aggregate_benchmarks.py --workspace {iter_dir}")
    print(f"  uv run analyze_patterns.py --workspace {iter_dir}")
    if iteration > 1:
        print(f"  uv run detect_regression.py "
              f"--baseline {iteration_dir(workspace, iteration-1)}/benchmark.json "
              f"--current {iter_dir}/benchmark.json")
    return 0


def _auto_loop(args, skill, workspace: Path) -> int:
    print(f"auto-loop: up to {args.max_iterations} iterations")
    prev_benchmark: dict | None = None
    no_improvement_streak = 0
    for it in range(1, args.max_iterations + 1):
        print(f"\n=== iteration {it} ===")
        rc = _single_iteration(args, skill, workspace, it)
        if rc != 0:
            return rc
        iter_dir = iteration_dir(workspace, it)

        # Drive the rest of the pipeline
        scripts_dir = Path(__file__).parent
        evals_path = _ensure_evals(args, skill, workspace)
        subprocess.run([sys.executable, str(scripts_dir / "grade_assertions.py"),
                        "--workspace", str(iter_dir), "--evals", str(evals_path)])
        subprocess.run([sys.executable, str(scripts_dir / "aggregate_benchmarks.py"),
                        "--workspace", str(iter_dir)])
        patterns = subprocess.run([sys.executable, str(scripts_dir / "analyze_patterns.py"),
                                   "--workspace", str(iter_dir)])
        if it > 1:
            subprocess.run([sys.executable, str(scripts_dir / "detect_regression.py"),
                            "--baseline", str(iteration_dir(workspace, it-1) / "benchmark.json"),
                            "--current", str(iter_dir / "benchmark.json"),
                            "--eval-results", str(iter_dir)])
        subprocess.run([sys.executable, str(scripts_dir / "propose_improvements.py"),
                        "--skill", str(skill.path),
                        "--workspace", str(iter_dir)])

        # Convergence check
        bench_path = iter_dir / "benchmark.json"
        if not bench_path.exists():
            print("warn: no benchmark.json produced — stopping auto-loop")
            return 1
        bench = json.loads(bench_path.read_text())
        with_rate = bench.get("run_summary", {}).get("with_skill", {}).get("pass_rate", {}).get("mean", 0.0)
        with_std = bench.get("run_summary", {}).get("with_skill", {}).get("pass_rate", {}).get("stddev", 0.0)
        print(f"iteration-{it} with_skill pass_rate={with_rate:.3f} ± {with_std:.3f}")
        if prev_benchmark is not None:
            prev_rate = prev_benchmark.get("run_summary", {}).get("with_skill", {}).get("pass_rate", {}).get("mean", 0.0)
            improvement = with_rate - prev_rate
            if improvement <= max(with_std, 1e-6):
                no_improvement_streak += 1
            else:
                no_improvement_streak = 0
            if no_improvement_streak >= 2:
                print("auto-loop: two consecutive iterations without meaningful improvement — stopping")
                return 0
        prev_benchmark = bench
        if with_rate >= 0.95:
            print("auto-loop: pass rate ≥ 95% — stopping")
            return 0

        if args.apply_proposals:
            proposal = iter_dir / "proposal.md"
            print(f"warn: --apply-proposals is set. Manual review of {proposal} still recommended.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
