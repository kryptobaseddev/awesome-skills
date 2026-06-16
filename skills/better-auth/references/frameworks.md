# Better Auth — per-framework integration

The single most important reference: for each framework, the exact mount snippet + route file path, how to read the session server-side, and how to protect routes/pages. See [the skill overview](../SKILL.md) for the mental model; [client.md](client.md) for the front-end; [security-and-production.md](security-and-production.md) for cookies, cross-subdomain, and `trustedOrigins`.

## Contents

- [The one invariant](#the-one-invariant) · [Next.js App](#nextjs--app-router) · [Next.js Pages](#nextjs--pages-router) · [Express](#express) · [Raw Node http](#raw-node-http) · [SvelteKit](#sveltekit) · [Nuxt](#nuxt-nitro) · [SolidStart](#solidstart) · [Remix / RR7](#remix-v2--react-router-v7) · [Astro](#astro) · [TanStack Start](#tanstack-start) · [Hono](#hono) · [Fastify](#fastify) · [Elysia](#elysia)
- [Catch-all route cheat sheet](#catch-all-route-path-cheat-sheet) · [Route protection](#route-protection-optimistic-vs-authoritative) · [Import paths](#import-paths--symbols-load-bearing)

## The one invariant

Every framework reduces to handing a Web `Request` to `auth.handler(request: Request): Promise<Response>`. The helpers (`toNextJsHandler`, `toNodeHandler`, `svelteKitHandler`, `toSolidStartHandler`) exist only to (a) adapt Node `IncomingMessage`/`ServerResponse` ↔ Web `Request`/`Response`, and (b) flush `Set-Cookie` from server actions/RPC. The auth instance comes from `betterAuth({...})` (`"better-auth"`), exported from `lib/auth.ts` (or `auth.ts`). The catch-all is `/api/auth/*` by convention — change it via `basePath`, but then the client `baseURL` must match.

The cookie-helper plugins (`nextCookies`, `sveltekitCookies`, `tanstackStartCookies`) only matter when **server actions / server-side RPC set cookies** (e.g. server-side `auth.api.signInEmail`). Server actions can't return raw response headers, so these plugins re-emit `Set-Cookie` through the framework's native cookie API. Keep them **last in `plugins`** — anything registered after won't have its cookies flushed.

## Next.js — App Router

File: `app/api/auth/[...all]/route.ts`

```ts
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

Add `nextCookies()` **last** in `plugins` so server-action cookies persist (file `lib/auth.ts`):

```ts
import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";

export const auth = betterAuth({
  // ...config
  plugins: [nextCookies()], // MUST be the LAST plugin
});
```

**Read the session** (authoritative — server component / route handler / server action). Call this in the page/layout to protect it:

```ts
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const session = await auth.api.getSession({ headers: await headers() });
if (!session) redirect("/sign-in");   // session = { session, user }
```

For middleware-level protection, see [route protection](#route-protection-optimistic-vs-authoritative) — `getSessionCookie` is for redirects only.

## Next.js — Pages Router

File: `pages/api/auth/[...all].ts`

```ts
import { toNodeHandler } from "better-auth/node";
import { auth } from "@/lib/auth";

export const config = { api: { bodyParser: false } }; // REQUIRED: disable body parsing

export default toNodeHandler(auth.handler);
```

`toNodeHandler` accepts both `toNodeHandler(auth)` (Express) and `toNodeHandler(auth.handler)` (Pages). Read the session in `getServerSideProps` / API routes with `fromNodeHeaders` (see [Express](#express)).

## Express

File: `server.ts`

```ts
import express from "express";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";

const app = express();

app.all("/api/auth/*", toNodeHandler(auth));        // Express v4
// app.all("/api/auth/*splat", toNodeHandler(auth)); // Express v5

app.use(express.json()); // MUST come AFTER the Better Auth handler

app.listen(8000);
```

Two load-bearing gotchas:

- **`express.json()` ordering.** Never register `express.json()` (or any body parser) before the auth handler — the docs warn the client API "will get stuck on 'pending'". Mount it after, or scope it to non-auth routes. **Express v5 wildcard:** v4 uses `"/api/auth/*"`; v5 needs a named splat: `"/api/auth/*splat"`.

**Read the session** in any Node/Express route — adapt Node headers with `fromNodeHeaders`. Wrap this in middleware (401/redirect when null) to protect a route:

```ts
import { fromNodeHeaders } from "better-auth/node";

const session = await auth.api.getSession({ headers: fromNodeHeaders(req.headers) });
```

## Raw Node http

No dedicated docs page (`/docs/integrations/node` 404s), but `toNodeHandler` returns a `(req, res) => void` Node handler you can wire straight into `http.createServer`:

```ts
import { createServer } from "node:http";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";

const handler = toNodeHandler(auth);
createServer((req, res) => {
  if (req.url?.startsWith("/api/auth")) return handler(req, res);
  // ...your other routing
  res.statusCode = 404; res.end();
}).listen(3000);
```

`better-auth/node` exports `toNodeHandler` and `fromNodeHeaders` — read sessions exactly as in [Express](#express).

## SvelteKit

File: `src/hooks.server.ts`

```ts
import { auth } from "$lib/auth";
import { svelteKitHandler } from "better-auth/svelte-kit";
import { building } from "$app/environment";

export async function handle({ event, resolve }) {
  return svelteKitHandler({ event, resolve, auth, building });
}
```

`building` (from `"$app/environment"`) is required in the handler signature. Add the cookie plugin **last** (file `src/lib/auth.ts`):

```ts
import { betterAuth } from "better-auth";
import { sveltekitCookies } from "better-auth/svelte-kit";
import { getRequestEvent } from "$app/server";

export const auth = betterAuth({
  // ...config
  plugins: [sveltekitCookies(getRequestEvent)], // LAST plugin
});
```

Watch the casing — the handler is `svelteKitHandler` (capital K), the plugin is `sveltekitCookies` (lowercase k). `sveltekitCookies` needs SvelteKit ≥ 2.20.0. **Read the session** in a `load`/`+page.server.ts` via `auth.api.getSession({ headers: event.request.headers })`.

## Nuxt (Nitro)

File: `server/api/auth/[...all].ts`

```ts
import { auth } from "~~/lib/auth"; // or ~/utils/auth
export default defineEventHandler((event) => {
  return auth.handler(toWebRequest(event));
});
```

`defineEventHandler` and `toWebRequest` are Nitro auto-imports — no Better-Auth-specific symbol. There is no `toNuxtHandler`; call `auth.handler` directly. **Read the session** with `auth.api.getSession({ headers: event.headers })`.

## SolidStart

File: `src/routes/api/auth/[...all].ts` (the catch-all segment name is arbitrary)

```ts
import { auth } from "~/lib/auth";
import { toSolidStartHandler } from "better-auth/solid-start";

export const { GET, POST } = toSolidStartHandler(auth);
```

Read the session in a route/server function via `auth.api.getSession({ headers })` (see [route protection](#route-protection-optimistic-vs-authoritative)).

## Remix v2 / React Router v7

File: `app/routes/api.auth.$.ts` (Remix flat-route dot syntax, `$` splat)

```ts
import { auth } from "~/lib/auth.server";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "react-router";
// Remix v2 legacy: import type { ... } from "@remix-run/node";

export async function loader({ request }: LoaderFunctionArgs) {
  return auth.handler(request);
}
export async function action({ request }: ActionFunctionArgs) {
  return auth.handler(request);
}
```

No helper needed — call `auth.handler(request)` in `loader` (GET) and `action` (non-GET). The **only** difference between React Router v7 and Remix v2 is the type-import source: `"react-router"` vs `"@remix-run/node"`. Read sessions in any loader/action with `auth.api.getSession({ headers: request.headers })`.

## Astro

File: `src/pages/api/auth/[...all].ts`

```ts
import { auth } from "~/auth";
import type { APIRoute } from "astro";

export const ALL: APIRoute = async (ctx) => {
  return auth.handler(ctx.request);
};
```

Export a single `ALL` handler (type `APIRoute` from `"astro"`) and pass `ctx.request`. For rate limiting behind a proxy, set `ctx.request.headers.set("x-forwarded-for", ctx.clientAddress)` before calling. Astro must run in SSR / on-demand mode (`output: "server"` or hybrid) or the route never executes server-side — an Astro config prerequisite, not a Better Auth one.

## TanStack Start

File: `src/routes/api/auth/$.ts` (catch-all segment is `$`)

```ts
import { auth } from "@/lib/auth";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/auth/$")({
  server: {
    handlers: {
      GET:  async ({ request }: { request: Request }) => await auth.handler(request),
      POST: async ({ request }: { request: Request }) => await auth.handler(request),
    },
  },
});
```

Add the cookie plugin **last** (file `src/lib/auth.ts`):

```ts
import { betterAuth } from "better-auth";
import { tanstackStartCookies } from "better-auth/tanstack-start";        // React
// import { tanstackStartCookies } from "better-auth/tanstack-start/solid"; // Solid variant

