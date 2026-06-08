---
name: plugin-creator
description: "Scaffold, validate, test, and ship a production-grade Claude Code plugin + marketplace — especially the pattern where the plugin's ONLY component is an MCP server that surfaces a registry of skills and agents on demand (so they never clog the / menu or the always-on context). Use this WHENEVER the user wants to create, build, scaffold, package, or distribute a Claude Code plugin, plugin marketplace, or MCP-server plugin; expose project-specific skills/agents/tools to a coding agent; turn skills or agents into an installable package; or \"make a plugin for this project\" — even if they don't say \"MCP\" or \"marketplace\" explicitly. Ships a scaffolder, a smoke-tester, a validator, reference docs, and Node + Python server templates so any agent can do this repeatably and correctly."
license: MIT
compatibility: >-
  Requires Python 3.8+ for the bundled scripts (standard library only). Generated
  Node servers need Node.js; generated Python servers need Python 3.8+. The `claude`
  CLI is optional — used for official `claude plugin validate` and install
  round-trips. Linux, macOS, and WSL.
metadata:
  author: github.com/kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-06-08 12:20:29"
  category: skill-development
allowed-tools: Bash Read Write Edit Glob Grep
---

# plugin-creator

Create a robust, installable Claude Code **plugin + marketplace** for the project
you're invoked in — and do it the *right* way: a plugin whose only component is an
**MCP server** that exposes a registry of skills/agents **on demand**, so the
catalog can be huge while the always-on context cost stays ~0 and nothing lands in
the user's `/` menu.

This skill bundles everything needed to do it repeatably: a **scaffolder**, a
**smoke-tester**, a **validator**, Node + Python server templates, and four
reference docs. Use the scripts — don't hand-write boilerplate or reinvent an MCP
client; that's what the bundled tooling is for.

`${CLAUDE_SKILL_DIR}` below means this skill's own directory (where this SKILL.md
lives). Run the scripts from there.

## Not the right fit? Redirect, don't force it

This skill scaffolds a **distributable Claude Code plugin**. If the real request
is something adjacent, say so plainly and point the user the right way instead of
scaffolding a plugin they didn't ask for:

- **One standalone skill, not a package** ("turn this into a Claude Code skill",
  no distribution) → that's `skill-creator`, not this. Don't create a marketplace.
- **A general MCP *client* / application** (a CLI or app that connects out to MCP
  servers) → that's ordinary application code; help them build it directly. This
  skill builds the *server* side packaged as a plugin, not clients.
- **Just a slash command or a hook**, no catalog → a plain plugin `command`/`hook`
  is simpler; see `references/recipes.md` "Pick a shape".

When it *is* a plugin, continue below.

## The idea in one table

A plugin can ship commands, skills, agents, hooks, and MCP servers. Native skills
and agents inject their name+description into **every session's system prompt**
(cost scales with count) and add `/` menu entries. MCP tools are deferred (name
only) and MCP resources load their body **only when read**. So:

| Ship capabilities as… | Always-on cost | `/` menu noise | Scales with count |
|---|---|---|---|
| Native skills / agents | name+desc each | yes | badly |
| **MCP registry (this skill)** | ~0 (tool names + 1 preamble) | none | flat |

`claude plugin details <plugin>` will read **`Always-on: ~0 tok`** when done right.
The full cost model and the open-design worked example are in
`references/architecture.md` — read it if the user asks *why*, or wants the daemon-
backed variant.

## Before you scaffold: decide the shape

Most requests → the **MCP registry** default below. But check
`references/recipes.md` "Pick a shape" first when the user wants something else:
native auto-triggered skills, a pure data/API tool plugin, slash commands, hooks,
or a hybrid (a few native skills + a big MCP registry). Hybrids are common and
fine.

Then figure out **what THIS project actually needs** before generating anything:
- Skim the repo (README, package manifest, top-level dirs) to learn the domain.
- Ask the user (briefly) which capabilities the plugin should expose — the
  skills/workflows and any specialized agents. Each becomes a registry entry.
- Pick a name (kebab-case, starts with a letter) and a one-line description that
  says **what it does AND when to use it** (that description drives discovery).

## Happy path (the repeatable workflow)

All commands assume `SK=${CLAUDE_SKILL_DIR}`.

**1 — Scaffold** a complete, installable plugin+marketplace:

```bash
python "$SK/scripts/scaffold_plugin.py" \
  --name <plugin-name> \
  --description "<what it does AND when to use it>" \
  --owner <you-or-org> \
  --dest <where-to-create-it> \
  --lang node            # or: python
# add --homepage <url> if you have one; --force to overwrite; --server-name to override
```

This writes a `<name>-marketplace/` containing the plugin: `plugin.json`
(mcpServers only), `.mcp.json` (using `${CLAUDE_PLUGIN_ROOT}`), a zero-dependency
MCP server (`mcp/server.mjs` or `server.py`), a `registry/` with one example skill
and one example agent, a README, and `.gitignore`. It prints the next commands.

