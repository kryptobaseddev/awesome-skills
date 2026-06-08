# Reference: plugin.json · marketplace.json · .mcp.json · variables · validation

Read this when filling or debugging manifests. Field facts here are the *current
product schema* — note that Anthropic's own `plugin-structure` skill omits several
fields the schema accepts (`displayName`, `skills`, `lspServers`); those are
called out below.

## Directory layout (canonical)

```
my-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # REQUIRED at marketplace root
└── plugins/
    └── my-plugin/
        ├── .claude-plugin/
        │   └── plugin.json       # REQUIRED — MUST live in .claude-plugin/
        ├── .mcp.json             # MCP servers — at plugin ROOT (not in .claude-plugin/)
        ├── commands/             # auto-discovered (default ./commands)
        ├── agents/               # auto-discovered (default ./agents)
        ├── skills/<id>/SKILL.md  # auto-discovered (default ./skills)
        ├── hooks/hooks.json      # default ./hooks/hooks.json
        └── scripts/              # your code; reference via ${CLAUDE_PLUGIN_ROOT}
```

**Rule:** the manifest MUST be in `.claude-plugin/`; all *component* dirs MUST be
at the **plugin root**, NOT nested under `.claude-plugin/`. Create only the dirs
you use. Everything kebab-case.

## plugin.json

```json
{
  "name": "my-plugin",
  "displayName": "My Plugin",
  "version": "0.1.0",
  "description": "What it does AND when to use it.",
  "author": { "name": "you", "email": "you@example.com", "url": "https://…" },
  "homepage": "https://…",
  "repository": "https://github.com/you/repo",
  "license": "MIT",
  "keywords": ["mcp", "…"],
  "mcpServers": "./.mcp.json"
}
```

- `name` — **required**. Regex `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` (lowercase, starts
  with a letter, kebab). It's the namespace (`/my-plugin:cmd`, `plugin:my-plugin:server`).
- `version` — semver; defaults to `0.1.0` if omitted; pre-release ok (`1.0.0-rc.1`).
- `author` — object (as above) **or** string `"Jane <jane@x.com> (https://x.com)"`.
- `repository` — string URL **or** `{ "type": "git", "url": "…", "directory": "…" }`.
- `homepage`/URLs — must be **valid URLs**. Do NOT emit empty strings (`""` fails
  validation with "Invalid URL"). Omit the field instead. (The scaffolder prunes
  empty optionals automatically.)
- **Component fields** — each is a path string, an array of paths, or an inline
  object. They **supplement, not replace** the auto-discovery defaults:

  | Field | Default | Notes |
  |---|---|---|
  | `commands` | `["./commands"]` | flat `.md`; **nested subdirs are NOT auto-discovered — list each subdir** |
  | `agents` | `["./agents"]` | subagent `.md` files |
  | `skills` | `./skills` (auto) | `skills/<id>/SKILL.md` |
  | `hooks` | `./hooks/hooks.json` | path **or** inline object |
  | `mcpServers` | `./.mcp.json` | path **or** inline object |
  | `lspServers` | `./.lsp.json` | path **or** inline object |

  Paths must be relative, start with `./`, no `../`, forward slashes only (even on
  Windows). For the MCP-only pattern: set **only `mcpServers`** and ship none of
  the others — that's what keeps always-on ~0.

> Schema-vs-docs note: the published `plugin-structure` skill does not document
> `displayName`, `skills`, or `lspServers`. The product schema accepts them (and
> `claude plugin validate` passes them). Prefer the fuller set; just know the docs
> lag.

## marketplace.json

```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/claude-code/main/schemas/marketplace.json",
  "name": "my-marketplace",
  "owner": { "name": "you", "url": "https://github.com/you" },
  "description": "…",
  "plugins": [
    { "name": "my-plugin", "source": "./plugins/my-plugin", "description": "…" }
  ]
}
```

- `name`, `owner` (`{name, email?, url?}`), `plugins[]` are required. (Again, omit
  empty `owner.url` rather than `""`.)