export const auth = betterAuth({
  // ...config
  plugins: [tanstackStartCookies()], // LAST plugin
});
```

## Hono

```ts
import { Hono } from "hono";
import { cors } from "hono/cors";
import { serve } from "@hono/node-server";
import { auth } from "./auth";

const app = new Hono();

// CORS must be registered BEFORE the auth route
app.use("/api/auth/*", cors({
  origin: "http://localhost:3001",
  allowHeaders: ["Content-Type", "Authorization"],
  allowMethods: ["POST", "GET", "OPTIONS"],
  exposeHeaders: ["Content-Length"],
  maxAge: 600,
  credentials: true,
}));

app.on(["POST", "GET"], "/api/auth/*", (c) => auth.handler(c.req.raw));

serve(app);
```

Pass the raw Web Request `c.req.raw`. **CORS middleware must come before the auth route** — Hono applies middleware in registration order, so a later `cors()` never decorates the auth responses. To put the session on context, add `app.use("*", async (c, next) => { c.set("session", await auth.api.getSession({ headers: c.req.raw.headers })); await next(); })`.

## Fastify

No Fastify-specific helper — manually build a Web `Request`, call `auth.handler`, then copy status/headers/body back onto `reply`:

```ts
import Fastify from "fastify";
import { fromNodeHeaders } from "better-auth/node";
import { auth } from "./auth";

