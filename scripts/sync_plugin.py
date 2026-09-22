#!/usr/bin/env python3
"""Keep the plugin's copy of a skill identical to the skill.

A plugin has to CONTAIN the skills it ships. `deuxui-plugin/skills/deuxui` was
a symlink into `skills/deuxui`, which reads correctly in the working tree and
does not survive installation: the installer copies the directory, the symlink is
not followed, and the installed plugin arrives with an empty `skills/` folder.

The consequence is quiet and total. Every `/ux-*` command says "invoke the
deuxui skill" and the plugin ships none; the PostToolUse check and the PreToolUse
phase gate point at `${CLAUDE_PLUGIN_ROOT}/skills/deuxui/scripts/...`, which does
not exist, so both hooks silently do nothing. Nothing errors. It simply never
runs -- which is the failure mode this whole skill exists to argue against.

So the copy is real and this keeps it honest:

    python3 scripts/sync_plugin.py            # copy, report what moved
    python3 scripts/sync_plugin.py --check    # exit 1 if the copy has drifted

`--check` runs in the pre-commit hook and in CI, so the two cannot diverge
without somebody being told.
"""
from __future__ import annotations
import argparse
import filecmp
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAIRS = [(ROOT / "skills" / "deuxui", ROOT / "deuxui-plugin" / "skills" / "deuxui")]
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
SKIP_SUFFIX = {".pyc", ".pyo"}
# Build output and local scratch never ship.
SKIP_NAMES = {".DS_Store"}


def files_of(root: Path) -> dict:
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.name in SKIP_NAMES or p.suffix in SKIP_SUFFIX:
            continue
        if p.is_file():
            out[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def versions() -> tuple[str, str, list]:
    """(skill version, plugin version, complaints). They ship together, so they
    carry the same number -- a plugin at 2.1.0 wrapping a skill at 4.3.1 tells
    the person installing it nothing true."""
    sk = (ROOT / "skills" / "deuxui" / "SKILL.md").read_text()
    m = re.search(r'^\s*version:\s*"([^"]+)"', sk, re.M)
    sv = m.group(1) if m else "?"
    pj = ROOT / "deuxui-plugin" / ".claude-plugin" / "plugin.json"
    pv = json.loads(pj.read_text()).get("version", "?")
    return sv, pv, ([] if sv == pv else
                    [f"the skill is {sv} and the plugin says {pv}; they install "
                     f"together and must carry the same version"])


def sync(check: bool) -> int:
    problems, moved = [], 0
    for src, dst in PAIRS:
        if dst.is_symlink():
            if check:
                problems.append(f"{dst.relative_to(ROOT)} is a symlink. It will not "
                                f"survive installation: the installed plugin arrives "
                                f"with an empty skills/ directory and its hooks point "
                                f"at scripts that are not there.")
                continue
            dst.unlink()
        want, have = files_of(src), files_of(dst)
        missing = sorted(set(want) - set(have))
        extra = sorted(set(have) - set(want))
        differing = sorted(k for k in set(want) & set(have) if want[k] != have[k])
        if check:
            for k in missing:
                problems.append(f"missing from the plugin copy: {k}")
            for k in extra:
                problems.append(f"in the plugin copy but not in the skill: {k}")
            for k in differing:
                problems.append(f"differs: {k}")
            continue
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, symlinks=False,
                        ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc", "*.pyo",
                                                      ".DS_Store"))
        moved = len(files_of(dst))
        sys.stderr.write(f"copied {src.relative_to(ROOT)} -> "
                         f"{dst.relative_to(ROOT)}  ({moved} files)\n")

    sv, pv, vprob = versions()
    problems += vprob
    if not check and vprob:
        pj = ROOT / "deuxui-plugin" / ".claude-plugin" / "plugin.json"
        d = json.loads(pj.read_text())
        d["version"] = sv
        pj.write_text(json.dumps(d, indent=2) + "\n")
        sys.stderr.write(f"plugin version {pv} -> {sv}\n")
        problems = [p for p in problems if p not in vprob]

    if check:
        if problems:
            sys.stderr.write("\nthe plugin's copy of the skill has drifted:\n")
            for p in problems[:20]:
                sys.stderr.write(f"  {p}\n")
            if len(problems) > 20:
                sys.stderr.write(f"  ... and {len(problems) - 20} more\n")
            sys.stderr.write("\n  python3 scripts/sync_plugin.py\n")
            return 1
        sys.stderr.write(f"plugin copy is identical to the skill (v{sv})\n")

    # Checked on both paths, because a copy can be perfectly in sync and still ship a
    # command citing a rule nobody wrote.
    cites = cited_ids(PAIRS[0][0], ROOT / "deuxui-plugin" / "commands")
    if cites:
        sys.stderr.write("\nplugin commands cite IDs the skill does not define:\n")
        for c in cites:
            sys.stderr.write(f"  {c}\n")
        return 1
    sys.stderr.write(f"plugin commands cite only IDs the skill defines "
                     f"({len(list((ROOT / 'deuxui-plugin' / 'commands').glob('*.md')))} "
                     f"command file(s))\n")
    return 0


def cited_ids(skill: Path, commands: Path) -> list:
    """Rule and detector IDs cited by a plugin command that the skill does not define.

    `lint_rules.py` proves no prose inside the skill invents a rule ID. The plugin's
    slash commands are outside the skill, so nothing checked them -- and they are the
    text an agent reads first, which makes an invented ID there worse than one buried
    in a reference. A command that says `S-CRAFT-RYTHM` sends the agent looking for a
    detector that does not exist and, finding nothing, to report the check as passing.
    """
    import yaml
    ids = set()

    def harvest(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and re.fullmatch(r"[SRAM]-[A-Z0-9][A-Z0-9-]*", k):
                    ids.add(k)
                if k == "id" and isinstance(v, str):
                    ids.add(v)
                harvest(v)
        elif isinstance(o, list):
            for x in o:
                harvest(x)

    for name in ("registry.yaml", "detectors.yaml", "thresholds.yaml"):
        q = skill / "references" / "rules" / name
        if q.exists():
            try:
                harvest(yaml.safe_load(q.read_text()))
            except yaml.YAMLError:
                pass
    if not ids:
        return [f"{skill.name}: no rule or detector IDs could be read, so the commands "
                f"cannot be checked against them"]

    # A trailing `-*` is a family, not an ID: `S-CONTRACT-*` names the whole group.
    pat = re.compile(r"\b([SRAM]-[A-Z0-9][A-Z0-9-]{2,}|"
                     r"(?:A11Y|LAY|NUM|GOV|CONTENT|UX|VIS|FORM|COMP|STATE|PERF|TRUST"
                     r"|AI|MEASURE|QA|CTX|NAV|AND|IOS|LAW)-\d{3})\b")
    bad = []
    for f in sorted(commands.glob("*.md")):
        body = f.read_text(errors="replace")
        for m in sorted(set(pat.findall(body))):
            if m in ids:
                continue
            if re.search(re.escape(m) + r"-\*", body):
                continue                      # a family wildcard, not a claim about one ID
            bad.append(f"commands/{f.name} cites {m}, which is not in the skill's "
                       f"registry or detector table")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit 1 rather than copying")
    a = ap.parse_args(argv)
    return sync(a.check)


if __name__ == "__main__":
    sys.exit(main())