- `plugins[].source` forms:
  - local relative path `"./plugins/x"` (resolves to **marketplace root**; works
    for `directory` and git marketplaces);
  - `{ "source": "github", "repo": "owner/repo", "ref": "v1", "sha": "…" }`;
  - `{ "source": "url", "url": "https://gitlab.com/…​.git", "ref": "…" }`;
  - `{ "source": "git-subdir", "url": "…", "path": "tools/x" }`;
  - `{ "source": "npm", "package": "@org/x", "version": "^2" }`.
- `metadata.pluginRoot: "./plugins"` lets you write `"source": "x"` instead of
  `"./plugins/x"`. **Don't set both** a `pluginRoot` and `./plugins/x`-style
  sources — pick one style. (This skill's template uses explicit `./plugins/x` and
  no `pluginRoot`.)
- Plugin entries may also carry `version`, `author`, `homepage`, `category`,
  `tags`, `displayName`, `defaultEnabled`, `strict`.

> The OpenAI/Codex "marketplace" shape (`source:{source,path}`, `policy{}`,
> `interface{}`) is a **different product** — do not mix it into a Claude Code
> marketplace. Claude Code uses the shape above.

## .mcp.json

```json
{
  "mcpServers": {
    "my-plugin": {
      "type": "stdio",
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/server.mjs"],
      "env": { "MY_PLUGIN_REGISTRY": "${CLAUDE_PLUGIN_ROOT}/registry" }
    }
  }
}
```

- Transports: `stdio` (use this for a bundled local server), `http`, `sse`, `ws`.
- `command`/`args`/`env` all support variable expansion.

## Path variables

| Variable | Expands to | Use for |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | the plugin's root dir | **all intra-plugin paths** in `.mcp.json`, hooks, commands, LSP. For local `directory` marketplaces this is your live source dir (hot-reload); for git it's the cache copy. |
| `${CLAUDE_PROJECT_DIR}` | the project/repo root | reading the user's project |
| `${CLAUDE_PLUGIN_DATA}` | persistent state dir (survives updates) | caches, db |
| `${CLAUDE_SKILL_DIR}` | a **skill's** own dir (inside a skill) | a SKILL.md self-referencing its bundled files |
| `${ANY_ENV_VAR}` | environment value | secrets, hosts |

**Never** hardcode absolute paths, `~/…`, or working-dir-relative `./scripts/…`
in plugin config — they break once installed/cached. Always `${CLAUDE_PLUGIN_ROOT}`.

## Install / manage commands

```bash
claude plugin validate <plugin-or-marketplace-dir>     # lint WITHOUT installing
claude plugin marketplace add <dir | owner/repo | git-url> [--scope user|project|local]
claude plugin install <plugin>@<marketplace> [--scope …]
claude plugin list                                     # enabled/disabled
claude plugin details <plugin>                         # component inventory + token cost
claude plugin enable|disable|uninstall <plugin>@<marketplace>
claude plugin marketplace remove <marketplace>
claude mcp list                                        # confirm plugin:<p>:<s> ✓ Connected
```

State files: `~/.claude/plugins/{known_marketplaces.json, installed_plugins.json,
cache/, marketplaces/}`; enabled state in `settings.json` `enabledPlugins`.

## Validation errors → fixes

| Error | Cause | Fix |
|---|---|---|
| `homepage: Invalid URL` | `homepage`/`owner.url` is `""` | omit the field (don't emit empty strings) |
| `name: …` invalid | not `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` | lowercase, start with a letter, kebab |
| component path error | absolute / `../` / backslash / missing | relative `./…`, forward slashes, file must exist |
| server entry not found | `${CLAUDE_PLUGIN_ROOT}/x` doesn't resolve | check the path exists in the plugin |
| server connects but tools absent | session predates install | start a **new** session (MCP attaches at start) |
| `not valid JSON` | trailing comma / syntax | `jq empty file.json` to locate |
| stdout-corruption / server drops | server logged to stdout | route all logs to **stderr** (see mcp-server.md) |
