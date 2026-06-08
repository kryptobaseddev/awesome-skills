# Architecture: MCP-only plugins that surface skills/agents on demand

Read this when you need the *why* and the cost model behind the pattern this
skill scaffolds. The decisive idea: **a plugin can ship just one MCP server** and
keep its whole catalog of skills/agents behind it, loaded just-in-time — so the
always-on context cost stays ~flat no matter how big the catalog grows, and
nothing clutters the `/` menu.

## The token / context cost model (this is the whole point)

A Claude Code plugin can ship: **commands**, **skills**, **agents (subagents)**,
**hooks**, **MCP servers** (and LSP/output styles). What decides whether a plugin
"clogs a session" is what each costs in the **always-on system prompt** — the
bytes attached to every request whether or not you use the capability.

| Component | Always-on (every session) | Loaded on demand | Scales with count? |
|---|---|---|---|
| Native **skill** (`SKILL.md`) | name + description (+ when-to-use), ~≤1,536 chars/skill; all share a ~1%-of-context budget | the SKILL.md **body**, only on trigger/invoke | **Yes** + a `/` entry each |
| Native **subagent** (`agents/*.md`) | name + description | agent **body**, only on invoke | **Yes** |
| **Command** (`commands/*.md`) | name + description | body on invoke | Yes (lighter) |
| **MCP tool** | with Tool Search (default on Opus/Sonnet/newer Haiku): **name only** (~1–2 tok); schema fetched at use | input schema, fetched on use | **~No** |
| **MCP resource** | URI + 1-line desc from `resources/list` | **body**, only via `ReadMcpResourceTool` | **~No** |
| MCP server **`instructions`** | one short preamble, on connect | — | No |

`claude plugin details <name>` reports a "Projected token cost → Always-on" line.
An MCP-only plugin reads **`Always-on: ~0 tok`** with `MCP servers (1) … (tool
schemas resolved at runtime; not counted)`. That is the target: a registry of any
size behind one server, fetched on demand.

> **Tool Search caveat.** The "names only" deferral applies on endpoints that
> support tool search (1P Anthropic API on Opus/Sonnet/newer Haiku). On Bedrock,
> Vertex, older Haiku, or a custom `ANTHROPIC_BASE_URL`, tool *schemas* can load
> fully (cost scales with tool *count*). So keep the tool surface to a handful of
> `list_*`/`load_*` verbs and push the catalog into **resources + arguments**, not
> into dozens of tools.

## How the surfacing works (three channels)

1. **Discovery tool** — `list_skills` / `list_agents` return a tiny catalog
   (id + one-line description). Cheap; the agent calls it when relevant.
2. **On-demand load** — `load_skill(id)` / `load_agent(id)` return the *full*
   body. This is "call the skill on demand": the agent then follows the workflow
   (or dispatches the agent prompt via its Task tool).
3. **Resources** — `skill://<id>` / `agent://<id>` expose the same bodies the
   resource way; `resources/list` advertises only URIs+descriptions, and the body
   is fetched only when the agent reads that URI (`ReadMcpResourceTool`).

The MCP server's **`instructions`** string is the one always-on teaching surface:
a few lines that tell the agent the discover→load→act loop exists, so it uses the
registry without you paying for N descriptions.

## The worked example: open-design

`nexu-io/open-design` ships a Claude Code plugin whose only payload is
`od mcp` (a stdio MCP server) — `Skills(0) Agents(0)`, `Always-on: ~0 tok` — yet
exposes 137+ skills and 150 design systems. Its server:
- `ListResources` advertises `od://skills/<id>/SKILL.md` (one per skill, name + 1-liner).
- `ReadResource` fetches the **full body** from the daemon's `/api/skills/:id` only
  when that URI is read. The `/api/skills` *listing* is deliberately body-less
  ("keeps the listing payload small").
- `list_skills` / `start_run` tools handle discovery and (optionally) execution.

The scaffolder in this skill produces the same shape, minus the daemon: a
filesystem `registry/` instead of an HTTP backend. For a heavier variant that
talks to a running service, see `mcp-server.md` (§ "HTTP/daemon-backed registry").

## Where install state lives (so you can debug/verify)

None of the public plugin docs spell these out; they matter when verifying:

- `~/.claude/plugins/known_marketplaces.json` — each marketplace → `source`
  (`{source:"directory",path}` for local, `{source:"github",repo}` for git) +
  `installLocation`.
- `~/.claude/plugins/installed_plugins.json` — `{ "<plugin>@<marketplace>":
  [{ scope, installPath, version, gitCommitSha, installedAt }] }` (`version: 2`).
- `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` — resolved copy
  (used for git/github sources; **local `directory` sources resolve
  `${CLAUDE_PLUGIN_ROOT}` to the live source dir** — handy for hot-reload dev).
- **Enabled/disabled** → `enabledPlugins` in `~/.claude/settings.json` (user),
  `.claude/settings.json` (project, shareable), or `…local.json` (gitignored).

## Naming you'll see at runtime

A plugin's MCP server appears in `claude mcp list` as
**`plugin:<plugin-name>:<server-name>`** (e.g. `plugin:acme-tools:acme-tools`),
and its tools are namespaced under that. This is how you confirm a freshly
installed plugin's server connected (`✓ Connected`). New MCP tools become callable
to the agent on the **next session start** (MCP attaches at session start), even
though the health check connects immediately.

## When NOT to use this pattern

- A capability you want **auto-triggered** by the model on matching prompts, used
  constantly → a **native skill** is better (you *want* the always-on description
  + `/` entry). Mix freely: a few native skills for the hot path, the long tail
  behind MCP.
- Pure slash-command UX with no logic → a plugin **command** is simpler than MCP.
- A behavior that must run deterministically around tool calls → a **hook**.
