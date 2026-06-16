---
name: better-auth
description: "Implement Better Auth (better-auth.com) — the framework-agnostic TypeScript authentication library — across ANY stack: Next.js, SvelteKit, Nuxt, SolidStart, Remix/React Router, Astro, TanStack Start, Express, Hono, Elysia, Fastify, or raw Node. Covers the betterAuth() server instance, database adapters (Drizzle, Prisma, Kysely/raw pg·mysql·sqlite, MongoDB), the CLI (generate/migrate), the client SDK (React, Vue, Svelte, Solid, vanilla), email/password + social/OAuth login (Google, GitHub, Apple…), account linking, sessions, and plugins (2FA, magic link, email OTP, passkey, username, organization multi-tenancy, admin, API keys, JWT/bearer, RBAC via access control). Use whenever the user adds, configures, scaffolds, or debugs Better Auth, sign-in/sign-up, sessions, OAuth, 2FA, multi-tenant orgs, or role-based permissions in a TS/JS app — even if they only say 'better auth', 'add login', or 'auth'. Ships a preflight, a scaffolder, and a setup doctor."
license: MIT
compatibility: >-
  Better Auth v1.x (verified runnable against v1.6.19, mid-2026). Needs Node 18+
  (Web Crypto) / Bun / Deno and a TypeScript project. One database: Postgres,
  MySQL, or SQLite via Drizzle/Prisma/Kysely-or-raw-driver, or MongoDB. Works
  with any of the listed web frameworks. Bundled scripts need Node 18+ and bash;
  the scaffolder emits a runnable Next.js, Express, SvelteKit, or Hono starter
  (the Express/Hono demos' npm scripts use Node 20.6+'s --env-file).
inputs:
  - name: BETTER_AUTH_SECRET
    description: "Random secret used to sign/encrypt/hash sessions and tokens. REQUIRED — Better Auth throws on boot in production if unset. Generate with `openssl rand -base64 32` or `npx @better-auth/cli@latest secret`. Read from process.env if not passed as `secret` in config."
    required: true
  - name: BETTER_AUTH_URL
    description: "Base URL of the app, e.g. http://localhost:3000 (prod: https://yourapp.com). Used for cookies, OAuth redirects, and trusted-origin checks. Optional in dev (inferred), REQUIRED in production. Equivalent to the `baseURL` config option."
    required: false
  - name: DATABASE_URL
    description: "Connection string for your database (Postgres/MySQL/SQLite/Mongo). Name varies by host (POSTGRES_URL, TURSO_DATABASE_URL, MONGODB_URI…). Needed by the adapter and the CLI. SQLite may be a file path instead."
    required: false
metadata:
  author: github.com/kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-06-15 18:20:00"
  category: auth
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
---

# Better Auth — cross-stack authentication for TypeScript

Better Auth is a **framework-agnostic** auth library: one `betterAuth()` server
instance owns the logic, a tiny per-framework adapter mounts it as HTTP routes,
and a typed client SDK talks to those routes. The same core works in Next.js,
SvelteKit, Nuxt, Solid, Remix, Astro, TanStack Start, Express, Hono, Elysia,
Fastify, or raw Node — only the **mount** and the **client import** change.

This skill keeps the cross-cutting rules here and pushes the per-framework,
per-adapter, and per-plugin detail into `references/`. Read the relevant
reference before writing integration code — the import paths and method names
are load-bearing and easy to get subtly wrong.

## The mental model (4 moving parts)

```
.env  →  auth.ts (server instance)  →  mount handler (/api/auth/*)  →  auth-client.ts (client SDK)
secret      betterAuth({db, ...})        toNextJsHandler / auth.handler     createAuthClient({...})
```

1. **Server instance** (`auth.ts`/`lib/auth.ts`): `betterAuth({ database, emailAndPassword, socialProviders, plugins })`. One file, the source of truth.
2. **Database**: an adapter (Drizzle/Prisma/Mongo) or a raw driver (built-in Kysely). Then **generate the schema** and migrate.
3. **Mount**: expose `auth.handler` at the catch-all route `/api/auth/*` using your framework's adapter.
4. **Client**: `createAuthClient` from the subpath for your front-end framework; call `signIn`/`signUp`/`useSession`.

