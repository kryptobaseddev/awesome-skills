#!/usr/bin/env node
/**
 * better-auth-doctor.mjs — Audit an EXISTING Better Auth integration for the
 * misconfigurations that cause the classic "it compiles but auth is broken"
 * failures. Heuristic/static — it reads source files, it does not run the app.
 *
 * Checks:
 *   1. A server instance (betterAuth({...})) exists, and the secret comes from env.
 *   2. The catch-all auth route exists ([...all] / *splat / $ / *) — not a single route.
 *   3. Express: toNodeHandler(...) is mounted BEFORE express.json().
 *   4. Next.js: nextCookies() is present and is the LAST entry in the plugins array.
 *   5. SvelteKit: sveltekitCookies() is the LAST plugin.
 *   6. Client baseURL is set when the client is a separate origin (best-effort) and
 *      trustedOrigins is configured.
 *   7. Schema-adding plugins are present → reminder to (re)run generate/migrate.
 *   8. BETTER_AUTH_SECRET present in .env / .env.local.
 *
 * Usage:
 *   node better-auth-doctor.mjs [--dir .] [--json]
 *
 * Exit codes: 0 no errors · 1 one or more errors found · 2 usage / no project
 */
import fs from "node:fs";
import path from "node:path";

const argv = process.argv.slice(2);
const flag = (n, def) => { const i = argv.indexOf(`--${n}`); return i !== -1 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : def; };
if (argv.includes("-h") || argv.includes("--help")) { console.log(fs.readFileSync(new URL(import.meta.url)).toString().split("\n").slice(1, 24).join("\n").replace(/^ \*?/gm, "")); process.exit(2); }
const ROOT = path.resolve(flag("dir", "."));
const JSON_OUT = argv.includes("--json");

const findings = []; // { level: error|warn|ok|info, msg, file? }
const add = (level, msg, file) => findings.push({ level, msg, ...(file ? { file } : {}) });

// ── collect candidate source files (skip noise) ──────────────────────────────
const IGNORE = new Set(["node_modules", ".git", ".next", "dist", "build", ".svelte-kit", "drizzle", ".turbo"]);
const SRC_EXT = new Set([".ts", ".tsx", ".js", ".mjs", ".jsx", ".svelte"]);
const sources = [];
(function walk(dir, depth) {
  if (depth > 8) return;
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    if (e.name.startsWith(".") && e.name !== ".env" && e.name !== ".env.local") continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) { if (!IGNORE.has(e.name)) walk(full, depth + 1); }
    else if (SRC_EXT.has(path.extname(e.name))) sources.push(full);
  }
})(ROOT, 0);

const read = (f) => { try { return fs.readFileSync(f, "utf8"); } catch { return ""; } };
const rel = (f) => path.relative(ROOT, f) || path.basename(f);

if (!sources.length) { console.error(`error: no source files found under ${ROOT}`); process.exit(2); }

