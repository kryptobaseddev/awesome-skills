# Reference: the MCP server (protocol, design, extending, execution models)

Read this when customizing the generated server (`mcp/server.mjs` or `server.py`)
or adding project-specific tools. The scaffolded server is zero-dependency and
implements MCP stdio by hand so it runs with bare `node`/`python` — no SDK to
install, nothing to break in CI.

## Protocol in one screen

MCP over **stdio = newline-delimited JSON-RPC 2.0**. One JSON object per line, no
embedded newlines. The client (Claude Code) spawns your server and exchanges:

```
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",
     "capabilities":{"tools":{},"resources":{}},
     "serverInfo":{"name":"…","version":"…"},"instructions":"…"}}
→ {"jsonrpc":"2.0","method":"notifications/initialized"}        (notification: no id, no reply)
→ {"jsonrpc":"2.0","id":2,"method":"tools/list"}
← {... "result":{"tools":[ ... ]}}
→ {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"…","arguments":{…}}}
← {... "result":{"content":[{"type":"text","text":"…"}]}}
```

Methods the scaffolded server handles: `initialize`, `notifications/initialized`,
`ping`, `tools/list`, `tools/call`, `resources/list`, `resources/templates/list`,
`resources/read`. Unknown method → JSON-RPC error `-32601`.

**THE #1 RULE: stdout carries ONLY protocol JSON.** Every log/print/debug line
must go to **stderr**. A single stray `console.log`/`print` to stdout corrupts the
stream and the client drops the connection. The bundled `smoke_test_mcp.py`
explicitly checks for stdout pollution.

## What the server exposes (the registry pattern)

- **Tools** (always-on cost = name only, under Tool Search):
  `list_skills`, `load_skill(id)`, `list_agents`, `load_agent(id)`.
- **Resources** (always-on cost = URI + 1-liner): `skill://<id>`, `agent://<id>`,
  plus `resources/templates/list` advertising the `skill://{id}` / `agent://{id}`
  shapes.
- **`instructions`**: a short preamble teaching the discover→load→act loop. This
  is your highest-leverage always-on text — keep it tight and concrete.

The registry is the filesystem: `registry/skills/<id>/SKILL.md` (frontmatter
`name`+`description`, then body) and `registry/agents/<id>.md`. The server parses
frontmatter for the listing and returns the body on `load_*`/`read`. Add files →
they appear automatically. No rebuild, no manifest.

## Adding a project-specific tool

Two edits. (Node shown; Python is the same shape.)

```js
// 1) add a tool definition to TOOLS
{
  name: "search_registry",
  description: "Full-text search skill/agent bodies for a term.",
  inputSchema: { type: "object",
    properties: { q: { type: "string", description: "search term" } },
    required: ["q"], additionalProperties: false },
}
// 2) add a case to callTool()
case "search_registry": {
  const q = String(args?.q ?? "").toLowerCase();
  const hits = listSkills().filter(s =>
    readSkillBody(s.id).toLowerCase().includes(q)).map(s => s.id);
  return text(JSON.stringify(hits));
}
```

Keep the tool **count** small (Tool-Search-off endpoints pay per tool). Prefer
adding *arguments* and *resources* over many tools.

## Execution models — host-executes vs server-executes

**A. Host-executes (default).** `load_skill`/`load_agent` return text; the calling
Claude session follows it. No extra runtime; the work shares the session context.
Best for "a workflow the main agent should carry out" and for agents you dispatch
via the host's Task tool (`load_agent("x")` → spawn a subagent with that prompt).

**B. Server-executes (commission a run).** Add a `run_*` tool that does the work
*inside the server* and returns only the result — so the calling session never
holds the heavy context. Two ways to implement the worker:

- **Spawn a CLI** (what open-design does): `spawn('claude', ['-p','--output-format',
  'stream-json', …])`, feed the composed prompt on **stdin**, stream results back.
  Needs an agent CLI + creds where the server runs.
- **Call the Claude Agent SDK / Messages API in-process**: `@anthropic-ai/claude-agent-sdk`
  (Node) or the `anthropic` SDK; read the key from `env` (set via `.mcp.json`
  `env` or the user's environment). Return the final text/artifact.

Choose B for long, self-contained jobs you want isolated; A for guidance the main
agent should act on. (Note: if your server runs in a sandbox/container without an
agent CLI or API key — e.g. a Dockerized daemon — `run_*` via CLI spawn won't
work; use the SDK path with a key, or keep to model A.)

## HTTP/daemon-backed registry (scaling beyond the filesystem)

When the catalog is large or shared, back the registry with a service instead of
local files (open-design's model): the stdio server becomes a thin bridge that
fetches `GET /api/skills` for the listing and `GET /api/skills/:id` for the body.
Keep the **listing body-less** (ids + descriptions only) and fetch full bodies
lazily in `load_*`/`resources/read`. Everything else (tool surface, instructions,
resource URIs) is identical. This lets one daemon serve many agents and hot-update
the catalog without reinstalling the plugin.

## Testing your server

```bash
# bundled smoke test (handshake + tools + resources + stdout-purity check)
python scripts/smoke_test_mcp.py --plugin <plugin-dir> \
  --expect-tool list_skills --call list_skills --call 'load_skill:{"id":"<id>"}'

# or against a raw command
python scripts/smoke_test_mcp.py -- node <plugin-dir>/mcp/server.mjs
```

The `scripts/lib/mcp_stdio.py` `McpStdioClient` is a tiny, vendorable MCP stdio
client you can reuse in your own tests.