## Facts that prevent broken work

Read this first — each row is a real failure integrators hit.

| Fact | Consequence |
|---|---|
| **`BETTER_AUTH_SECRET` is mandatory in prod** | Boot throws without it. Generate `openssl rand -base64 32`. Also set `BETTER_AUTH_URL` (baseURL) or cookies/redirects break in prod. |
| **The route MUST be a catch-all at `/api/auth/*`** | A single non-catch-all route (e.g. `/api/auth/route.ts`) silently 404s sub-paths like `/api/auth/sign-in/email`. Use `[...all]`, `*`, `$`, or `*splat` per framework. |
| **Express: mount the handler BEFORE `express.json()`** | `toNodeHandler(auth)` must run before any body parser, or the client API hangs on "pending". Scope `express.json()` to non-auth routes. (Express v5 wildcard is `/api/auth/*splat`.) |
| **Next.js server actions need `nextCookies()` as the LAST plugin** | Without it, cookies set inside server actions (e.g. server-side `signInEmail`) never reach the browser → "logged out right after sign-up". |
| **`generate` ≠ `migrate`** | `npx @better-auth/cli@latest generate` writes the schema for your ORM; only the **built-in Kysely** adapter can `migrate` directly. Drizzle/Prisma must run **their own** migrate after generate. |
| **Re-run `generate` after adding a schema plugin** | twoFactor, username, admin, organization, passkey, jwt, apiKey… add tables/columns. Forgetting to regenerate = "column/table does not exist" at runtime — the #1 plugin error. |
| **Server `auth.api.*` calls REQUIRE `headers`** | `auth.api.getSession({ headers })` — pass the request headers (Node: `fromNodeHeaders(req.headers)`). No headers = always null session. |
| **Client `baseURL` must match the server origin + `basePath`** | If the client is on a different origin, set `createAuthClient({ baseURL })` and add that origin to server `trustedOrigins`, or every call fails CORS/CSRF. |
| **Server plugin + client plugin come in pairs** | A server plugin from `better-auth/plugins` needs its client twin from `better-auth/client/plugins` (e.g. `organization()` ↔ `organizationClient()`), or the client methods/types won't exist. |
| **`passkey` (v1.4+), `sso` & `apiKey` (v1.5+) ship as scoped packages** | Import from `@better-auth/passkey`, `@better-auth/sso`, `@better-auth/api-key` (client: `.../client`). Before those versions they lived in `better-auth/plugins`. Check the installed version. |
| **Middleware cookie checks are optimistic, not authoritative** | `getSessionCookie()` only checks a cookie exists — never trust it for real authz. Do the real check with `auth.api.getSession()` in the page/route/loader. |
| **Cross-subdomain cookies need explicit config** | app.x.com ↔ api.x.com: set `advanced.crossSubDomainCookies` + `defaultCookieAttributes { sameSite:'none', secure:true, partitioned:true }`. "Works locally, breaks in prod" is almost always this. |

## Preflight

Confirm the environment + detect the right handler/adapter BEFORE writing code,
so the first failure points at config, not a bug:

```bash
bash scripts/better-auth-preflight.sh                 # node, secret, env + framework/ORM detection
bash scripts/better-auth-preflight.sh --gen-secret    # also print a fresh BETTER_AUTH_SECRET
bash scripts/better-auth-preflight.sh --dir ./apps/web # check a sub-package in a monorepo
```

It reads the nearest `package.json` and tells you the exact handler import and
database adapter for the stack it finds.

## Build it in one command (scaffold)

The fastest path to a working setup is to **generate** it, then customize. The
scaffolder emits a complete, runnable starter (server instance + mounted route +
client + schema + `.env.example`) wired for your framework and database:

