#!/usr/bin/env python3
"""
validate_plugin.py — one command to check a plugin (and its marketplace) is sound.

Layers:
  1. Structural: plugin.json present + required fields; .mcp.json resolvable;
     server file exists; registry well-formed; marketplace.json (if found) lists
     the plugin and its source resolves.
  2. Official: runs `claude plugin validate <path>` if the CLI is on PATH.
  3. Live: runs scripts/smoke_test_mcp.py against the server (skip with --no-smoke).

Usage:
    python validate_plugin.py path/to/plugins/my-plugin
    python validate_plugin.py path/to/marketplace        # auto-finds plugins/*

Exit 0 = all good, 1 = problems found.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GREEN, RED, YEL, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


class Report:
    def __init__(self):
        self.fail = 0
        self.warn = 0

    def ok(self, m): print(f"  {GREEN}ok{RESET}   {m}")
    def bad(self, m): print(f"  {RED}FAIL{RESET} {m}"); self.fail += 1
    def wrn(self, m): print(f"  {YEL}warn{RESET} {m}"); self.warn += 1


def find_plugin_dirs(path: Path):
    """Accept a plugin dir (has .claude-plugin/plugin.json) or a marketplace
    dir (has .claude-plugin/marketplace.json) and yield plugin dirs."""
    if (path / ".claude-plugin" / "plugin.json").exists():
        return [path]
    mkt = path / ".claude-plugin" / "marketplace.json"
    if mkt.exists():
        data = json.loads(mkt.read_text())
        root = data.get("metadata", {}).get("pluginRoot", ".")
        dirs = []
        for p in data.get("plugins", []):
            src = p.get("source", "")
            if isinstance(src, str) and src.startswith("."):
                dirs.append((path / src).resolve())
            elif isinstance(src, str):
                dirs.append((path / root / src).resolve())
        return dirs or [d for d in (path / "plugins").glob("*") if d.is_dir()]
    return [d for d in (path / "plugins").glob("*") if (d / ".claude-plugin" / "plugin.json").exists()] or [path]


def check_plugin(path: Path, r: Report, smoke: bool):
    print(f"\nplugin: {path}")
    pj = path / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        r.bad(f"missing {pj}"); return
    try:
        meta = json.loads(pj.read_text())
    except json.JSONDecodeError as e:
        r.bad(f"plugin.json is not valid JSON: {e}"); return
    if not meta.get("name"):
        r.bad("plugin.json missing required 'name'")
    else:
        r.ok(f"name={meta['name']}  version={meta.get('version','(none)')}")
    if not meta.get("description"):
        r.wrn("plugin.json has no 'description' (it drives discovery)")

    # resolve mcpServers
    ms = meta.get("mcpServers")
    spec = None
    if isinstance(ms, str):
        sp = (path / ms).resolve()
        if not sp.exists():
            r.bad(f"mcpServers path not found: {sp}")
        else:
            spec = json.loads(sp.read_text()).get("mcpServers", {})
            r.ok(f"mcpServers -> {ms}")
    elif isinstance(ms, dict):
        spec = ms; r.ok("mcpServers inline")
    elif (path / ".mcp.json").exists():
        spec = json.loads((path / ".mcp.json").read_text()).get("mcpServers", {})
        r.ok(".mcp.json present (auto-discovered)")
    else:
        r.wrn("no MCP server declared (fine if this plugin uses skills/commands instead)")

    if spec:
        for sname, conf in spec.items():
            entry = " ".join(conf.get("args", []))
            for token in conf.get("args", []):
                if "${CLAUDE_PLUGIN_ROOT}" in token:
                    rel = token.replace("${CLAUDE_PLUGIN_ROOT}/", "")
                    if not (path / rel).exists():
                        r.bad(f"server '{sname}' entry not found: {rel}")
                    else:
                        r.ok(f"server '{sname}' entry exists: {rel}")
                elif token.startswith("/") and not Path(token).exists():
                    r.wrn(f"server '{sname}' uses absolute path that does not exist here: {token}")
            if "${CLAUDE_PLUGIN_ROOT}" not in entry and conf.get("command") not in (None,):
                if not any(t.startswith("${") for t in conf.get("args", [])):
                    r.wrn(f"server '{sname}' does not use ${{CLAUDE_PLUGIN_ROOT}} — prefer it over hardcoded paths")

    # registry sanity (this template's convention; harmless if absent)
    reg = path / "registry"
    if reg.exists():
        skills = list((reg / "skills").glob("*/SKILL.md")) if (reg / "skills").exists() else []
        agents = list((reg / "agents").glob("*.md")) if (reg / "agents").exists() else []
        r.ok(f"registry: {len(skills)} skill(s), {len(agents)} agent(s)")
        for sk in skills:
            txt = sk.read_text()
            if not txt.lstrip().startswith("---"):
                r.wrn(f"{sk.relative_to(path)} has no frontmatter (need name+description)")

    # smoke test
    if smoke and spec:
        print("  running smoke test ...")
        rc = subprocess.run(
            [sys.executable, str(HERE / "smoke_test_mcp.py"), "--plugin", str(path),
             "--expect-tool", "list_skills"],
            capture_output=True, text=True,
        )
        for line in rc.stdout.splitlines():
            print(f"    {line}")
        if rc.returncode != 0:
            r.bad("smoke test failed")
            if rc.stderr.strip():
                print(f"    {rc.stderr.strip()[:300]}")
        else:
            r.ok("smoke test passed")


def run_official(path: Path, r: Report):
    if not shutil.which("claude"):
        r.wrn("`claude` CLI not on PATH — skipping official `claude plugin validate`")
        return
    rc = subprocess.run(["claude", "plugin", "validate", str(path)], capture_output=True, text=True)
    out = (rc.stdout + rc.stderr).strip()
    if rc.returncode == 0 and "passed" in out.lower():
        r.ok(f"claude plugin validate {path.name}: passed")
    else:
        r.bad(f"claude plugin validate {path.name}: {out.splitlines()[-1] if out else 'failed'}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a Claude Code plugin/marketplace.")
    ap.add_argument("path", help="plugin dir or marketplace dir")
    ap.add_argument("--no-smoke", action="store_true", help="skip the live MCP smoke test")
    args = ap.parse_args()
    target = Path(args.path).resolve()
    if not target.exists():
        print(f"error: {target} not found", file=sys.stderr); return 2

    r = Report()
    # official validate on whatever was passed (plugin or marketplace)
    print("== official manifest validation ==")
    run_official(target, r)
    if (target / ".claude-plugin" / "marketplace.json").exists():
        # also validate each member plugin manifest
        pass

    print("\n== structural + live checks ==")
    for pdir in find_plugin_dirs(target):
        check_plugin(pdir, r, smoke=not args.no_smoke)

    print()
    if r.fail:
        print(f"{RED}VALIDATION FAILED{RESET}: {r.fail} error(s), {r.warn} warning(s)")
        return 1
    print(f"{GREEN}VALIDATION PASSED{RESET}" + (f" ({r.warn} warning(s))" if r.warn else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
