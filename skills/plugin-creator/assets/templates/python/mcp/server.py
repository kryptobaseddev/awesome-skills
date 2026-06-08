#!/usr/bin/env python3
"""
{{SERVER_NAME}} — MCP stdio server for the "{{PLUGIN_NAME}}" Claude Code plugin.

A zero-dependency Model Context Protocol server (stdio transport) that exposes a
*registry* of skills and agents to a coding agent just-in-time. Bundling these as
native plugin skills/agents would inject their name+description into every
session and add `/` menu entries; keeping them behind this server means the only
always-on cost is ~4 tool names + a short preamble, regardless of catalog size.

Surface:
    tools:     list_skills, load_skill(id), list_agents, load_agent(id)
    resources: skill://<id>, agent://<id>

Protocol: MCP over stdio = newline-delimited JSON-RPC 2.0 on stdin/stdout.
HARD RULE: stdout carries ONLY protocol messages (one JSON object per line).
All logs go to stderr or the stream is corrupted.

Run:  python server.py        (then speak JSON-RPC on stdin)
In .mcp.json: python ${CLAUDE_PLUGIN_ROOT}/mcp/server.py
Requires Python 3.8+ (standard library only).
"""
import json
import os
import re
import sys
from pathlib import Path

SERVER_NAME = "{{SERVER_NAME}}"
SERVER_VERSION = os.environ.get("{{ENV_PREFIX}}_VERSION", "{{VERSION}}")
PROTOCOL_VERSION = "2024-11-05"

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent
REGISTRY = Path(os.environ.get("{{ENV_PREFIX}}_REGISTRY", PLUGIN_ROOT / "registry")).resolve()
SKILLS_DIR = REGISTRY / "skills"
AGENTS_DIR = REGISTRY / "agents"

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def log(*a):
    sys.stderr.write(f"[{SERVER_NAME}] " + " ".join(str(x) for x in a) + "\n")
    sys.stderr.flush()


def parse_frontmatter(raw: str):
    m = _FM.match(raw)
    if not m:
        return {}, raw.strip()
    meta = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip("\"'")
    return meta, m.group(2).strip()


def list_skills():
    out = []
    if SKILLS_DIR.is_dir():
        for d in sorted(SKILLS_DIR.iterdir()):
            f = d / "SKILL.md"
            if d.is_dir() and f.exists():
                meta, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
                out.append({"id": meta.get("name", d.name), "name": meta.get("name", d.name),
                            "description": meta.get("description", "")})
    return out


def list_agents():
    out = []
    if AGENTS_DIR.is_dir():
        for f in sorted(AGENTS_DIR.glob("*.md")):
            meta, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
            out.append({"id": meta.get("name", f.stem), "name": meta.get("name", f.stem),
                        "description": meta.get("description", "")})
    return out


def read_skill_body(skill_id: str) -> str:
    f = SKILLS_DIR / skill_id / "SKILL.md"
    if not f.exists():
        for s in list_skills():
            if s["id"] == skill_id:
                f = SKILLS_DIR / s["id"] / "SKILL.md"
                break
    if not f.exists():
        raise ValueError(f"skill not found: {skill_id}")
    _, body = parse_frontmatter(f.read_text(encoding="utf-8"))
    return body


def read_agent_body(agent_id: str) -> str:
    f = AGENTS_DIR / f"{agent_id}.md"
    if not f.exists():
        raise ValueError(f"agent not found: {agent_id}")
    return f.read_text(encoding="utf-8")  # keep frontmatter — it IS the definition


TOOLS = [
    {"name": "list_skills",
     "description": "List the skills this plugin can provide on demand (id + one-line description). "
                    "Cheap discovery — call this first, then load_skill(id) for the one you need.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "load_skill",
     "description": "Return the full instructions (SKILL.md body) for one skill so you can follow its "
                    "workflow now. Loads on demand — nothing preloaded into your context.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string", "description": "Skill id from list_skills."}},
                     "required": ["id"], "additionalProperties": False}},
    {"name": "list_agents",
     "description": "List the specialized sub-agent definitions this plugin ships (id + description). "
                    "Use load_agent(id) to pull one's prompt, then run it via your Task/Agent tool.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "load_agent",
     "description": "Return one agent's full definition (frontmatter + system prompt). Dispatch it by "
                    "spawning a generic subagent with this text as its instructions.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string", "description": "Agent id from list_agents."}},
                     "required": ["id"], "additionalProperties": False}},
]


