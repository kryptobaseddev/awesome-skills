#!/usr/bin/env python3
"""One gate for a skill in this repo: everything CI and the hooks will check,
plus the things they do not check and people therefore get wrong.

    forge_check.py skills/<name> [--json] [--fix-hints]

Runs the structural validator, the progressive-disclosure rule and the body
audit, then adds the checks that cost real time to discover:

  * which README category the skill will actually land in, and which rule put it
    there -- explicit `metadata.category` beats matching, and the matching rules
    are order-sensitive, so a `mobile` or `automation` tag silently hijacks a
    frontend skill
  * executable bits AS GIT RECORDS THEM -- this repo sets core.fileMode=false,
    so a `chmod +x` on disk never reaches a commit and a script the SKILL.md
    tells the agent to run lands non-executable
  * generated-file freshness, which is a hard CI gate
  * description headroom and whether it states a boundary as well as a trigger
  * the skill's own selftest, if it ships one

Exit: 0 clean, 1 problems found, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


def repo_root(start: Path) -> Path:
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / "registry.json").exists() and (cand / "skills").is_dir():
            return cand
    return p


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []

    def add(self, level: str, check: str, detail: str):
        self.rows.append((level, check, detail))

    ok = lambda self, c, d="": self.add("ok", c, d)          # noqa: E731
    warn = lambda self, c, d="": self.add("warn", c, d)      # noqa: E731
    fail = lambda self, c, d="": self.add("FAIL", c, d)      # noqa: E731

    @property
    def failed(self):
        return any(r[0] == "FAIL" for r in self.rows)


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def frontmatter(skill_md: Path):
    raw = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if not m:
        return None, raw, raw
    try:
        return yaml.safe_load(m.group(1)) or {}, m.group(2), m.group(1)
    except yaml.YAMLError:
        return None, m.group(2), m.group(1)


# ---------------------------------------------------------------- checks
def check_delegated(root: Path, skill: Path, rep: Report):
    """The three tools this repo already has. Run them, do not reimplement."""
    v = root / "skills" / "skill-validator" / "scripts"
    for name, script, hard in (("structural validator", "validate.py", True),
                               ("progressive disclosure", "check_depth.py", True),
                               ("body audit", "audit_body.py", False)):
        p = v / script
        if not p.exists():
            rep.warn(name, f"{script} not found")
            continue
        r = run([sys.executable, str(p), str(skill)])
        if r.returncode == 0:
            rep.ok(name)
        elif hard:
            tail = [ln for ln in r.stdout.splitlines() if "ERROR" in ln or "✗" in ln]
            rep.fail(name, "; ".join(tail[:3]) or f"exit {r.returncode}")
        else:
            rep.warn(name, f"exit {r.returncode}")


def check_category(root: Path, skill: Path, fm: dict, rep: Report):
    cfg = root / "skills" / "skill-validator" / "config" / "categories.yml"
    if not cfg.exists():
        return
    cats = yaml.safe_load(cfg.read_text())
    explicit = (fm.get("metadata") or {}).get("category") or fm.get("category")
    if explicit:
        known = {c.get("slug") for c in cats["categories"]}
        if explicit in known:
            rep.ok("category", f"explicit '{explicit}' -- immune to rule order")
        else:
            rep.fail("category", f"'{explicit}' matches no slug; it falls through "
                                 "to rule matching SILENTLY. Known: "
                                 + ", ".join(sorted(x for x in known if x)))
        return
    meta = fm.get("metadata") or {}
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    hay = f"{fm.get('name','')} {fm.get('description','')} {' '.join(tags)}".lower()
    for c in cats["categories"]:
        m = c.get("match", {})
        hit = next((f"tag '{t}'" for t in m.get("tags", []) if t in tags), None) \
            or next((f"name contains '{n}'" for n in m.get("name_contains", [])
                     if n in fm.get("name", "")), None) \
            or next((f"keyword '{k}'" for k in m.get("keywords", [])
                     if re.search(rf"(?:^|[^a-z0-9]){re.escape(k)}(?:[^a-z0-9]|$)", hay)), None)
        if hit:
            rep.warn("category", f"resolved by {hit} -> '{c['slug']}'. Rule order "
                                 "decides this; set metadata.category to pin it")
            return
    rep.warn("category", "no rule matched -> falls back to 'other'")


def check_exec_bits(root: Path, skill: Path, body: str, rep: Report):
    """The bit only matters for DIRECT invocation.

    `bash scripts/x.sh`, `node scripts/x.js` and `python3 scripts/x.py` all run
    a mode-644 file perfectly well -- the interpreter opens it, the kernel never
    execs it. Only `scripts/x` or `./scripts/x` needs +x. Flagging the
    interpreter-prefixed form produces exactly the noise that gets a linter
    ignored, so this looks for direct invocation only.

    It still matters, because core.fileMode=false means a local chmod never
    reaches the commit.
    """
    direct: set[str] = set()
    for line in body.splitlines():
        # inside a fenced block or not, a command line starting with the path
        stripped = line.strip().lstrip("$ ").strip()
        m = re.match(r"\.?/?(?:skills/([\w-]+)/)?(scripts/[\w.-]+)(?:\s|$)", stripped)
        if not m:
            continue
        owner, path = m.group(1), m.group(2)
        if owner and owner != skill.name:
            continue          # a sibling skill's script is the sibling's problem
        if re.search(r"\.(md|json|ya?ml|txt)$", path):
            continue
        direct.add(path)

    if not direct:
        rep.ok("executable bits", "no script is invoked directly (interpreter-prefixed "
                                  "invocations run fine at 644)")
        return
    rel = skill.relative_to(root)
    r = run(["git", "ls-files", "-s", str(rel / "scripts")], cwd=root)
    modes = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            modes[str(Path(parts[3]).relative_to(rel))] = parts[0]
    missing = [s for s in sorted(direct) if s in modes and modes[s] != "100755"]
    untracked = [s for s in sorted(direct) if s not in modes]
    if missing:
        rep.fail("executable bits", "invoked directly but not +x in git: "
                 + ", ".join(missing) + "  -> git update-index --chmod=+x "
                 + " ".join(f"{rel}/{s}" for s in missing))
    elif untracked:
        rep.warn("executable bits", "not tracked yet: " + ", ".join(untracked))
    else:
        rep.ok("executable bits", f"{len(direct)} directly-invoked script(s) are +x")


def check_generated(root: Path, rep: Report):
    b = root / "scripts" / "build_registry.py"
    if not b.exists():
        return
    r = run([sys.executable, str(b), "--check"], cwd=root)
    if r.returncode == 0:
        rep.ok("generated files", "README + registry current")
    else:
        rep.fail("generated files", "stale -- CI gates on this. Run: "
                                    "python3 scripts/build_registry.py")


def check_description(fm: dict, cfg: dict, rep: Report):
    d = fm.get("description") or ""
    raw_cap = (cfg.get("description") or {}).get("max_length")
    # the config nests some limits as {value, severity} and states others bare
    cap = raw_cap.get("value") if isinstance(raw_cap, dict) else (raw_cap or 1024)
    n = len(d)
    if n > cap:
        rep.fail("description", f"{n} chars, over the {cap} limit")
    elif n > cap - 30:
        rep.warn("description", f"{n}/{cap} chars -- no room to add a trigger later")
    else:
        rep.ok("description", f"{n}/{cap} chars")
    if not re.search(r"\buse (when|whenever|for)\b", d, re.I):
        rep.warn("description trigger", "no 'Use when …' clause; this is the field "
                                        "that decides whether the skill ever loads")
    if not re.search(r"\bnot for\b|\beven if\b|\bdo not use\b", d, re.I):
        rep.warn("description boundary", "states no boundary or near-miss. Skills "
                                         "undertrigger AND poach neighbours without one")


def check_evals(skill: Path, rep: Report):
    ev = skill / "evals"
    tq, ej = ev / "trigger_queries.json", ev / "evals.json"
    if not ev.is_dir():
        rep.warn("evals", "no evals/ -- nothing can measure this skill")
        return
    if tq.exists():
        try:
            q = json.loads(tq.read_text())
            pos = sum(1 for x in q if x.get("should_trigger"))
            neg = len(q) - pos
            (rep.ok if neg >= 5 else rep.warn)(
                "trigger queries", f"{len(q)} queries, {pos} positive / {neg} negative"
                + ("" if neg >= 5 else " -- negatives are what catch poaching"))
        except ValueError as e:
            rep.fail("trigger queries", f"invalid JSON: {e}")
    else:
        rep.warn("trigger queries", "absent")
    if ej.exists():
        rep.ok("output evals", "evals.json present")
    else:
        rep.warn("output evals", "absent")


def check_selftest(skill: Path, rep: Report):
    st = skill / "scripts" / "selftest.py"
    if not st.exists():
        if (skill / "scripts").is_dir():
            rep.warn("selftest", "ships scripts but no selftest.py -- a check that "
                                 "cannot fail its own negative case is a comment")
        return
    r = run([sys.executable, str(st)])
    (rep.ok if r.returncode == 0 else rep.fail)(
        "selftest", "passes" if r.returncode == 0 else r.stdout.strip().splitlines()[-1:][0]
        if r.stdout.strip() else f"exit {r.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    skill = Path(a.skill).resolve()
    if not (skill / "SKILL.md").exists():
        print(f"no SKILL.md in {skill}", file=sys.stderr)
        return 2
    root = repo_root(skill)
    fm, body, _ = frontmatter(skill / "SKILL.md")
    rep = Report()
    if fm is None:
        rep.fail("frontmatter", "missing or unparseable YAML")
        fm = {}

    cfgp = root / "skills" / "skill-validator" / "config" / "default.yml"
    cfg = yaml.safe_load(cfgp.read_text()) if cfgp.exists() else {}

    check_delegated(root, skill, rep)
    check_description(fm, cfg, rep)
    check_category(root, skill, fm, rep)
    check_exec_bits(root, skill, body, rep)
    check_evals(skill, rep)
    check_selftest(skill, rep)
    check_generated(root, rep)

    if a.json:
        print(json.dumps({"skill": skill.name,
                          "rows": [{"level": l, "check": c, "detail": d}
                                   for l, c, d in rep.rows],
                          "ok": not rep.failed}, indent=1))
    else:
        print(f"\nforge check: {skill.name}\n" + "-" * 72)
        for level, check, detail in rep.rows:
            mark = {"ok": "  ok  ", "warn": " warn ", "FAIL": " FAIL "}[level]
            print(f"{mark} {check:<24} {detail}")
        n_f = sum(1 for r in rep.rows if r[0] == "FAIL")
        n_w = sum(1 for r in rep.rows if r[0] == "warn")
        print("-" * 72)
        print(f"{n_f} blocking, {n_w} worth a look\n")
        if not rep.failed and n_w:
            print("Warnings do not block, but every one of them is something that "
                  "bit someone once.\n")
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