const fastify = Fastify({ logger: true });

fastify.route({
  method: ["GET", "POST"],
  url: "/api/auth/*",
  async handler(request, reply) {
    const url = new URL(request.url, `http://${request.headers.host}`);
    const headers = fromNodeHeaders(request.headers);
    const req = new Request(url.toString(), {
      method: request.method,
      headers,
      ...(request.body ? { body: JSON.stringify(request.body) } : {}),
    });
    const response = await auth.handler(req);
    reply.status(response.status);
    response.headers.forEach((value, key) => reply.header(key, value));
    reply.send(response.body ? await response.text() : null);
  },
});

fastify.listen({ port: 4000 });
```

If Fastify's content-type parser already consumed the body, the `JSON.stringify(request.body)` re-stringify must match what the client sent — verify against your parser config.

## Elysia

```ts
import { Elysia } from "elysia";
import { cors } from "@elysiajs/cors";       // optional
import { auth } from "./auth";

const app = new Elysia()
  .use(cors({ origin: "http://localhost:3001", credentials: true })) // optional
  .mount(auth.handler)   // mounts the Web-standard handler
  .listen(3000);
```

`.mount(auth.handler)` plugs the Web handler straight in (Bun runtime).

## Catch-all route path cheat sheet

A non-catch-all route silently 404s sub-paths like `/api/auth/sign-in/email` — use the right wildcard:

| Framework | File path | Method export |
|---|---|---|
| Next.js App | `app/api/auth/[...all]/route.ts` | `export const { GET, POST } = toNextJsHandler(auth)` |
| Next.js Pages | `pages/api/auth/[...all].ts` | `export default toNodeHandler(auth.handler)` + `config.api.bodyParser=false` |
| SvelteKit | `src/hooks.server.ts` | `handle` → `svelteKitHandler(...)` |
| Nuxt | `server/api/auth/[...all].ts` | `export default defineEventHandler(...)` |
| SolidStart | `src/routes/api/auth/[...all].ts` | `export const { GET, POST } = toSolidStartHandler(auth)` |
| Remix / RR7 | `app/routes/api.auth.$.ts` | `loader` + `action` |
| Astro | `src/pages/api/auth/[...all].ts` | `export const ALL: APIRoute` |
| TanStack Start | `src/routes/api/auth/$.ts` | `createFileRoute("/api/auth/$")` server handlers |
| Express v4/v5 | `server.ts` | `app.all("/api/auth/*" \| "/api/auth/*splat", toNodeHandler(auth))` |
| Hono | `index.ts` | `app.on(["POST","GET"], "/api/auth/*", c => auth.handler(c.req.raw))` |
| Fastify | `index.ts` | `fastify.route({ method:["GET","POST"], url:"/api/auth/*" })` manual adapt |
| Elysia | `index.ts` | `new Elysia().mount(auth.handler)` |
| raw Node http | — | `const h = toNodeHandler(auth); createServer((req,res)=>h(req,res))` |

## Route protection: optimistic vs authoritative

Two strategies, both documented, for different jobs.

**1. Optimistic cookie check** — fast, **no DB validation**, redirect-only UX. Use in middleware to bounce logged-out users before render. It only checks a cookie *exists* — never trust it for real authz.

```ts
import { getSessionCookie } from "better-auth/cookies";
import { NextResponse, type NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const sessionCookie = getSessionCookie(request);
  if (!sessionCookie) return NextResponse.redirect(new URL("/sign-in", request.url));
  return NextResponse.next();
}
```

`getSessionCookie(request, opts?)` and `getCookieCache(request)` both come from `better-auth/cookies`. `getSessionCookie` does NOT read your `auth.ts` config — if you customized the cookie name/prefix (`advanced.cookiePrefix`/`advanced.cookies`, see [security-and-production.md](security-and-production.md)), pass `{ cookieName, cookiePrefix }` as the 2nd arg or it returns null on a logged-in user. `getCookieCache(request)` returns the cached session **object** from the signed `session_data` cookie (requires `session.cookieCache.enabled`).

**2. Authoritative validation** — the real check; requires the Node.js runtime. Do this per page / route / loader:

```ts
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const session = await auth.api.getSession({ headers: await headers() });
if (!session) redirect("/sign-in");   // guard with session?.user
```

Other frameworks pass raw headers: Nuxt `event.headers`; Hono/Express/loaders `request.headers`.

**The rule:** `getSessionCookie`/`getCookieCache` in middleware only, for optimistic redirects; authoritative `auth.api.getSession` per page/route/loader. To run the authoritative check **inside** Next.js middleware you need `export const config = { runtime: "nodejs", matcher: [...] }` (Next 15.2.0+) — on the Edge runtime only the optimistic check is available.

## Import paths & symbols (load-bearing)

Copy verbatim — casing and subpaths are easy to get subtly wrong. Universal: `betterAuth` from `"better-auth"`; `auth.handler(request)` (Web handler); `auth.api.getSession({ headers })` (server session read).

- Next.js: `import { toNextJsHandler, nextCookies } from "better-auth/next-js"`
- Node / Express / Fastify / Pages / raw-http: `import { toNodeHandler, fromNodeHeaders } from "better-auth/node"`
- SvelteKit: `import { svelteKitHandler, sveltekitCookies } from "better-auth/svelte-kit"` (note `svelteKitHandler` vs `sveltekitCookies`)
- SolidStart: `import { toSolidStartHandler } from "better-auth/solid-start"`
- TanStack Start: `import { tanstackStartCookies } from "better-auth/tanstack-start"` (or `.../tanstack-start/solid`)
- Cookies: `import { getSessionCookie, getCookieCache } from "better-auth/cookies"`
- Nuxt / Astro / Hono / Elysia / Remix / React Router: **no** dedicated import — call `auth.handler(...)` directly.

> Version note: the Express v5 `*splat` wildcard, the TanStack Start `server.handlers` shape, and `sveltekitCookies` + `getRequestEvent` (SvelteKit ≥ 2.20.0) are recent additions (~v1.6) — confirm against the installed `better-auth` version. After wiring, generate the schema with `npx @better-auth/cli@latest generate` (short alias `npx auth@latest generate`), then `migrate` per [database-adapters.md](database-adapters.md).

Sources: https://better-auth.com/docs
