#!/usr/bin/env node
/**
 * scaffold-better-auth.mjs — Generate a runnable Better Auth starter.
 *
 * Instead of hand-copying snippets across files, this emits a coherent set of
 * wiring files for a chosen FRAMEWORK × DATABASE (+ optional plugins): the
 * server instance, the mounted catch-all route, the typed client, the DB setup,
 * `.env.example`, `package.json`, and a README with the EXACT generate/migrate
 * commands for that combo.
 *
 * The `--framework express --db sqlite` combo emits a 100%-standalone, runnable
 * demo (Express 5 + better-sqlite3, zero external services). Other combos emit
 * correct drop-in files for an existing app of that framework.
 *
 * Usage:
 *   node scaffold-better-auth.mjs [--out DIR] [--framework F] [--db D]
 *                                 [--plugins a,b,c] [--force] [--dry-run]
 *
 *   --framework  next | express | sveltekit | hono     (default: next)
 *   --db         sqlite | drizzle-pg | drizzle-sqlite | prisma-pg  (default: sqlite)
 *   --plugins    comma list: admin,organization,username,twoFactor,magicLink
 *   --out        output dir   (default: ./better-auth-app)
 *   --force      overwrite a non-empty dir
 *   --dry-run    print the file list without writing
 *
 * Examples:
 *   node scaffold-better-auth.mjs --framework express --db sqlite      # runnable demo
 *   node scaffold-better-auth.mjs --framework next --db drizzle-pg --plugins admin,organization
 */
import fs from "node:fs";
import path from "node:path";

// ── arg parsing ──────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const flag = (n, def) => {
  const i = argv.indexOf(`--${n}`);
  return i !== -1 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : def;
};
const has = (n) => argv.includes(`--${n}`);
if (has("help") || has("h")) {
  console.log(fs.readFileSync(new URL(import.meta.url)).toString().split("\n").slice(1, 30).join("\n").replace(/^ \*?/gm, ""));
  process.exit(2);
}

const FRAMEWORKS = ["next", "express", "sveltekit", "hono"];
const DBS = ["sqlite", "drizzle-pg", "drizzle-sqlite", "prisma-pg"];
const KNOWN_PLUGINS = ["admin", "organization", "username", "twoFactor", "magicLink"];

const opts = {
  out: flag("out", "./better-auth-app"),
  framework: flag("framework", "next"),
  db: flag("db", "sqlite"),
  plugins: (flag("plugins", "") || "").split(",").map((s) => s.trim()).filter(Boolean),
  force: has("force"),
  dryRun: has("dry-run"),
};
if (!FRAMEWORKS.includes(opts.framework)) { console.error(`error: --framework must be ${FRAMEWORKS.join("|")} (got "${opts.framework}")`); process.exit(2); }
if (!DBS.includes(opts.db)) { console.error(`error: --db must be ${DBS.join("|")} (got "${opts.db}")`); process.exit(2); }
const badPlugins = opts.plugins.filter((p) => !KNOWN_PLUGINS.includes(p));
if (badPlugins.length) { console.error(`error: unknown --plugins: ${badPlugins.join(", ")} (known: ${KNOWN_PLUGINS.join(", ")})`); process.exit(2); }

// ── plugin registry (server import + ctor, client import + ctor, needs schema) ─
const PLUGIN_DEFS = {
  admin:        { srv: "admin",        srvCtor: "admin()",        cli: "adminClient",        cliCtor: "adminClient()",        schema: true,  pkg: "better-auth/plugins" },
  organization: { srv: "organization", srvCtor: "organization()", cli: "organizationClient", cliCtor: "organizationClient()", schema: true,  pkg: "better-auth/plugins" },
  username:     { srv: "username",     srvCtor: "username()",     cli: "usernameClient",     cliCtor: "usernameClient()",     schema: true,  pkg: "better-auth/plugins" },
  twoFactor:    { srv: "twoFactor",    srvCtor: "twoFactor()",    cli: "twoFactorClient",    cliCtor: "twoFactorClient()",    schema: true,  pkg: "better-auth/plugins" },
  magicLink:    { srv: "magicLink",    srvCtor: 'magicLink({ sendMagicLink: async ({ email, url }) => { console.log("magic link for", email, url); } })', cli: "magicLinkClient", cliCtor: "magicLinkClient()", schema: false, pkg: "better-auth/plugins" },
};
const chosen = opts.plugins.map((p) => PLUGIN_DEFS[p]);
const anyPluginSchema = chosen.some((p) => p.schema);