```bash
node scripts/scaffold-better-auth.mjs --out ./my-auth --framework next --db drizzle-pg
node scripts/scaffold-better-auth.mjs --framework express --db sqlite --plugins admin,organization
node scripts/scaffold-better-auth.mjs --help     # all flags; --dry-run previews
```

Then: `cd my-auth && npm install`, fill `.env`, run the CLI generate + migrate
shown in the emitted README, and `npm run dev`. The output is a correct
skeleton, not a black box — refine it with the references below.

## Canonical quick start (Next.js App Router + Drizzle/Postgres)

The most common stack, end to end. Swap the two starred lines per the
references for any other framework/database.

```ts
// lib/auth.ts — the server instance (source of truth)
import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";   // ★ database
import { nextCookies } from "better-auth/next-js";
import { db } from "@/db";

export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "pg" }),              // ★ provider: pg|mysql|sqlite
  emailAndPassword: { enabled: true },
  plugins: [nextCookies()],   // MUST stay LAST so server actions can set cookies
});
```

```ts
// app/api/auth/[...all]/route.ts — mount the catch-all handler
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";
export const { POST, GET } = toNextJsHandler(auth);
```

```ts
// lib/auth-client.ts — the typed client
import { createAuthClient } from "better-auth/react";            // ★ framework subpath
export const authClient = createAuthClient();                   // same origin → no baseURL needed
```

```bash
# create the tables: generate the Drizzle schema, then migrate with drizzle-kit
npx @better-auth/cli@latest generate     # writes auth-schema.ts
npx drizzle-kit generate && npx drizzle-kit migrate
```

```tsx
// use it (React) — { data, error } everywhere; useSession is reactive
const { data: session, isPending } = authClient.useSession();
await authClient.signUp.email({ email, password, name });
await authClient.signIn.email({ email, password, callbackURL: "/dashboard" });
await authClient.signOut();
```

```ts
// protect a server route / page — the AUTHORITATIVE check
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
const session = await auth.api.getSession({ headers: await headers() });
if (!session) redirect("/sign-in");   // session = { user, session }
```

## Choose your pieces (then read the reference)

**Framework** — exact mount + route path + client + session read + route protection live in `references/frameworks.md`:

| Framework | Mount | Route file |
|---|---|---|
| Next.js (App) | `toNextJsHandler(auth)` from `better-auth/next-js` + `nextCookies()` last | `app/api/auth/[...all]/route.ts` |
| Express / Node | `toNodeHandler(auth)` from `better-auth/node`, **before** `express.json()` | `app.all("/api/auth/*splat", …)` |
| SvelteKit | `svelteKitHandler({event,resolve,auth,building})` + `sveltekitCookies` last | `src/hooks.server.ts` |
| Nuxt | `auth.handler(toWebRequest(event))` | `server/api/auth/[...all].ts` |
| SolidStart | `toSolidStartHandler(auth)` from `better-auth/solid-start` | `src/routes/api/auth/[...all].ts` |
| Remix / RR7 | `auth.handler(request)` in `loader` + `action` | `app/routes/api.auth.$.ts` |
| Astro | `export const ALL: APIRoute = (c) => auth.handler(c.request)` | `src/pages/api/auth/[...all].ts` |
| TanStack Start | `createFileRoute("/api/auth/$")` server handlers + `tanstackStartCookies` | `src/routes/api/auth/$.ts` |
| Hono | `app.on(["POST","GET"], "/api/auth/*", c => auth.handler(c.req.raw))` | (CORS first) |
| Elysia | `new Elysia().mount(auth.handler)` | — |
| Fastify | manual `Request` adapt via `fromNodeHeaders` | `url: "/api/auth/*"` |

**Database** — adapters, schema, generate/migrate, custom table names, numeric IDs in `references/database-adapters.md`:

