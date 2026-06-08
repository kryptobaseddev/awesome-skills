# {{DISPLAY_NAME}}

{{DESCRIPTION}}

This is a Claude Code **plugin** whose only component is an **MCP server**. It ships
no native skills/agents, so it adds **~0 always-on context** and nothing to your `/`
menu. Capabilities live in `plugins/{{PLUGIN_NAME}}/registry/` and are surfaced to the
agent **on demand** via MCP tools (`list_skills` / `load_skill` / `list_agents` /
`load_agent`) and resources (`skill://<id>`, `agent://<id>`).

## Layout

```
{{MARKETPLACE_NAME}}/
├── .claude-plugin/marketplace.json
└── plugins/{{PLUGIN_NAME}}/
    ├── .claude-plugin/plugin.json     # mcpServers only
    ├── .mcp.json                      # {{RUNTIME}} ${CLAUDE_PLUGIN_ROOT}/{{SERVER_ENTRY}}
    ├── {{SERVER_ENTRY}}               # zero-dependency MCP stdio server
    └── registry/
        ├── skills/<id>/SKILL.md       # one folder per skill (loaded on demand)
        └── agents/<id>.md             # one file per agent (loaded on demand)
```

## Develop

```bash
# Smoke-test the MCP server (no install needed)
{{RUNTIME}} plugins/{{PLUGIN_NAME}}/{{SERVER_ENTRY}} < /dev/null   # or pipe JSON-RPC

# Validate manifests
claude plugin validate plugins/{{PLUGIN_NAME}}
claude plugin validate .

# Install locally and confirm it connects
claude plugin marketplace add . --scope user
claude plugin install {{PLUGIN_NAME}}@{{MARKETPLACE_NAME}} --scope user
claude mcp list | grep {{SERVER_NAME}}     # → ✓ Connected
```

## Add capabilities

- New skill: `mkdir -p plugins/{{PLUGIN_NAME}}/registry/skills/<id>` and add a `SKILL.md`
  with `name` + `description` frontmatter and a body. It appears in `list_skills` automatically.
- New agent: add `plugins/{{PLUGIN_NAME}}/registry/agents/<id>.md` with `name` + `description`.

## Ship

Push this marketplace to GitHub, then users run:

```bash
claude plugin marketplace add {{OWNER}}/{{MARKETPLACE_NAME}}
claude plugin install {{PLUGIN_NAME}}@{{MARKETPLACE_NAME}}
```
