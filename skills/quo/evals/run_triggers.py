#!/usr/bin/env python3
"""Trigger eval for an installed skill: does an agent actually pick it up?

Usage (from anywhere, with the skill installed for Claude Code):
  python3 run_triggers.py --eval-set trigger_queries.json --skill ux-laws --fixtures files \
      --work /path/to/scratch --runs 3 --model claude-opus-5-5 --out results.json

Each query may name a "fixture" (a folder under --fixtures); it runs inside a fresh git copy of it, so
queries that mention src/routes/... or a Vue codebase meet a matching project.

--skill-dir PATH tests a skill version that is NOT installed: each run gets a throwaway HOME whose
.claude/skills/<skill> and .agents/skills/<skill> point at PATH, with every other entry symlinked to
the real home, so the installed copy is neither used nor modified.

Differences from skill-creator's run_eval.py (which inspects only the FIRST tool call and adds a temp
command beside the real skill): scans the whole tool sequence, counts any Skill/Read touching the
skill name as a trigger, runs inside a realistic project in plan mode (no edits), and stops early
once the skill fires, the run ends, or MAX_TOOLS tool calls pass without it.
"""
import argparse, json, os, select, shutil, subprocess, time
from concurrent.futures import ThreadPoolExecutor

MAX_TOOLS = 14


def fresh_copy(src, dst_root, home_path=None):
    """Give one run its own git copy of the fixture (and, with home_path, its own HOME that holds it there)."""
    import tempfile
    run_dir = tempfile.mkdtemp(prefix="run-", dir=dst_root)
    home = None
    if home_path:
        home = os.path.join(run_dir, "home")
        os.makedirs(home)
        for dot in (".claude", ".claude.json", ".agents", ".config", ".local", "Library"):
            real = os.path.join(os.path.expanduser("~"), dot)
            if os.path.exists(real):
                os.symlink(real, os.path.join(home, dot))
        dst = os.path.join(home, home_path)
    else:
        dst = os.path.join(run_dir, "repo")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst)
    subprocess.run("git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm fixture", shell=True, cwd=dst, check=True)
    return run_dir, dst, home


def overlay_home(home, skill, skill_dir):
    """Build HOME with the real dotfiles, except <skill> in the skills dirs points at skill_dir."""
    real_home = os.path.expanduser("~")
    for dot in (".claude.json", ".config", ".local", "Library"):
        real = os.path.join(real_home, dot)
        if os.path.exists(real) and not os.path.lexists(os.path.join(home, dot)):
            os.symlink(real, os.path.join(home, dot))
    for top in (".claude", ".agents"):
        real_top, fake_top = os.path.join(real_home, top), os.path.join(home, top)
        if os.path.islink(fake_top):
            os.unlink(fake_top)
        os.makedirs(fake_top, exist_ok=True)
        if not os.path.isdir(real_top):
            continue
        for name in os.listdir(real_top):
            if name != "skills" and not os.path.lexists(os.path.join(fake_top, name)):
                os.symlink(os.path.join(real_top, name), os.path.join(fake_top, name))
        fake_skills = os.path.join(fake_top, "skills")
        os.makedirs(fake_skills, exist_ok=True)
        real_skills = os.path.join(real_top, "skills")
        if os.path.isdir(real_skills):
            for name in os.listdir(real_skills):
                if name != skill and not os.path.lexists(os.path.join(fake_skills, name)):
                    os.symlink(os.path.join(real_skills, name), os.path.join(fake_skills, name))
        os.symlink(os.path.abspath(skill_dir), os.path.join(fake_skills, skill))


