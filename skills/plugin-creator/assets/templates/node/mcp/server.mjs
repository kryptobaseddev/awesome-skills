#!/usr/bin/env node
/**
 * {{SERVER_NAME}} — MCP stdio server for the "{{PLUGIN_NAME}}" Claude Code plugin.
 *
 * WHAT THIS IS
 *   A zero-dependency Model Context Protocol server (stdio transport) that
 *   exposes a *registry* of skills and agents to a coding agent JIT
 *   (just-in-time). Bundling these as native plugin skills/agents would inject
 *   their name+description into every session's system prompt and add `/` menu
 *   entries — a cost that grows with the catalog. Keeping them behind this
 *   server means the only always-on cost is ~4 tool names + a short preamble,
 *   regardless of whether the registry holds 3 entries or 3,000.
 *
 * SURFACE
 *   tools:     list_skills, load_skill(id), list_agents, load_agent(id)
 *   resources: skill://<id>, agent://<id>   (same bodies, resource-style)
 *
 * PROTOCOL
 *   MCP over stdio = newline-delimited JSON-RPC 2.0 on stdin/stdout.
 *   HARD RULE: stdout carries ONLY protocol messages (one JSON object per line).
 *   Everything else — logs, diagnostics — goes to stderr, or it corrupts the
 *   stream and the client drops the connection.
 *
 * RUN
 *   node server.mjs                       # then speak JSON-RPC on stdin
 *   In .mcp.json: node ${CLAUDE_PLUGIN_ROOT}/mcp/server.mjs
 *
 * EXTEND
 *   - Add a domain tool: push a def into TOOLS and a case into callTool().
 *   - Server-executes pattern: add a run_* tool that invokes the Claude Agent
 *     SDK / an API in-process and returns only the result (see references).
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SERVER_NAME = "{{SERVER_NAME}}";
const SERVER_VERSION = process.env.{{ENV_PREFIX}}_VERSION || "{{VERSION}}";
const PROTOCOL_VERSION = "2024-11-05";

// Resolve the registry relative to THIS file so the server is location-independent
// (identical behavior whether launched from source or a ~/.claude/plugins cache copy).
const HERE = dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = resolve(HERE, "..");
const REGISTRY = process.env.{{ENV_PREFIX}}_REGISTRY
  ? resolve(process.env.{{ENV_PREFIX}}_REGISTRY)
  : join(PLUGIN_ROOT, "registry");
const SKILLS_DIR = join(REGISTRY, "skills");
const AGENTS_DIR = join(REGISTRY, "agents");

const log = (...a) => process.stderr.write(`[${SERVER_NAME}] ${a.join(" ")}\n`);

/* ----------------------------- registry I/O ----------------------------- */

/** Minimal frontmatter splitter: returns { meta, body } from a `---`-fenced doc. */
function parseFrontmatter(raw) {
  const m = raw.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
  if (!m) return { meta: {}, body: raw.trim() };
  const meta = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!kv) continue;
    meta[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, "");
  }
  return { meta, body: m[2].trim() };
}

function listSkills() {
  if (!existsSync(SKILLS_DIR)) return [];
  const out = [];
  for (const ent of readdirSync(SKILLS_DIR, { withFileTypes: true })) {
    if (!ent.isDirectory()) continue;
    const file = join(SKILLS_DIR, ent.name, "SKILL.md");
    if (!existsSync(file)) continue;
    const { meta } = parseFrontmatter(readFileSync(file, "utf8"));
    out.push({ id: meta.name || ent.name, name: meta.name || ent.name, description: meta.description || "" });
  }
  return out;
}

function listAgents() {
  if (!existsSync(AGENTS_DIR)) return [];
  const out = [];
  for (const ent of readdirSync(AGENTS_DIR, { withFileTypes: true })) {
    if (!ent.isFile() || !ent.name.endsWith(".md")) continue;
    const id = ent.name.replace(/\.md$/, "");
    const { meta } = parseFrontmatter(readFileSync(join(AGENTS_DIR, ent.name), "utf8"));
    out.push({ id: meta.name || id, name: meta.name || id, description: meta.description || "" });
  }
  return out;
}

function readSkillBody(id) {
  let file = join(SKILLS_DIR, id, "SKILL.md");
  if (!existsSync(file)) {
    for (const s of listSkills()) if (s.id === id) { file = join(SKILLS_DIR, s.id, "SKILL.md"); break; }
  }
  if (!existsSync(file)) throw new Error(`skill not found: ${id}`);
  return parseFrontmatter(readFileSync(file, "utf8")).body;
}

function readAgentBody(id) {
  const file = join(AGENTS_DIR, `${id}.md`);
  if (!existsSync(file)) throw new Error(`agent not found: ${id}`);
  return readFileSync(file, "utf8"); // keep frontmatter — it IS the agent definition
}

/* ------------------------------ tool layer ------------------------------ */

