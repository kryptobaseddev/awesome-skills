# Sessions, security & production

Everything that hardens a Better Auth instance for real traffic: session lifetime, cookies, the cross-subdomain trap, trusted origins, rate limiting, Redis secondary storage, lifecycle hooks, password hashing, route protection, and a ship checklist. See [the skill overview](../SKILL.md) for the mental model; all config below lives inside `betterAuth({ ... })` from `import { betterAuth } from "better-auth";` ([core-server-config.md](core-server-config.md)).

## Contents

- [Session config](#session-config)
- [Cookie config & default names](#cookie-config--default-names)
- [Cross-subdomain cookies (the #1 prod break)](#cross-subdomain-cookies-the-1-prod-break)
- [trustedOrigins](#trustedorigins)
- [Rate limiting](#rate-limiting)
- [Secondary storage (Redis)](#secondary-storage-redis)
- [Database hooks](#database-hooks)
- [Request hooks (createAuthMiddleware)](#request-hooks-createauthmiddleware)
- [Password hashing](#password-hashing)
- [Route protection: optimistic vs authoritative](#route-protection-optimistic-vs-authoritative)
- [Production checklist](#production-checklist)

## Session config

Sessions use a **sliding window**: a session expires `expiresIn` seconds after creation, but each time it is used past `updateAge`, its expiry is bumped to `now + expiresIn`. Set `updateAge: 0` to refresh on every request (most writes; least likely to log an active user out).

```ts
export const auth = betterAuth({
  session: {
    modelName: "sessions",            // table override (default "session")
    fields: { userId: "user_id" },    // column name mapping
    expiresIn: 60 * 60 * 24 * 7,      // seconds — default 7 days (604800)
    updateAge: 60 * 60 * 24,          // seconds — default 1 day (86400); 0 => refresh every use
    disableSessionRefresh: false,     // true => never bump expiry, ignoring updateAge
    additionalFields: {               // extra session columns (re-run generate after adding)
      customField: { type: "string" },
    },
    storeSessionInDatabase: false,    // keep DB session rows even when secondaryStorage is set
    preserveSessionInDatabase: false, // keep the DB row after delete from secondary storage
    cookieCache: {
      enabled: false,                 // cache the session in a signed cookie -> skip DB on read
      maxAge: 5 * 60,                 // seconds the cached cookie is trusted (300 = 5 min)
    },
  },
});
```

`cookieCache` is the cheapest scale win: it stores the session object in a short-lived cookie signed with your `secret`, so `getSession`/`useSession` skip the DB until `maxAge` elapses. Trade-off: a revoked session stays "valid" in the cache until it expires, so keep `maxAge` short (minutes). There is **no built-in expired-session cleanup job** — prune the `session` table yourself (cron) or lean on `secondaryStorage` TTLs.

## Cookie config & default names

Default cookie attributes are `{ httpOnly: true, secure: <prod || useSecureCookies>, sameSite: "lax", path: "/" }`. Cookies are named `${prefix}.${cookieName}` with prefix `better-auth`, and gain a `__Secure-` prefix when secure. The default cookies are:

| Cookie | Purpose |
|---|---|
| `session_token` | the session identifier |
| `session_data` | the cookie cache payload (only when `session.cookieCache.enabled`) |
| `dont_remember` | tracks "remember me" opt-out |

```ts
export const auth = betterAuth({
  advanced: {
    cookiePrefix: "myapp",          // default "better-auth" -> "myapp.session_token"
    useSecureCookies: true,         // default: secure only in prod; true forces Secure everywhere
    disableCSRFCheck: false,        // default false — leave on
    disableOriginCheck: false,      // default false — related origin-validation toggle; leave on
    defaultCookieAttributes: {      // merged into EVERY cookie
      httpOnly: true,
      secure: true,
      sameSite: "lax",              // "lax" | "strict" | "none"
    },
    cookies: {                      // per-cookie name + attribute overrides
      session_token: {
        name: "custom_session_token",
        attributes: { httpOnly: true, secure: true },
      },
    },
    ipAddress: {
      ipAddressHeaders: ["cf-connecting-ip", "x-forwarded-for"], // order = priority
      disableIpTracking: false,
      ipv6Subnet: 64,               // rate-limit IPv6 by /64
    },
  },
});
```

Behind a proxy/CDN, set `ipAddress.ipAddressHeaders` to your edge's real-client header (e.g. `cf-connecting-ip`) — otherwise every request looks like it came from the proxy IP and per-IP rate limits collapse onto one bucket.

Note: in v1.x the OAuth **state** cookie config moved off `advanced` to `account.storeStateStrategy` / `account.skipStateCookieCheck` — don't look for it here (see [social-oauth.md](social-oauth.md)).

## Cross-subdomain cookies (the #1 prod break)

When the frontend and the auth server sit on different subdomains (`app.example.com` ↔ `api.example.com`), the browser drops the `Set-Cookie` by default — "works on localhost, logs out in prod" is almost always this. Fix it by scoping the cookie to the parent domain and relaxing `sameSite`:

```ts
export const auth = betterAuth({
  baseURL: "https://api.example.com",   // REQUIRED — throws if crossSubDomainCookies on without it
  advanced: {
    crossSubDomainCookies: {
      enabled: true,
      domain: "example.com",            // leading-dot parent; auto-derived from baseURL host if omitted
      additionalCookies: ["custom_cookie"],
    },
    defaultCookieAttributes: {
      sameSite: "none",                 // cross-site requests need "none"...
      secure: true,                     // ...which browsers ONLY honor with Secure (=> HTTPS)
      partitioned: true,                // CHIPS — required by Chrome's third-party-cookie phase-out
    },
  },
});
```

Why each line matters: `sameSite: "none"` is the only value the browser sends on cross-site requests, but it is silently rejected without `secure: true` (so this needs HTTPS on both ends). `partitioned: true` (CHIPS) keys the cookie to the top-level site so it survives Chrome's third-party-cookie deprecation. Enabling `crossSubDomainCookies` without a `baseURL` (and no explicit `domain`) throws `BetterAuthError: baseURL is required when crossSubdomainCookies are enabled`.

## trustedOrigins

`trustedOrigins` gates CSRF/Origin checks and OAuth redirect validation. Any client on a **different origin** than the server must be listed, or its requests fail CSRF. Static array or async function:

```ts
trustedOrigins: ["http://localhost:3000", "https://example.com"]   // static

trustedOrigins: async (request) => {                               // dynamic (e.g. tenant domains)
  if (!request) return ["https://my-frontend.com"];
  return ["https://dynamic-origin.com"];
}
```

## Rate limiting

Enabled in **production by default, disabled in dev**. Limits are per-IP per-path; a 429 returns an `X-Retry-After` header. Server-side `auth.api.*` calls **bypass** rate limiting entirely — limits only apply to requests coming through the HTTP handler, so trusted backend code is never throttled.

```ts
rateLimit: {
  enabled: true,
  window: 60,                     // seconds (default 60)
  max: 100,                       // requests per window (default 100/60s)
  storage: "memory",              // "memory" | "database" | "secondary-storage"
  modelName: "rateLimit",         // table name when storage:"database" (re-run generate)
  customRules: {
    "/sign-in/email": { window: 10, max: 3 },                    // tighten sensitive paths
    "/two-factor/*": async (request) => ({ window: 10, max: 3 }), // wildcard + fn form
    "/get-session": false,                                        // disable for a hot path
  },
}
```

`storage: "memory"` (the default) does not survive restarts and is **not shared across instances** — for any multi-process/serverless deploy use `"database"` or `"secondary-storage"` (the latter requires `secondaryStorage` configured, below) so all nodes share the counter.

## Secondary storage (Redis)

A `SecondaryStorage` backend holds short-lived auth data — sessions, verification records, and rate-limit counters — off your primary DB. When set, sessions go to secondary storage **unless** `session.storeSessionInDatabase: true`. The interface is three methods:

```ts
interface SecondaryStorage {
  get: (key: string) => Promise<unknown>;            // ioredis returns string | null; BA JSON-parses
  set: (key: string, value: string, ttl?: number) => Promise<void>;  // ttl in seconds
  delete: (key: string) => Promise<void>;
}
```

Hand-rolled `ioredis` implementation (always correct, no extra dependency):

```ts
import { betterAuth } from "better-auth";
import { Redis } from "ioredis";

const redis = new Redis();
export const auth = betterAuth({
  secondaryStorage: {
    get: async (key) => await redis.get(key),
    set: async (key, value, ttl) => {
      if (ttl) await redis.set(key, value, "EX", ttl);
      else await redis.set(key, value);
    },
    delete: async (key) => { await redis.del(key); },
  },
});
```

There is an official helper — `import { redisStorage } from "@better-auth/redis-storage"; secondaryStorage: redisStorage({ client: redis, keyPrefix: "better-auth:" })` — but confirm the package is installed for your version before relying on it; the manual object above is the guaranteed-correct path. Pairing `secondaryStorage` (Redis) with `session.cookieCache` is the canonical "cut session DB reads at scale" combo.

## Database hooks

`databaseHooks` fire `before`/`after` create and update on `user`, `session`, `account`, and `verification`. A `before` hook that returns `{ data }` **replaces** the payload; returning `false` **aborts** the operation. The second argument is the auth context.

```ts
databaseHooks: {
  user: {
    create: {
      before: async (user, ctx) => ({ data: { ...user, customField: "value" } }),
      after:  async (user, ctx) => { /* side effects: welcome email, analytics */ },
    },
    update: {
      before: async (userData, ctx) => ({ data: { ...userData, updatedAt: new Date() } }),
      after:  async (user, ctx) => {},
    },
  },
  session: { create: { before, after }, update: { before, after } },
  account: { create: { before, after }, update: { before, after } },
  verification: { create: { before, after }, update: { before, after } },
}
```

Common use: encrypt OAuth `accessToken`/`refreshToken` at rest inside `account.create.before` before they hit the DB.

## Request hooks (createAuthMiddleware)

For request-lifecycle middleware (logging, custom validation, gating a path), use `createAuthMiddleware` from the exact path `better-auth/api`:

```ts
import { betterAuth } from "better-auth";
import { createAuthMiddleware } from "better-auth/api";   // exact import path

export const auth = betterAuth({
  hooks: {
    before: createAuthMiddleware(async (ctx) => {
      if (ctx.path !== "/sign-up/email") return;          // match a specific route
      // ctx.path, ctx.request, ctx.headers, ctx.body are available here
    }),
    after: createAuthMiddleware(async (ctx) => {
      console.log("Response:", ctx.context.returned);
    }),
  },
});
```

Inside the middleware, `ctx.context.authCookies.sessionToken.name` is the resolved session-cookie name and `ctx.context.password.hash(pw)` / `.verify(...)` expose the internal hasher. Don't confuse these `hooks` (HTTP lifecycle) with `databaseHooks` (DB lifecycle) above.

## Password hashing

The default is **scrypt**, built in — no configuration needed and safe to leave alone. Override only to match an existing hash format or a stricter policy, via `emailAndPassword.password`:

```ts
emailAndPassword: {
  enabled: true,
  password: {
    hash: async (password) => { /* return string */ },
    verify: async ({ hash, password }) => { /* return boolean */ },
  },
}
```

## Route protection: optimistic vs authoritative

Two strategies, and the distinction is the most common authz bug. **Never trust the optimistic check for real authorization** — it only proves a cookie exists, not that the session is valid or unrevoked.

| | Optimistic (cookie only) | Authoritative (server validation) |
|---|---|---|
| Call | `getSessionCookie` / `getCookieCache` from `better-auth/cookies` | `auth.api.getSession({ headers })` |
| Hits DB | no | yes (unless served from cookie cache) |
| Runtime | edge-safe | Node.js |
| Use for | middleware redirects, fast UX gating | every page/route/loader that returns protected data |

**Optimistic** — fast redirect in middleware, no DB:

```ts
import { getSessionCookie } from "better-auth/cookies";

export function middleware(request: NextRequest) {
  const sessionCookie = getSessionCookie(request);
  if (!sessionCookie) return NextResponse.redirect(new URL("/sign-in", request.url));
  return NextResponse.next();
}
// or read the cached object: const session = await getCookieCache(request);
```

`getSessionCookie(request, opts?)` does **not** read your `auth.ts` config — if you customized `advanced.cookiePrefix` or the cookie `name`, pass them in the second arg `{ cookieName?, cookiePrefix? }` or it returns `null` for a logged-in user. `getCookieCache(request)` returns the decoded session object and requires `session.cookieCache.enabled`.

**Authoritative** — the real check, per page/route:

```ts
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const session = await auth.api.getSession({ headers: await headers() });
if (!session) redirect("/sign-in");   // session = { session: {...}, user: {...} }
```

Running the authoritative check inside Next.js middleware requires the Node runtime (`export const config = { runtime: "nodejs", matcher: [...] }`, Next 15.2.0+); on the Edge runtime use the cookie-only optimistic check and re-validate in the route. Per-framework header plumbing (Nuxt `event.headers`, Hono `request.headers`, etc.) and route-protection recipes live in [frameworks.md](frameworks.md) — don't re-derive them here.

## Production checklist

| Item | Why / how |
|---|---|
| `BETTER_AUTH_SECRET` set | Signs/encrypts/hashes everything. Dev uses a placeholder; **boot throws in prod if unset**. Generate `openssl rand -base64 32` or `npx @better-auth/cli@latest secret`. |
| `baseURL` / `BETTER_AUTH_URL` set | Cookies, OAuth redirects, and origin checks need it. Static `"https://example.com"` or dynamic `{ allowedHosts: ["myapp.com","*.vercel.app"], protocol: "https", fallback: "https://myapp.com" }`. `basePath` defaults to `/api/auth`. |
| HTTPS in prod | Cookies are `secure` automatically in prod; force everywhere with `advanced.useSecureCookies: true`. Required for `sameSite: "none"`. |
| `trustedOrigins` lists every client origin | CSRF + OAuth-redirect safety for any cross-origin client. |
| Cross-subdomain wired | If frontend ≠ server subdomain: `crossSubDomainCookies` + `sameSite:"none"` + `secure:true` + `partitioned:true`. |
| DB indexed | Index `session.userId`, `session.token`, `user.email`, `account.userId`; use connection pooling. See [database-adapters.md](database-adapters.md). |
| Rate-limit storage shared | Move off `"memory"` to `"database"` or `"secondary-storage"` for multi-instance/serverless. |
| Redis + cookie cache | `secondaryStorage` (Redis) + `session.cookieCache` cut session DB reads at scale. |
| Real client IP | Behind a proxy/CDN set `advanced.ipAddress.ipAddressHeaders` (e.g. `cf-connecting-ip`). |
| Serverless deferral | Use `advanced.backgroundTasks.handler` (e.g. `waitUntil`) to defer non-critical work. |
| Schema current | Re-run `npx @better-auth/cli@latest generate` then migrate after any plugin/field add (short alias `npx auth@latest`). |
| Bundle size | `better-auth/minimal` with a custom adapter trims the build. |

Sources: https://better-auth.com/docs