// ── server auth.ts pieces ────────────────────────────────────────────────────
const clientSubpath = { next: "better-auth/react", sveltekit: "better-auth/svelte", express: "better-auth/client", hono: "better-auth/client" }[opts.framework];

function serverImports() {
  const lines = ['import { betterAuth } from "better-auth";'];
  if (opts.db === "sqlite") lines.push('import Database from "better-sqlite3";');
  if (opts.db === "drizzle-pg" || opts.db === "drizzle-sqlite") {
    lines.push('import { drizzleAdapter } from "better-auth/adapters/drizzle";');
    lines.push('import { db } from "./db.js";');
  }
  if (opts.db === "prisma-pg") {
    lines.push('import { prismaAdapter } from "better-auth/adapters/prisma";');
    lines.push('import { PrismaClient } from "@prisma/client";');
  }
  if (opts.framework === "next") lines.push('import { nextCookies } from "better-auth/next-js";');
  if (opts.framework === "sveltekit") lines.push('import { sveltekitCookies } from "better-auth/svelte-kit";\nimport { getRequestEvent } from "$app/server";');
  if (chosen.length) lines.push(`import { ${chosen.map((p) => p.srv).join(", ")} } from "better-auth/plugins";`);
  if (opts.db === "prisma-pg") lines.push("\nconst prisma = new PrismaClient();");
  return lines.join("\n");
}
function databaseValue() {
  switch (opts.db) {
    case "sqlite": return 'new Database("better-auth.db")';
    case "drizzle-pg": return 'drizzleAdapter(db, { provider: "pg" })';
    case "drizzle-sqlite": return 'drizzleAdapter(db, { provider: "sqlite" })';
    case "prisma-pg": return 'prismaAdapter(prisma, { provider: "postgresql" })';
  }
}
function serverPlugins() {
  const arr = chosen.map((p) => p.srvCtor);
  if (opts.framework === "next") arr.push("nextCookies()");          // LAST
  if (opts.framework === "sveltekit") arr.push("sveltekitCookies(getRequestEvent)"); // LAST
  return arr;
}
function authServer() {
  const plugins = serverPlugins();
  const pluginLine = plugins.length ? `\n  plugins: [${plugins.join(", ")}], // framework cookie plugin stays LAST` : "";
  return `${serverImports()}

export const auth = betterAuth({
  database: ${databaseValue()},
  emailAndPassword: { enabled: true },
  // socialProviders: { github: { clientId: process.env.GITHUB_CLIENT_ID!, clientSecret: process.env.GITHUB_CLIENT_SECRET! } },
  trustedOrigins: [process.env.BETTER_AUTH_URL ?? "http://localhost:3000"],${pluginLine}
});
`;
}
function authClient() {
  const cliImports = chosen.length ? `\nimport { ${chosen.map((p) => p.cli).join(", ")} } from "better-auth/client/plugins";` : "";
  const cliPlugins = chosen.length ? `\n  plugins: [${chosen.map((p) => p.cliCtor).join(", ")}],` : "";
  // Cross-origin clients (separate API server) need an explicit baseURL; same-origin (Next/SvelteKit) omit it.
  const baseURL = (opts.framework === "express" || opts.framework === "hono") ? `\n  baseURL: "http://localhost:3000",` : "";
  const body = baseURL || cliPlugins ? `{${baseURL}${cliPlugins}\n}` : "{}";
  return `import { createAuthClient } from "${clientSubpath}";${cliImports}

export const authClient = createAuthClient(${body});

export const { signIn, signUp, signOut, useSession } = authClient;
`;
}

