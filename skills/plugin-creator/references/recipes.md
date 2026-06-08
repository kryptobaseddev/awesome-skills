# Recipes: common plugin shapes, on-demand enable, and an error table

Read this when deciding what *kind* of plugin to build, or when you want the
extra patterns (toggle-on-demand without a restart, hybrid native+MCP).

## Pick a shape

| You want… | Build | How |
|---|---|---|
| A big catalog of workflows/agents, used occasionally, no `/` clutter | **MCP registry** (this skill's default) | `scaffold_plugin.py`; fill `registry/` |
| One service's data exposed to the agent (DB, API, files) | **MCP tools** plugin | scaffold, replace registry tools with domain tools (`mcp-server.md`) |
| 1–3 behaviors you want auto-triggered by the model, used constantly | **native skills** | put `SKILL.md`s under `skills/`; set `skills` in plugin.json |
| Specialized subagents the orchestrator should auto-delegate to | **native agents** | `agents/*.md` listed in plugin.json (always-on) — vs on-demand `load_agent` via MCP |
| Slash-command UX, simple logic | **commands** | `commands/*.md` |
| Deterministic behavior around tool calls / session events | **hooks** | `hooks/hooks.json` |
| Large shared catalog, hot-updatable, many users | **HTTP/daemon-backed MCP** | `mcp-server.md` § daemon |

**Hybrid is normal:** a few native skills for the hot path + a big MCP registry
for the long tail. Set both `skills` and `mcpServers` in one plugin.json.

## On-demand enable WITHOUT editing hooks.json (the `.local.md` pattern)

Hooks and MCP servers can't be hot-swapped mid-session (they bind at session
start). To let a user toggle a capability per-project *without* editing
`hooks.json`, use a project settings file + a quick-exiting hook:

`.claude/<plugin>.local.md` (gitignored via `.claude/*.local.md`):
```markdown
---
enabled: true
mode: strict
---
Notes for humans.
```

A `SessionStart` (or `UserPromptSubmit`) hook reads it and quick-exits when off:
```bash
#!/usr/bin/env bash
SETTINGS=".claude/myplugin.local.md"
[[ ! -f "$SETTINGS" ]] && exit 0
# extract a frontmatter value (sed), guard against path traversal
enabled=$(sed -n '/^---$/,/^---$/p' "$SETTINGS" | sed -n 's/^enabled:[[:space:]]*//p')
[[ "$enabled" != "true" ]] && exit 0
echo "myplugin active (mode from settings)"   # injected into context
```
Register it in `hooks/hooks.json` with `"command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/enable.sh", "timeout": 30`.
Changing the `.local.md` takes effect on the next session (no plugin edit). This
is the cleanest "surface only when the project opts in" lever.

Hook events available: `PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart,
SessionEnd, UserPromptSubmit, PreCompact, Notification`.

## Dispatching a registry agent (on-demand, plugin-scoped)

```
1. list_agents                      → see what's available
2. load_agent("researcher")         → get the agent's full prompt
3. spawn a subagent (Task tool) with that text as its instructions
```
Result: an agent scoped to this plugin, loaded only when used — no `/agents`
entry, no always-on cost. Contrast with native `agents/*.md`, which are first-class
and auto-delegated but always-on. Use native for 1–3 signature agents; use the
registry for the long tail.

## Error table (scaffold/validate/install)

| Symptom | Cause | Fix |
|---|---|---|
| `claude plugin validate` → `Invalid URL` | empty `homepage`/`owner.url` | omit the field (scaffolder prunes empties) |
| validate → name error | bad name | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` |
| `marketplace add` fails on local dir | not a dir / no `.claude-plugin/marketplace.json` | point at the marketplace root |
| installed but server `✗`/absent | server crashed or stdout polluted | run `smoke_test_mcp.py`; route logs to stderr |
| server `✓ Connected` but no tools to the agent | session predates install | start a new session |
| tools work in `node server.mjs` but not installed | hardcoded path instead of `${CLAUDE_PLUGIN_ROOT}` | use the variable |
| duplicate plugin name | marketplace name collision | rename marketplace or plugin |
| JSON syntax error | trailing comma etc. | `jq empty file.json` |

## Ship checklist

1. `scaffold_plugin.py --name … --description … --lang node|python`
2. Fill `registry/` (skills/agents the project needs); add domain tools if useful.
3. `smoke_test_mcp.py --plugin <dir>` → all PASS, stdout clean.
4. `validate_plugin.py <marketplace-or-plugin>` → VALIDATION PASSED.
5. Install: `marketplace add` → `install` → `claude mcp list` shows `✓ Connected`.
6. (New session) confirm the agent can `list_skills` / `load_skill`.
7. Distribute: push the marketplace repo to GitHub; users
   `claude plugin marketplace add <owner>/<repo>` then `claude plugin install …`.
   (Local `directory` source is for dev; git/github for sharing.)