const TOOLS = [
  {
    name: "list_skills",
    description:
      "List the skills this plugin can provide on demand (id + one-line description). " +
      "Cheap discovery — call this first, then load_skill(id) for the one you need.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "load_skill",
    description:
      "Return the full instructions (SKILL.md body) for one skill so you can follow its " +
      "workflow now. Loads on demand — nothing is preloaded into your context window.",
    inputSchema: {
      type: "object",
      properties: { id: { type: "string", description: "Skill id from list_skills." } },
      required: ["id"], additionalProperties: false,
    },
  },
  {
    name: "list_agents",
    description:
      "List the specialized sub-agent definitions this plugin ships (id + description). " +
      "Use load_agent(id) to pull one's prompt, then run it via your Task/Agent tool.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "load_agent",
    description:
      "Return one agent's full definition (frontmatter + system prompt). Dispatch it by " +
      "spawning a generic subagent with this text as its instructions.",
    inputSchema: {
      type: "object",
      properties: { id: { type: "string", description: "Agent id from list_agents." } },
      required: ["id"], additionalProperties: false,
    },
  },
];

const text = (s) => ({ content: [{ type: "text", text: s }] });

function callTool(name, args) {
  switch (name) {
    case "list_skills": return text(JSON.stringify(listSkills(), null, 2));
    case "load_skill":  return text(readSkillBody(String(args?.id ?? "")));
    case "list_agents": return text(JSON.stringify(listAgents(), null, 2));
    case "load_agent":  return text(readAgentBody(String(args?.id ?? "")));
    default: throw new Error(`unknown tool: ${name}`);
  }
}

/* --------------------------- resource layer ----------------------------- */

function listResources() {
  const res = [];
  for (const s of listSkills())
    res.push({ uri: `skill://${encodeURIComponent(s.id)}`, name: `Skill: ${s.name}`, description: s.description, mimeType: "text/markdown" });
  for (const a of listAgents())
    res.push({ uri: `agent://${encodeURIComponent(a.id)}`, name: `Agent: ${a.name}`, description: a.description, mimeType: "text/markdown" });
  return res;
}

const RESOURCE_TEMPLATES = [
  { uriTemplate: "skill://{id}", name: "Skill body", description: "Full SKILL.md for a registry skill.", mimeType: "text/markdown" },
  { uriTemplate: "agent://{id}", name: "Agent definition", description: "Full definition for a registry agent.", mimeType: "text/markdown" },
];

function readResource(uri) {
  const m = String(uri).match(/^(skill|agent):\/\/(.+)$/);
  if (!m) throw new Error(`unsupported resource uri: ${uri}`);
  const id = decodeURIComponent(m[2]);
  const body = m[1] === "skill" ? readSkillBody(id) : readAgentBody(id);
  return { contents: [{ uri, mimeType: "text/markdown", text: body }] };
}

/* --------------------------- JSON-RPC plumbing -------------------------- */

const INSTRUCTIONS = [
  "{{DISPLAY_NAME}} is a CAPABILITY REGISTRY. Its skills and agents are NOT in your",
  "`/` menu and NOT preloaded — pull them on demand:",
  "  1. list_skills            -> discover available workflows (id + 1-line desc).",
  "  2. load_skill(id)          -> get a skill's full instructions, then follow them.",
  "  3. list_agents / load_agent(id) -> get a specialized agent's prompt, then run it",
  "     by spawning a subagent (Task tool) with that text as its instructions.",
  "Resources mirror this: read skill://<id> or agent://<id> for the same bodies.",
  "Always list_* first (cheap), then load exactly the one capability you need.",
].join("\n");

function send(msg) { process.stdout.write(JSON.stringify(msg) + "\n"); }
function reply(id, result) { if (id !== undefined && id !== null) send({ jsonrpc: "2.0", id, result }); }
function fail(id, code, message) { if (id !== undefined && id !== null) send({ jsonrpc: "2.0", id, error: { code, message } }); }

function handle(msg) {
  const { id, method, params } = msg;
  try {
    switch (method) {
      case "initialize":
        return reply(id, {
          protocolVersion: PROTOCOL_VERSION,
          capabilities: { tools: {}, resources: {} },
          serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
          instructions: INSTRUCTIONS,
        });
      case "notifications/initialized":
      case "notifications/cancelled":
        return;
      case "ping": return reply(id, {});
      case "tools/list": return reply(id, { tools: TOOLS });
      case "tools/call": return reply(id, callTool(params?.name, params?.arguments ?? {}));
      case "resources/list": return reply(id, { resources: listResources() });
      case "resources/templates/list": return reply(id, { resourceTemplates: RESOURCE_TEMPLATES });
      case "resources/read": return reply(id, readResource(params?.uri));
      default: return fail(id, -32601, `method not found: ${method}`);
    }
  } catch (err) {
    if (method === "tools/call")
      return reply(id, { isError: true, content: [{ type: "text", text: String(err?.message ?? err) }] });
    return fail(id, -32603, String(err?.message ?? err));
  }
}

let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buf += chunk;
  let nl;
  while ((nl = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { log("skipping non-JSON line"); continue; }
    handle(msg);
  }
});
process.stdin.on("end", () => process.exit(0));
log(`ready; registry=${REGISTRY}`);