| Database / ORM | `database:` value |
|---|---|
| Drizzle | `drizzleAdapter(db, { provider: "pg"\|"mysql"\|"sqlite", schema })` |
| Prisma | `prismaAdapter(prisma, { provider: "postgresql"\|"mysql"\|"sqlite" })` |
| MongoDB | `mongodbAdapter(db, { client })` |
| Raw Postgres/MySQL/SQLite (built-in Kysely — supports `migrate`) | `new Pool(...)` / `createPool(...)` / `new Database(...)` |

**Client** — `createAuthClient` subpath + how `useSession` differs per framework, error handling, custom-field typing in `references/client.md`.

**Plugins** — the full catalog (2FA, magic link, email OTP, passkey, username, anonymous, phone, organization, admin, apiKey, jwt, bearer, multiSession, oneTap, captcha, haveIBeenPwned, oidcProvider, sso…) with exact imports, methods, and which add schema in `references/plugins.md`.

## Where to go next

| Task | Reference |
|---|---|
| `betterAuth()` full config, env, the CLI, `auth.api.*`, type inference | `references/core-server-config.md` |
| Pick + wire a database adapter; schema, `generate` vs `migrate`, IDs | `references/database-adapters.md` |
| Mount the handler + read the session + protect routes in **your** framework | `references/frameworks.md` |
| `createAuthClient`, `useSession` per framework, `{ data, error }`, `fetchOptions` | `references/client.md` |
| Add a plugin (2FA, passkey, magic link, jwt, bearer, username…) | `references/plugins.md` |
| Social/OAuth login (Google/GitHub/Apple…), account linking, `genericOAuth` | `references/social-oauth.md` |
| Multi-tenant **organizations**, **admin** panel, **RBAC** via access control | `references/organization-admin-rbac.md` |
| Sessions, cookies, cross-subdomain, `trustedOrigins`, rate limit, Redis, hooks, prod | `references/security-and-production.md` |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/better-auth-preflight.sh` | Check node/secret/env and **detect** the right handler + adapter from `package.json`. `--gen-secret`, `--dir`. |
| `scripts/scaffold-better-auth.mjs` | **Generate a runnable starter** (server + route + client + schema + env) for `--framework` × `--db` (+ optional `--plugins`). `--dry-run`. |
| `scripts/better-auth-doctor.mjs` | Audit an EXISTING project for the common misconfigurations (handler-before-json, nextCookies-last, catch-all route, client baseURL, missing secret, un-regenerated schema). |

## Common mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | `express.json()` before the auth handler | Mount `toNodeHandler(auth)` first; the request hangs otherwise. |
| 2 | Non-catch-all auth route | Use the catch-all (`[...all]`/`*`/`$`/`*splat`); sub-paths 404 otherwise. |
| 3 | `nextCookies()` missing or not last | Put it last in `plugins`; server-action cookies won't persist without it. |
| 4 | Calling `migrate` for Drizzle/Prisma | `migrate` is Kysely-only. Run `generate`, then the ORM's own migrate. |
| 5 | Adding a plugin but not regenerating schema | Re-run `generate` + migrate; missing columns/tables crash at runtime. |
| 6 | `auth.api.getSession()` without `headers` | Always pass headers (Node: `fromNodeHeaders(req.headers)`). |
| 7 | Trusting `getSessionCookie()` for authz | It's optimistic only; do the real `auth.api.getSession()` check. |
| 8 | Client on another origin, no `trustedOrigins` | Set client `baseURL` + add the origin to server `trustedOrigins`. |
| 9 | Server plugin without its client twin (or wrong order) | Register both halves; keep `ac`/`roles` identical on server and client. |
| 10 | Importing `passkey`/`sso`/`apiKey` from `better-auth/plugins` on v1.5+ | Import from the scoped `@better-auth/*` package for your version. |

## Resources

- Docs: https://better-auth.com/docs · LLM index: https://better-auth.com/llms.txt
- Options reference: https://better-auth.com/docs/reference/options
- CLI: https://better-auth.com/docs/concepts/cli · Plugins: https://better-auth.com/docs/plugins
- GitHub: https://github.com/better-auth/better-auth