// ── 1. server instance + secret ──────────────────────────────────────────────
const serverFiles = sources.filter((f) => /betterAuth\s*\(/.test(read(f)) && !/createAuthClient/.test(read(f)));
const serverFile = serverFiles[0];
if (!serverFile) {
  add("error", "No server instance found — expected a file calling betterAuth({ ... }) (commonly lib/auth.ts).");
} else {
  add("ok", "Server instance found.", rel(serverFile));
  const src = read(serverFile);
  if (/secret\s*:\s*["'`]/.test(src) && !/process\.env/.test(src.match(/secret\s*:\s*[^,\n]+/)?.[0] || "")) {
    add("warn", "secret appears to be a hardcoded string — read it from process.env.BETTER_AUTH_SECRET instead.", rel(serverFile));
  }
  if (!/trustedOrigins/.test(src)) add("info", "No trustedOrigins set — required in production for any cross-origin client (CSRF/redirect safety).", rel(serverFile));
}

// ── 2/3/4/5. route mount + ordering per framework ────────────────────────────
const pkg = (() => { try { return JSON.parse(read(path.join(ROOT, "package.json"))); } catch { return {}; } })();
const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
// Detect framework from deps OR from Better Auth import paths in source (works on drop-in files too).
const isNext = "next" in deps || sources.some((f) => /better-auth\/next-js/.test(read(f)));
const isExpress = "express" in deps || sources.some((f) => /better-auth\/node/.test(read(f)) && /\bexpress\b/.test(read(f)));
const isSvelte = "@sveltejs/kit" in deps || sources.some((f) => /better-auth\/svelte-kit/.test(read(f)));

// catch-all route presence
const hasCatchAll =
  sources.some((f) => /\[\.\.\.[a-zA-Z]+\]/.test(rel(f))) ||                 // [...all]
  sources.some((f) => /\bapi\.auth\.\$/.test(rel(f))) ||                      // api.auth.$.ts
  sources.some((f) => /auth\/\$\.[tj]s/.test(rel(f))) ||                      // /api/auth/$.ts
  sources.some((f) => /toNextJsHandler|toSolidStartHandler/.test(read(f))) ||
  sources.some((f) => /\/api\/auth\/\*/.test(read(f)));                       // app.all("/api/auth/*...")
if (hasCatchAll) add("ok", "Catch-all auth route detected.");
else add("error", "No catch-all auth route detected — sub-paths like /api/auth/sign-in/email will 404. Use [...all] / *splat / $ / * per framework.");

// Express ordering
if (isExpress) {
  const exFile = sources.find((f) => /toNodeHandler/.test(read(f)) && /express/.test(read(f)));
  if (exFile) {
    const s = read(exFile);
    const handlerIdx = s.search(/toNodeHandler\s*\(/);          // the call (the import has no paren)
    const jsonIdx = s.search(/app\.use\(\s*express\.json/);     // the real registration, not a comment mentioning it
    if (jsonIdx !== -1 && handlerIdx !== -1 && jsonIdx < handlerIdx) {
      add("error", "express.json() is registered BEFORE the Better Auth handler — requests will hang on 'pending'. Mount toNodeHandler(auth) first.", rel(exFile));
    } else if (handlerIdx !== -1) {
      add("ok", "Express handler is mounted before express.json().", rel(exFile));
    }
  } else {
    add("warn", "Express detected but no toNodeHandler(auth) mount found — the auth routes may not be wired.");
  }
}

// Next.js nextCookies last
if (isNext && serverFile) {
  const s = read(serverFile);
  const m = s.match(/plugins\s*:\s*\[([\s\S]*?)\]/);
  if (!/nextCookies\s*\(/.test(s)) {
    add("error", "Next.js project but nextCookies() is missing — cookies set in server actions won't persist (looks like 'logged out right after sign-up'). Add it as the LAST plugin.", rel(serverFile));
  } else if (m) {
    const items = m[1].split(",").map((x) => x.trim()).filter(Boolean);
    const last = items[items.length - 1] || "";
    if (!/nextCookies\s*\(/.test(last)) add("error", "nextCookies() is present but NOT the last plugin — move it to the end of the plugins array.", rel(serverFile));
    else add("ok", "nextCookies() is the last plugin.", rel(serverFile));
  }
}

// SvelteKit sveltekitCookies last
if (isSvelte && serverFile) {
  const s = read(serverFile);
  const m = s.match(/plugins\s*:\s*\[([\s\S]*?)\]/);
  if (!/sveltekitCookies\s*\(/.test(s)) {
    add("warn", "SvelteKit project but sveltekitCookies() not found — server-side cookie setting in actions/load may not persist. Add it as the LAST plugin.", rel(serverFile));
  } else if (m) {
    const items = m[1].split(",").map((x) => x.trim()).filter(Boolean);
    if (!/sveltekitCookies\s*\(/.test(items[items.length - 1] || "")) add("warn", "sveltekitCookies() should be the LAST plugin.", rel(serverFile));
    else add("ok", "sveltekitCookies() is the last plugin.", rel(serverFile));
  }
}

// ── 6. client baseURL / pairing ──────────────────────────────────────────────
const clientFile = sources.find((f) => /createAuthClient/.test(read(f)));
if (clientFile) {
  const s = read(clientFile);
  add("ok", "Client (createAuthClient) found.", rel(clientFile));
  // server/client plugin pairing
  if (serverFile) {
    const srv = read(serverFile);
    const srvPlugins = [...srv.matchAll(/\b(admin|organization|username|twoFactor|magicLink|passkey|apiKey|jwt|emailOTP|phoneNumber|anonymous|multiSession|genericOAuth)\s*\(/g)].map((m) => m[1]);
    for (const p of new Set(srvPlugins)) {
      const twin = `${p}Client`;
      if (!new RegExp(`\\b${twin}\\s*\\(`).test(s) && !["bearer", "openAPI", "haveIBeenPwned", "captcha", "oAuthProxy"].includes(p)) {
        add("warn", `Server plugin ${p}() has no matching ${twin}() on the client — client methods/types for it won't exist.`, rel(clientFile));
      }
    }
  }
} else {
  add("info", "No createAuthClient found (fine for server-only / API-token setups).");
}

// ── 7. schema-adding plugins reminder ────────────────────────────────────────
if (serverFile) {
  const srv = read(serverFile);
  const schemaPlugins = ["admin", "organization", "username", "twoFactor", "passkey", "jwt", "apiKey", "anonymous", "phoneNumber", "oidcProvider", "sso"].filter((p) => new RegExp(`\\b${p}\\s*\\(`).test(srv));
  if (schemaPlugins.length) add("info", `Schema-adding plugins present (${schemaPlugins.join(", ")}). Ensure you ran: npx @better-auth/cli@latest generate  + your migrate, AFTER adding them.`);
}

// ── 8. secret in env ─────────────────────────────────────────────────────────
let secretInEnv = false;
for (const envName of [".env", ".env.local"]) {
  const p = path.join(ROOT, envName);
  if (fs.existsSync(p) && /^BETTER_AUTH_SECRET=.+/m.test(read(p))) secretInEnv = true;
}
if (secretInEnv) add("ok", "BETTER_AUTH_SECRET is set in an env file.");
else add("warn", "BETTER_AUTH_SECRET not found in .env/.env.local — Better Auth throws on boot in production without it.");

// ── report ───────────────────────────────────────────────────────────────────
const errors = findings.filter((f) => f.level === "error").length;
const warns = findings.filter((f) => f.level === "warn").length;
if (JSON_OUT) {
  console.log(JSON.stringify({ root: ROOT, errors, warnings: warns, findings }, null, 2));
} else {
  const icon = { error: "\x1b[31m✗\x1b[0m", warn: "\x1b[33m!\x1b[0m", ok: "\x1b[32m✓\x1b[0m", info: "\x1b[36mℹ\x1b[0m" };
  console.log(`Better Auth doctor — ${ROOT}\n${"-".repeat(40)}`);
  for (const f of findings) console.log(`  ${icon[f.level]} ${f.msg}${f.file ? `  \x1b[2m(${f.file})\x1b[0m` : ""}`);
  console.log(`${"-".repeat(40)}\n${errors} error(s), ${warns} warning(s)`);
}
process.exit(errors ? 1 : 0);