**2 — Fill the registry** with the project's real capabilities:
- Skill: `registry/skills/<id>/SKILL.md` — frontmatter `name` + `description`,
  then the body (the workflow the agent will follow). Appears in `list_skills`
  automatically; zero always-on cost.
- Agent: `registry/agents/<id>.md` — frontmatter `name` + `description`, then the
  subagent's system prompt. Pulled via `load_agent` and dispatched with the host's
  Task tool.
Delete the `example-*` entries once you've added real ones.

**3 — Customize the server (optional)** — add project-specific tools (a DB query,
an API call, a `search_registry`) or a server-executes `run_*` tool. See
`references/mcp-server.md` "Adding a tool" and "Execution models". Keep the tool
**count** small; lean on arguments + resources.

**4 — Smoke-test** the server (handshake + tools + resources + stdout-purity):

```bash
python "$SK/scripts/smoke_test_mcp.py" --plugin <marketplace>/plugins/<name> \
  --expect-tool list_skills --call list_skills --call 'load_skill:{"id":"<id>"}'
```
All checks must read `PASS` and end `SMOKE TEST PASSED`. If stdout is polluted,
the server is logging to stdout — route logs to stderr.

**5 — Validate** structure + manifests + a live smoke run in one shot:

```bash
python "$SK/scripts/validate_plugin.py" <marketplace-dir>
```
Must end `VALIDATION PASSED`. (It also runs the official `claude plugin validate`
when the CLI is present.)

**6 — Install locally and confirm it connects:**

```bash
claude plugin marketplace add <marketplace-dir> --scope user
claude plugin install <name>@<name>-marketplace --scope user
claude mcp list | grep <server-name>      # → plugin:<name>:<server> ✓ Connected
```
The server health-checks as connected immediately; its **tools become callable to
the agent on the next session start** (MCP attaches at session start). Confirm by
asking, in a fresh session, to `list_skills` and `load_skill`.

**7 — Ship.** Push the marketplace repo to GitHub. Users then run
`claude plugin marketplace add <owner>/<repo>` and `claude plugin install
<name>@<name>-marketplace`. (Local `directory` source is for dev — it resolves
`${CLAUDE_PLUGIN_ROOT}` to your live source dir, so edits hot-reload on reconnect.
Git/GitHub sources are for distribution.)

## Bundled tooling

| Script | What it does |
|---|---|
| `scripts/scaffold_plugin.py` | Generate a full plugin+marketplace (Node or Python server) from the `assets/templates/`. Validates the name, prunes empty optional fields, prints next steps. |
| `scripts/smoke_test_mcp.py` | Drive the real MCP stdio handshake (`initialize`→`tools/list`→`resources/list`→`tools/call`) against a plugin dir or raw command; assert tools/resources exist and **stdout stayed clean JSON-RPC**. |
| `scripts/validate_plugin.py` | Structural checks (manifests, `${CLAUDE_PLUGIN_ROOT}` resolution, registry) + official `claude plugin validate` + a live smoke run. |
| `scripts/lib/mcp_stdio.py` | A tiny, dependency-free MCP stdio **client** (`McpStdioClient`) you can vendor into any project's tests. |

Templates the scaffolder emits live in `assets/templates/` (`common/`, `node/`,
`python/`) — edit them to change what every generated plugin looks like.

## References (read as needed)

| File | Read when |
|---|---|
| `references/architecture.md` | You need the cost model, the *why*, the open-design example, install-state files, or runtime namespacing. |
| `references/plugin-reference.md` | Filling/debugging `plugin.json` / `marketplace.json` / `.mcp.json`; path variables; the validation-error → fix table. |
| `references/mcp-server.md` | Customizing the server: protocol, adding tools, host-executes vs server-executes, daemon-backed registries. |
| `references/recipes.md` | Choosing a plugin shape, the on-demand-enable `.local.md` + hook pattern, dispatching registry agents, the error table, the ship checklist. |

## Non-negotiables (cheap to honor, expensive to skip)

- **stdout is protocol-only.** The server must print *nothing* to stdout except
  JSON-RPC; all logs go to stderr. This is the #1 way MCP servers silently fail —
  the smoke-tester checks it for you.
- **Always `${CLAUDE_PLUGIN_ROOT}`** for intra-plugin paths in `.mcp.json`/hooks —
  never absolute, `~/…`, or working-dir-relative paths. They break once installed.
- **Names**: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` (lowercase, start with a letter).
- **No empty URL fields.** Omit `homepage`/`owner.url` rather than emitting `""`
  (the validator rejects empty strings as invalid URLs). The scaffolder handles
  this; preserve it if you hand-edit.
- **Validate before you claim done.** Run `validate_plugin.py` and the install
  round-trip; report the actual `✓ Connected` line, not an assumption.