def _text(s):
    return {"content": [{"type": "text", "text": s}]}


def call_tool(name, args):
    if name == "list_skills":
        return _text(json.dumps(list_skills(), indent=2))
    if name == "load_skill":
        return _text(read_skill_body(str((args or {}).get("id", ""))))
    if name == "list_agents":
        return _text(json.dumps(list_agents(), indent=2))
    if name == "load_agent":
        return _text(read_agent_body(str((args or {}).get("id", ""))))
    raise ValueError(f"unknown tool: {name}")


def list_resources():
    res = []
    for s in list_skills():
        res.append({"uri": f"skill://{s['id']}", "name": f"Skill: {s['name']}",
                    "description": s["description"], "mimeType": "text/markdown"})
    for a in list_agents():
        res.append({"uri": f"agent://{a['id']}", "name": f"Agent: {a['name']}",
                    "description": a["description"], "mimeType": "text/markdown"})
    return res


RESOURCE_TEMPLATES = [
    {"uriTemplate": "skill://{id}", "name": "Skill body", "description": "Full SKILL.md for a registry skill.", "mimeType": "text/markdown"},
    {"uriTemplate": "agent://{id}", "name": "Agent definition", "description": "Full definition for a registry agent.", "mimeType": "text/markdown"},
]


def read_resource(uri):
    m = re.match(r"^(skill|agent)://(.+)$", uri or "")
    if not m:
        raise ValueError(f"unsupported resource uri: {uri}")
    body = read_skill_body(m.group(2)) if m.group(1) == "skill" else read_agent_body(m.group(2))
    return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": body}]}


INSTRUCTIONS = (
    "{{DISPLAY_NAME}} is a CAPABILITY REGISTRY. Its skills and agents are NOT in your\n"
    "`/` menu and NOT preloaded — pull them on demand:\n"
    "  1. list_skills            -> discover available workflows (id + 1-line desc).\n"
    "  2. load_skill(id)          -> get a skill's full instructions, then follow them.\n"
    "  3. list_agents / load_agent(id) -> get a specialized agent's prompt, then run it\n"
    "     by spawning a subagent (Task tool) with that text as its instructions.\n"
    "Resources mirror this: read skill://<id> or agent://<id> for the same bodies.\n"
    "Always list_* first (cheap), then load exactly the one capability you need."
)


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def reply(_id, result):
    if _id is not None:
        send({"jsonrpc": "2.0", "id": _id, "result": result})


def fail(_id, code, message):
    if _id is not None:
        send({"jsonrpc": "2.0", "id": _id, "error": {"code": code, "message": message}})


def handle(msg):
    _id, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    try:
        if method == "initialize":
            return reply(_id, {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {"tools": {}, "resources": {}},
                               "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                               "instructions": INSTRUCTIONS})
        if method in ("notifications/initialized", "notifications/cancelled"):
            return
        if method == "ping":
            return reply(_id, {})
        if method == "tools/list":
            return reply(_id, {"tools": TOOLS})
        if method == "tools/call":
            return reply(_id, call_tool(params.get("name"), params.get("arguments") or {}))
        if method == "resources/list":
            return reply(_id, {"resources": list_resources()})
        if method == "resources/templates/list":
            return reply(_id, {"resourceTemplates": RESOURCE_TEMPLATES})
        if method == "resources/read":
            return reply(_id, read_resource(params.get("uri")))
        return fail(_id, -32601, f"method not found: {method}")
    except Exception as e:  # noqa: BLE001
        if method == "tools/call":
            return reply(_id, {"isError": True, "content": [{"type": "text", "text": str(e)}]})
        return fail(_id, -32603, str(e))


def main():
    log(f"ready; registry={REGISTRY}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log("skipping non-JSON line")
            continue
        handle(msg)


if __name__ == "__main__":
    main()