def run_one(query, skill, cwd, model, timeout, home=None, fixture=None, home_path=None, work=None, skill_dir=None):
    run_dir = None
    if fixture:
        run_dir, cwd, home = fresh_copy(fixture, work, home_path)
    if skill_dir:
        import tempfile
        if not run_dir:
            run_dir = tempfile.mkdtemp(prefix="run-", dir=work)
        if not home:
            home = os.path.join(run_dir, "home")
            os.makedirs(home, exist_ok=True)
        overlay_home(home, skill, skill_dir)
    try:
        return _run(query, skill, cwd, model, timeout, home)
    finally:
        if run_dir:
            subprocess.run(["pkill", "-f", run_dir], capture_output=True)   # dev servers an agent may have started
            shutil.rmtree(run_dir, ignore_errors=True)


def _run(query, skill, cwd, model, timeout, home=None):
    cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--disallowedTools", "Edit", "Write", "NotebookEdit"]
    if model:
        cmd += ["--model", model]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    if home:
        env["HOME"] = home
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cwd, env=env)
    tools, buf, start = [], "", time.time()
    try:
        while time.time() - start < timeout:
            if p.poll() is not None:
                buf += (p.stdout.read() or b"").decode("utf-8", "replace")
            else:
                r, _, _ = select.select([p.stdout], [], [], 1.0)
                if not r:
                    continue
                chunk = os.read(p.stdout.fileno(), 65536)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") == "assistant":
                    for c in ev.get("message", {}).get("content", []):
                        if c.get("type") != "tool_use":
                            continue
                        name, inp = c.get("name", ""), json.dumps(c.get("input", {}))
                        tools.append(name + (":" + c.get("input", {}).get("skill", "") if name == "Skill" else ""))
                        if (name == "Skill" and skill in inp) or (name == "Read" and f"/{skill}/" in inp):
                            return True, tools
                        if len(tools) >= MAX_TOOLS:
                            return False, tools
                elif ev.get("type") == "result":
                    return False, tools
            if p.poll() is not None and "\n" not in buf:
                break
        return False, tools
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--skill", required=True)
    ap.add_argument("--cwd", help="run every query here (ignores per-query fixtures)")
    ap.add_argument("--fixtures", help="folder holding the fixtures named by each query's 'fixture' field")
    ap.add_argument("--work", help="scratch folder for fixture copies (required with --fixtures)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=150)
    ap.add_argument("--model")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skill-dir", help="test this skill folder instead of the installed copy")
    a = ap.parse_args()
    items = json.load(open(a.eval_set))
    os.makedirs(a.work or ".", exist_ok=True)
    def job_args(it):
        fx = it.get("fixture")
        if a.cwd or not fx:
            return dict(cwd=a.cwd, skill_dir=a.skill_dir, work=a.work)
        return dict(cwd=None, fixture=os.path.join(a.fixtures, fx), home_path=it.get("home_path"), work=a.work, skill_dir=a.skill_dir)
    jobs = [(i, r) for i in range(len(items)) for r in range(a.runs)]
    res = {i: [] for i in range(len(items))}
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_one, items[i]["query"], a.skill, model=a.model, timeout=a.timeout, **job_args(items[i])): i for i, _ in jobs}
        for f in futs:
            i = futs[f]
            hit, tools = f.result()
            res[i].append({"hit": hit, "tools": tools})
            print(f"[{i}] {'HIT ' if hit else 'miss'} want={items[i]['should_trigger']} tools={tools[:6]}", flush=True)
    rows, correct = [], 0
    for i, it in enumerate(items):
        rate = sum(x["hit"] for x in res[i]) / len(res[i])
        ok = (rate >= 0.5) == it["should_trigger"]
        correct += ok
        rows.append({"query": it["query"], "should_trigger": it["should_trigger"], "trigger_rate": rate, "pass": ok, "runs": res[i]})
    summary = {"accuracy": f"{correct}/{len(items)}", "rows": rows}
    json.dump(summary, open(a.out, "w"), indent=2)
    print("ACCURACY", summary["accuracy"])
    for r in rows:
        if not r["pass"]:
            print("FAIL", r["should_trigger"], round(r["trigger_rate"], 2), r["query"][:110])


if __name__ == "__main__":
    main()