// ── drizzle / prisma supporting files ────────────────────────────────────────
function drizzleDb() {
  if (opts.db === "drizzle-pg") {
    return `import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import * as schema from "./auth-schema.js"; // generated by: npx @better-auth/cli@latest generate

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
export const db = drizzle(pool, { schema });
`;
  }
  return `import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";
import * as schema from "./auth-schema.js"; // generated by: npx @better-auth/cli@latest generate

const sqlite = new Database("better-auth.db");
export const db = drizzle(sqlite, { schema });
`;
}
function drizzleConfig() {
  const dialect = opts.db === "drizzle-pg" ? "postgresql" : "sqlite";
  const creds = opts.db === "drizzle-pg" ? `dbCredentials: { url: process.env.DATABASE_URL! },` : `dbCredentials: { url: "better-auth.db" },`;
  return `import { defineConfig } from "drizzle-kit";
export default defineConfig({
  schema: "./src/auth-schema.ts",
  out: "./drizzle",
  dialect: "${dialect}",
  ${creds}
});
`;
}
function prismaSchema() {
  return `// Run \`npx @better-auth/cli@latest generate\` to append the Better Auth models,
// then \`npx prisma migrate dev\`.
generator client { provider = "prisma-client-js" }
datasource db { provider = "postgresql"; url = env("DATABASE_URL") }
`;
}

// ── framework mount + demo files ─────────────────────────────────────────────
function files() {
  const f = {};
  const pkg = packageJson();
  f["package.json"] = JSON.stringify(pkg, null, 2) + "\n";
  f[".gitignore"] = "node_modules\n.env\nbetter-auth.db\n.next\nbuild\ndist\ndrizzle\n";
  f[".env.example"] = envExample();
  f["src/auth.ts"] = authServer();
  f["src/auth-client.ts"] = authClient();
  if (opts.db === "drizzle-pg" || opts.db === "drizzle-sqlite") { f["src/db.ts"] = drizzleDb(); f["drizzle.config.ts"] = drizzleConfig(); }
  if (opts.db === "prisma-pg") f["prisma/schema.prisma"] = prismaSchema();

  if (opts.framework === "next") {
    f["app/api/auth/[...all]/route.ts"] = `import { auth } from "@/src/auth";\nimport { toNextJsHandler } from "better-auth/next-js";\n\nexport const { POST, GET } = toNextJsHandler(auth);\n`;
  } else if (opts.framework === "sveltekit") {
    f["src/hooks.server.ts"] = `import { auth } from "./auth";\nimport { svelteKitHandler } from "better-auth/svelte-kit";\nimport { building } from "$app/environment";\n\nexport async function handle({ event, resolve }) {\n  return svelteKitHandler({ event, resolve, auth, building });\n}\n`;
  } else if (opts.framework === "hono") {
    f["src/server.ts"] = `import { Hono } from "hono";\nimport { cors } from "hono/cors";\nimport { serve } from "@hono/node-server";\nimport { auth } from "./auth.js";\n\nconst app = new Hono();\napp.use("/api/auth/*", cors({ origin: "http://localhost:5173", credentials: true, allowHeaders: ["Content-Type", "Authorization"], allowMethods: ["GET", "POST", "OPTIONS"] }));\napp.on(["POST", "GET"], "/api/auth/*", (c) => auth.handler(c.req.raw));\napp.get("/api/me", async (c) => c.json(await auth.api.getSession({ headers: c.req.raw.headers })));\n\nserve({ fetch: app.fetch, port: 3000 }, (i) => console.log(\`http://localhost:\${i.port}\`));\n`;
  } else if (opts.framework === "express") {
    // fully-runnable standalone demo
    f["src/server.ts"] = `import express from "express";\nimport { toNodeHandler, fromNodeHeaders } from "better-auth/node";\nimport { auth } from "./auth.js";\n\nconst app = express();\n\n// Better Auth handler MUST be mounted BEFORE express.json() (Express 5 wildcard = *splat).\napp.all("/api/auth/*splat", toNodeHandler(auth));\n\napp.use(express.json());\napp.use(express.static("public"));\n\napp.get("/api/me", async (req, res) => {\n  const session = await auth.api.getSession({ headers: fromNodeHeaders(req.headers) });\n  res.json(session ?? { session: null });\n});\n\nconst port = Number(process.env.PORT ?? 3000);\napp.listen(port, () => console.log(\`Better Auth demo on http://localhost:\${port}\`));\n`;
    f["public/index.html"] = expressDemoHtml();
  }
  f["README.md"] = readme();
  return f;
}

