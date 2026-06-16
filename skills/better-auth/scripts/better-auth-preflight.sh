#!/usr/bin/env bash
# better-auth-preflight.sh — Verify a project is ready for a Better Auth
# (better-auth.com) integration BEFORE you write code, so the first failure
# points at config, not a bug.
#
# It is framework- and database-agnostic. From the nearest package.json it
# detects which web framework and ORM you use and prints the EXACT handler /
# adapter you should reach for — so you never wire the wrong integration.
#
# Checks:
#   1. node >= 18 (Better Auth needs Web Crypto + modern runtime)
#   2. better-auth is installed (or tells you the install command)
#   3. BETTER_AUTH_SECRET is set and long enough (>= 32 bytes of entropy);
#      offers to generate one
#   4. BETTER_AUTH_URL / base URL presence (warn only — optional in dev)
#   5. A database connection string is reachable in the env (soft check)
#   6. Framework detection  -> the right server handler + catch-all route
#   7. ORM detection        -> the right database adapter import
#
# Usage:
#   bash better-auth-preflight.sh            # checks + detection
#   bash better-auth-preflight.sh --gen-secret   # also print a fresh secret
#   bash better-auth-preflight.sh --dir ./apps/web   # check a sub-package
#
# Exit codes: 0 ready · 2 usage · 4 missing/old node · 6 secret problem
set -uo pipefail

DIR="."
GEN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --gen-secret) GEN=1 ;;
    --dir) shift; DIR="${1:-.}" ;;
    -h|--help) sed -n '2,33p' "$0"; exit 2 ;;
    *) echo "unknown arg: $1 (try --help)"; exit 2 ;;
  esac
  shift
done

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }
hint() { printf '    \033[2m%s\033[0m\n' "$1"; }

RC=0

echo "Better Auth preflight"
echo "---------------------"

# 1. node ----------------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  bad "node not found — install Node 18+ (https://nodejs.org)"; exit 4
fi
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if [ "${NODE_MAJOR:-0}" -ge 18 ]; then
  ok "node $(node --version) (>= 18)"
else
  bad "node $(node --version) is too old — Better Auth needs Node 18+"; RC=4
fi

# Locate the package.json that anchors detection ------------------------------
PKG=""
if [ -f "$DIR/package.json" ]; then
  PKG="$DIR/package.json"
fi

dep_has() { # dep_has <name> -> 0 if name appears as a dependency key
  [ -n "$PKG" ] && node -e '
    const fs=require("fs");const p=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
    const d={...p.dependencies,...p.devDependencies,...p.peerDependencies};
    process.exit(d&&Object.prototype.hasOwnProperty.call(d,process.argv[2])?0:1);
  ' "$PKG" "$1" 2>/dev/null
}

# 2. better-auth installed -----------------------------------------------------
if [ -d "$DIR/node_modules/better-auth" ] || dep_has better-auth; then
  ok "better-auth is a project dependency"
else
  warn "better-auth not found in $DIR"
  hint "npm install better-auth        (or: pnpm add / bun add / yarn add)"
fi

# 3. secret --------------------------------------------------------------------
SECRET="${BETTER_AUTH_SECRET:-}"
if [ -z "$SECRET" ] && [ -f "$DIR/.env" ]; then
  SECRET="$(grep -E '^BETTER_AUTH_SECRET=' "$DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"'' )"
fi
if [ -z "$SECRET" ]; then
  bad "BETTER_AUTH_SECRET is not set"
  hint "Generate one (see below) and add it to .env — sessions are signed with it."
  RC=6
elif [ "${#SECRET}" -lt 32 ]; then
  warn "BETTER_AUTH_SECRET is only ${#SECRET} chars — use >= 32 bytes of entropy"
  RC=6
else
  ok "BETTER_AUTH_SECRET is set (${#SECRET} chars)"
fi

# 4. base URL ------------------------------------------------------------------
if [ -n "${BETTER_AUTH_URL:-}" ]; then
  ok "BETTER_AUTH_URL = ${BETTER_AUTH_URL}"
else
  warn "BETTER_AUTH_URL not set (optional in dev; REQUIRED in production for correct cookies/redirects)"
fi

