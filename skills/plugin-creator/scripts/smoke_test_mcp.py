#!/usr/bin/env python3
"""
smoke_test_mcp.py — prove a plugin's MCP stdio server actually works.

Runs the real handshake a Claude Code client would: initialize -> tools/list ->
resources/list -> (optional) a tools/call, and checks that stdout stayed clean
JSON-RPC the whole time (the #1 way these servers break is logging to stdout).

Two ways to point it at a server:
  # A) at a plugin directory — derives the launch command from its .mcp.json,
  #    expanding ${CLAUDE_PLUGIN_ROOT} to that directory:
  python smoke_test_mcp.py --plugin path/to/plugins/my-plugin

  # B) at an explicit command:
  python smoke_test_mcp.py -- node path/to/server.mjs

Exit code 0 = all checks passed, 1 = a check failed, 2 = bad usage.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.mcp_stdio import McpStdioClient, McpError  # noqa: E402

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def ok(msg):
    print(f"  {GREEN}PASS{RESET} {msg}")


def bad(msg):
    print(f"  {RED}FAIL{RESET} {msg}")


def derive_command_from_plugin(plugin_dir: Path):
    """Read <plugin>/.mcp.json, return (command_list, server_name) with
    ${CLAUDE_PLUGIN_ROOT} expanded to the plugin dir."""
    mcp = plugin_dir / ".mcp.json"
    # plugin.json may point mcpServers elsewhere, or inline it.
    pj = plugin_dir / ".claude-plugin" / "plugin.json"
    spec_path = mcp
    inline = None
    if pj.exists():
        meta = json.loads(pj.read_text())
        ms = meta.get("mcpServers")
        if isinstance(ms, str):
            spec_path = (plugin_dir / ms).resolve()
        elif isinstance(ms, dict):
            inline = {"mcpServers": ms}
    data = inline if inline is not None else json.loads(spec_path.read_text())
    servers = data.get("mcpServers") or {}
    if not servers:
        raise SystemExit(f"no mcpServers found in {spec_path}")
    name, conf = next(iter(servers.items()))
    if conf.get("type", "stdio") != "stdio":
        raise SystemExit(f"server '{name}' is not stdio (type={conf.get('type')})")

    def expand(s: str) -> str:
        return (s.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_dir))
                 .replace("${CLAUDE_PROJECT_DIR}", os.getcwd()))

    cmd = [expand(conf["command"])] + [expand(a) for a in conf.get("args", [])]
    return cmd, name, {k: expand(v) for k, v in (conf.get("env") or {}).items()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Smoke-test an MCP stdio server.")
    ap.add_argument("--plugin", help="plugin directory containing .mcp.json")
    ap.add_argument("--call", action="append", default=[],
                    help="tool to invoke as name or name:json-args (repeatable)")
    ap.add_argument("--expect-tool", action="append", default=[],
                    help="assert this tool name exists (repeatable)")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("command", nargs="*", help="explicit server command after --")
    args = ap.parse_args()

    env = dict(os.environ)
    if args.plugin:
        plugin_dir = Path(args.plugin).resolve()
        cmd, server_name, extra_env = derive_command_from_plugin(plugin_dir)
        env.update(extra_env)
        print(f"{DIM}server '{server_name}' via {' '.join(cmd)}{RESET}")
    elif args.command:
        cmd = args.command
        print(f"{DIM}server via {' '.join(cmd)}{RESET}")
    else:
        ap.error("provide --plugin DIR or an explicit command after --")
        return 2

    failures = 0
    try:
        with McpStdioClient(cmd, env=env, timeout=args.timeout) as c:
            info = c.initialize()
            si = info.get("serverInfo", {})
            caps = info.get("capabilities", {})
            ok(f"initialize -> {si.get('name','?')} v{si.get('version','?')}; "
               f"capabilities={','.join(caps) or 'none'}")
            if not info.get("instructions"):
                print(f"  {DIM}note: no `instructions` preamble (recommended for discovery){RESET}")

            tools = c.list_tools()
            names = [t["name"] for t in tools]
            ok(f"tools/list -> {len(tools)} tool(s): {', '.join(names) or '(none)'}")
            for t in tools:
                if "inputSchema" not in t:
                    bad(f"tool '{t['name']}' missing inputSchema"); failures += 1
            for want in args.expect_tool:
                if want in names:
                    ok(f"expected tool present: {want}")
                else:
                    bad(f"expected tool MISSING: {want}"); failures += 1

            if "resources" in caps:
                resources = c.list_resources()
                ok(f"resources/list -> {len(resources)} resource(s)")
                if resources:
                    uri = resources[0]["uri"]
                    body = c.read_resource(uri)
                    txt = (body.get("contents") or [{}])[0].get("text", "")
                    ok(f"resources/read {uri} -> {len(txt)} chars")

            for spec in args.call:
                name, _, raw = spec.partition(":")
                cargs = json.loads(raw) if raw else {}
                res = c.call_tool(name, cargs)
                if res.get("isError"):
                    bad(f"tools/call {name} -> error: "
                        f"{(res.get('content') or [{}])[0].get('text','')[:120]}")
                    failures += 1
                else:
                    txt = (res.get("content") or [{}])[0].get("text", "")
                    ok(f"tools/call {name} -> {len(txt)} chars")

            # stdout purity: the client records any non-JSON stdout lines into stderr_text
            polluted = [l for l in c.stderr_text.splitlines() if l.startswith("[stdout-non-json]")]
            if polluted:
                bad(f"server polluted stdout with {len(polluted)} non-JSON line(s) — will break MCP")
                for l in polluted[:3]:
                    print(f"      {DIM}{l}{RESET}")
                failures += 1
            else:
                ok("stdout stayed clean JSON-RPC")
    except McpError as e:
        bad(str(e))
        return 1
    except FileNotFoundError as e:
        bad(f"could not launch server: {e}")
        return 1

    print()
    if failures:
        print(f"{RED}SMOKE TEST FAILED{RESET} ({failures} issue(s))")
        return 1
    print(f"{GREEN}SMOKE TEST PASSED{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