function packageJson() {
  const deps = { "better-auth": "^1.6.0" };
  if (opts.db === "sqlite") deps["better-sqlite3"] = "^12.0.0";
  if (opts.db === "drizzle-pg") { deps["drizzle-orm"] = "^0.36.0"; deps["pg"] = "^8.13.0"; }
  if (opts.db === "drizzle-sqlite") { deps["drizzle-orm"] = "^0.36.0"; deps["better-sqlite3"] = "^12.0.0"; }
  if (opts.db === "prisma-pg") { deps["@prisma/client"] = "^6.0.0"; }
  const dev = { typescript: "^5.6.0", tsx: "^4.19.0" };
  if (opts.db.startsWith("drizzle")) dev["drizzle-kit"] = "^0.30.0";
  if (opts.db === "prisma-pg") dev["prisma"] = "^6.0.0";
  const scripts = {};
  if (opts.framework === "express" || opts.framework === "hono") {
    // node --env-file loads .env natively (Node 20.6+); --import tsx runs the TS directly.
    scripts.dev = "node --env-file=.env --watch --import tsx src/server.ts";
    scripts.start = "node --env-file=.env --import tsx src/server.ts";
    deps["@hono/node-server"] = opts.framework === "hono" ? "^1.13.0" : undefined;
    deps["hono"] = opts.framework === "hono" ? "^4.6.0" : undefined;
    deps["express"] = opts.framework === "express" ? "^5.0.0" : undefined;
    Object.keys(deps).forEach((k) => deps[k] === undefined && delete deps[k]);
  } else {
    scripts.dev = `echo 'Add these files to your ${opts.framework} app, then run your framework dev server.'`;
  }
  return { name: path.basename(path.resolve(opts.out)), private: true, type: "module", scripts, dependencies: deps, devDependencies: dev };
}

function envExample() {
  const lines = [
    "# Generate: openssl rand -base64 32   (or: npx @better-auth/cli@latest secret)",
    "BETTER_AUTH_SECRET=replace-me-with-32+-bytes-of-entropy",
    `BETTER_AUTH_URL=http://localhost:3000`,
  ];
  if (opts.db === "drizzle-pg" || opts.db === "prisma-pg") lines.push("DATABASE_URL=postgres://user:password@localhost:5432/app");
  lines.push("# GITHUB_CLIENT_ID=", "# GITHUB_CLIENT_SECRET=");
  return lines.join("\n") + "\n";
}

function migrateSteps() {
  if (opts.db === "sqlite") return "npx @better-auth/cli@latest migrate    # built-in Kysely applies the schema directly";
  if (opts.db.startsWith("drizzle")) return "npx @better-auth/cli@latest generate   # writes src/auth-schema.ts\nnpx drizzle-kit generate && npx drizzle-kit migrate";
  if (opts.db === "prisma-pg") return "npx @better-auth/cli@latest generate   # appends models to prisma/schema.prisma\nnpx prisma migrate dev";
}

