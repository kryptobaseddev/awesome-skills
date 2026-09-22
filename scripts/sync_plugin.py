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
        return 0
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit 1 rather than copying")
    a = ap.parse_args(argv)
    return sync(a.check)


if __name__ == "__main__":
    sys.exit(main())