# 5. database url (soft) -------------------------------------------------------
DB_FOUND=0
for v in DATABASE_URL POSTGRES_URL DATABASE_URI MYSQL_URL TURSO_DATABASE_URL MONGODB_URI; do
  if [ -n "${!v:-}" ]; then ok "database env present: $v"; DB_FOUND=1; break; fi
done
[ "$DB_FOUND" -eq 0 ] && warn "no database connection env detected (DATABASE_URL/etc.) — set one before running the CLI"

# 6. framework detection -------------------------------------------------------
echo
echo "Detected stack"
echo "--------------"
if [ -z "$PKG" ]; then
  warn "no package.json at $DIR — skipping framework/ORM detection"
else
  FW="(unknown)"; ROUTE=""; HANDLER=""
  if   dep_has next;            then FW="Next.js";       HANDLER='toNextJsHandler from "better-auth/next-js"'; ROUTE='app/api/auth/[...all]/route.ts  (+ add nextCookies() LAST in plugins)'
  elif dep_has @sveltejs/kit;  then FW="SvelteKit";     HANDLER='svelteKitHandler from "better-auth/svelte-kit"'; ROUTE='src/hooks.server.ts  (+ sveltekitCookies plugin)'
  elif dep_has nuxt;           then FW="Nuxt";          HANDLER='auth.handler in a catch-all event handler'; ROUTE='server/api/auth/[...all].ts'
  elif dep_has @tanstack/react-start || dep_has @tanstack/start; then FW="TanStack Start"; HANDLER='auth.handler via createFileRoute("/api/auth/$").server.handlers (+ tanstackStartCookies LAST)'; ROUTE='src/routes/api/auth/$.ts'
  elif dep_has @solidjs/start; then FW="SolidStart";    HANDLER='auth.handler (toSolidStartHandler)'; ROUTE='src/routes/api/auth/[...all].ts'
  elif dep_has astro;          then FW="Astro";         HANDLER='auth.handler from your auth instance'; ROUTE='src/pages/api/auth/[...all].ts  (export prerender=false)'
  elif dep_has @remix-run/node || dep_has react-router; then FW="Remix / React Router"; HANDLER='auth.handler in a resource route'; ROUTE='app/routes/api.auth.$.ts'
  elif dep_has hono;           then FW="Hono";          HANDLER='auth.handler on app.on(["POST","GET"], "/api/auth/*", ...)'; ROUTE='register before other routes'
  elif dep_has elysia;         then FW="Elysia";        HANDLER='mount(auth.handler) or a wildcard route'; ROUTE='mount("/api/auth", auth.handler)'
  elif dep_has fastify;        then FW="Fastify";       HANDLER='auth.handler bridged to Fastify req/reply'; ROUTE='all "/api/auth/*"'
  elif dep_has express;        then FW="Express";       HANDLER='toNodeHandler from "better-auth/node"'; ROUTE='app.all("/api/auth/*splat", toNodeHandler(auth)) — mount BEFORE express.json()'
  fi
  ok "framework: $FW"
  [ -n "$HANDLER" ] && hint "handler: $HANDLER"
  [ -n "$ROUTE" ]   && hint "route:   $ROUTE"

  ORM="(none detected — Better Auth can use a raw pg/mysql2/better-sqlite3 pool via Kysely)"
  if   dep_has drizzle-orm;    then ORM='drizzleAdapter(db, { provider: "pg"|"mysql"|"sqlite", schema })  from "better-auth/adapters/drizzle"'
  elif dep_has @prisma/client; then ORM='prismaAdapter(prisma, { provider: "postgresql"|"mysql"|"sqlite" })  from "better-auth/adapters/prisma"'
  elif dep_has mongodb;        then ORM='mongodbAdapter(db)  from "better-auth/adapters/mongodb"'
  fi
  hint "adapter: $ORM"
  echo
  hint "Next: define auth, then run  npx @better-auth/cli@latest generate   (writes schema), then your ORM migrate."
fi

# secret generator -------------------------------------------------------------
if [ "$GEN" -eq 1 ]; then
  echo
  echo "Fresh secret (add to .env as BETTER_AUTH_SECRET):"
  node -e 'console.log(require("crypto").randomBytes(32).toString("base64url"))'
fi

echo
if [ "$RC" -eq 0 ]; then echo "preflight OK"; else echo "preflight found issues (exit $RC)"; fi
exit "$RC"