function readme() {
  const runnable = opts.framework === "express" || opts.framework === "hono";
  const pluginNote = anyPluginSchema ? "\n\n> Some chosen plugins add tables/columns — the schema step above already covers them. If you add MORE plugins later, re-run it." : "";
  const runSection = runnable
    ? `4. Start it:\n   \`\`\`bash\n   npm run dev\n   \`\`\`${opts.framework === "express" ? "\n   Open http://localhost:3000 — the demo page lets you sign up / sign in / sign out and shows the live session." : "\n   The API serves /api/auth/* and /api/me."}`
    : `4. These files are drop-ins for an existing ${opts.framework} project. Copy \`src/auth.ts\`, \`src/auth-client.ts\`, and the route handler into your app (adjust import aliases), then run your framework's dev server.`;
  return `# Better Auth starter — ${opts.framework} + ${opts.db}${opts.plugins.length ? " + " + opts.plugins.join(", ") : ""}

Generated by the \`better-auth\` skill's scaffolder. The server instance lives in
\`src/auth.ts\`; the typed client in \`src/auth-client.ts\`; the catch-all route is
mounted per ${opts.framework} convention.

## Setup

1. Install deps:
   \`\`\`bash
   npm install
   \`\`\`
2. Create \`.env\` from the example and set a real secret:
   \`\`\`bash
   cp .env.example .env
   # then: openssl rand -base64 32  → paste into BETTER_AUTH_SECRET
   \`\`\`
3. Create the database tables:
   \`\`\`bash
   ${migrateSteps()}
   \`\`\`${pluginNote}
${runSection}

## Notes
- Auth routes are served at \`/api/auth/*\` (catch-all). Don't collapse it to a single route.
- ${opts.framework === "express" ? "The handler is mounted BEFORE `express.json()` — keep it that way or requests hang." : opts.framework === "next" ? "`nextCookies()` is the LAST plugin so server actions can set cookies." : opts.framework === "sveltekit" ? "`sveltekitCookies` is the LAST plugin; the handler runs in `src/hooks.server.ts`." : "CORS is registered before the auth route."}
- Read the session server-side with \`auth.api.getSession({ headers })\` — never trust a cookie check alone for authorization.
- Add social login by filling \`socialProviders\` in \`src/auth.ts\` and the matching \`.env\` creds (callback URL: \`/api/auth/callback/<provider>\`).

See the \`better-auth\` skill references for plugins, RBAC, and production hardening.
`;
}

function expressDemoHtml() {
  return `<!doctype html><html><head><meta charset="utf-8"><title>Better Auth demo</title>
<style>body{font-family:system-ui;max-width:32rem;margin:3rem auto;padding:0 1rem}input,button{display:block;width:100%;padding:.5rem;margin:.25rem 0}pre{background:#f4f4f5;padding:1rem;border-radius:.5rem;overflow:auto}</style></head>
<body><h1>Better Auth demo</h1>
<input id="name" placeholder="name (sign up)"><input id="email" placeholder="email"><input id="password" type="password" placeholder="password">
<button onclick="su()">Sign up</button><button onclick="si()">Sign in</button><button onclick="so()">Sign out</button><button onclick="me()">Who am I?</button>
<pre id="out">{}</pre>
<script type="module">
import { createAuthClient } from "https://esm.sh/better-auth/client";
const auth = createAuthClient({ baseURL: location.origin });
const out = (x)=>document.getElementById("out").textContent = JSON.stringify(x,null,2);
const v = (id)=>document.getElementById(id).value;
window.su = async()=>out(await auth.signUp.email({ name:v("name"), email:v("email"), password:v("password") }));
window.si = async()=>out(await auth.signIn.email({ email:v("email"), password:v("password") }));
window.so = async()=>out(await auth.signOut());
window.me = async()=>out(await (await fetch("/api/me")).json());
</script></body></html>
`;
}

// ── write ────────────────────────────────────────────────────────────────────
const tree = files();
const outDir = path.resolve(opts.out);
if (opts.dryRun) {
  console.log(`Would scaffold ${opts.framework} + ${opts.db}${opts.plugins.length ? " + " + opts.plugins.join(",") : ""} into ${outDir}:`);
  for (const rel of Object.keys(tree).sort()) console.log("  " + rel);
  process.exit(0);
}
if (fs.existsSync(outDir) && fs.readdirSync(outDir).length && !opts.force) {
  console.error(`error: ${outDir} is not empty. Use --force to overwrite, or pick another --out.`);
  process.exit(2);
}
for (const [rel, content] of Object.entries(tree)) {
  const dest = path.join(outDir, rel);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, content);
}
console.log(`✓ Scaffolded ${opts.framework} + ${opts.db}${opts.plugins.length ? " + " + opts.plugins.join(",") : ""} into ${outDir}`);
console.log(`  Next: cd ${opts.out} && npm install && cp .env.example .env  (set BETTER_AUTH_SECRET)`);
console.log(`  Then follow ${path.join(opts.out, "README.md")} for the generate/migrate + run steps.`);
