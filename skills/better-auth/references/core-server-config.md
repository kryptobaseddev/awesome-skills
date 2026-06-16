# Core server config — the `betterAuth()` instance

The single source of truth for a Better Auth app: install, the full `betterAuth()` config object, the server-side `auth.api.*` surface, the CLI, required env, and type inference. Read [the skill overview](../SKILL.md) for the 4-part mental model first.

## Contents

- [Install](#install)
- [Required env](#required-env)
- [The server instance](#the-server-instance)
- [Full config object (top-level keys)](#full-config-object-top-level-keys)
- [Important sub-objects](#important-sub-objects)
- [Server-side: `auth.api.*`](#server-side-authapi)
- [The CLI (`@better-auth/cli`)](#the-cli-better-authcli)
- [Type inference (`auth.$Infer`)](#type-inference-authinfer)

## Install

One package ships the server, client, and adapters via subpaths:

```bash
npm install better-auth        # or: pnpm add / yarn add / bun add better-auth
```

The CLI is a separate package, `@better-auth/cli`, but you almost always run it with `npx` rather than installing it (see [the CLI](#the-cli-better-authcli)).

## Required env

```env
BETTER_AUTH_SECRET=<32+ char random>     # signs/encrypts/hashes sessions & tokens
BETTER_AUTH_URL=http://localhost:3000    # the app's base URL (prod: https://yourapp.com)
```

```bash
openssl rand -base64 32                   # generate a secret
npx @better-auth/cli@latest secret        # ...or via the CLI
```

Why these matter: `secret` is read from `BETTER_AUTH_SECRET` (or `AUTH_SECRET`) when you don't pass `secret` in config — boot **throws in production** if it's missing, because every cookie/token signature depends on it. `baseURL` is read from `BETTER_AUTH_URL` (or `AUTH_URL` / framework vars) when `baseURL` is omitted; get it wrong and cookies, OAuth redirects, and trusted-origin checks break in prod (the classic "works locally, 500s in prod").

## The server instance

The CLI auto-discovers `auth.ts` at the project root or under `lib/`, `utils/`, `server/` (optionally nested in `src/` or `app/`). Keep it one file — it is the source of truth.

```ts
// lib/auth.ts
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  database: /* adapter, or a raw pg.Pool / better-sqlite3 Database */,
  emailAndPassword: { enabled: true },
});
```

`database` accepts a built-in driver directly (no adapter needed) or an ORM adapter from a subpath. Full detail lives in [database-adapters.md](database-adapters.md); the short version:

```ts
import Database from "better-sqlite3";
betterAuth({ database: new Database("./sqlite.db") });          // built-in (Kysely)

import { Pool } from "pg";
betterAuth({ database: new Pool({ connectionString: process.env.DATABASE_URL }) });

import { drizzleAdapter } from "better-auth/adapters/drizzle";  // { provider: "pg"|"mysql"|"sqlite", schema }
import { prismaAdapter } from "better-auth/adapters/prisma";    // { provider: "postgresql"|"mysql"|"sqlite" }
// also: better-auth/adapters/mongodb → mongodbAdapter
```

Mounting the handler is per-framework (`toNextJsHandler`, `toNodeHandler`, `auth.handler`, …) — see [frameworks.md](frameworks.md).

## Full config object (top-level keys)

Every top-level key, one line each. Deep detail is deferred where noted.

| key | type | purpose |
|---|---|---|
| `appName` | string | App name. Default `"Better Auth"` |
| `baseURL` | string \| object | Root URL the server runs at (object form = dynamic multi-domain) |
| `basePath` | string | Mount path for auth routes. Default `/api/auth` |
| `secret` | string | Encryption / signing / hashing secret |
| `secrets` | array | Versioned secrets for non-destructive rotation → [security-and-production.md](security-and-production.md) |
| `database` | object \| Pool \| Database \| adapter | DB dialect or adapter → [database-adapters.md](database-adapters.md) |
| `secondaryStorage` | object | Alt store for sessions/verification/ratelimit (e.g. Redis) → [security-and-production.md](security-and-production.md) |
| `emailAndPassword` | object | Email/password auth ([below](#emailandpassword)) |
| `emailVerification` | object | Verification email handlers ([below](#emailverification)) |
| `socialProviders` | object | OAuth provider credentials → [social-oauth.md](social-oauth.md) |
| `plugins` | array | Better Auth plugins → [plugins.md](plugins.md) |
| `user` | object | User model customization ([below](#user)) |
| `session` | object | Session lifecycle ([below](#session)) |
| `account` | object | OAuth account linking + token storage ([below](#account)) |
| `verification` | object | Verification record storage / identifier handling |
| `trustedOrigins` | string[] \| function | Extra trusted origins; wildcard patterns + `fn(request)` → [security-and-production.md](security-and-production.md) |
| `rateLimit` | object | Rate limiting ([below](#ratelimit)) → [security-and-production.md](security-and-production.md) |
| `onAPIError` | object | API error handling ([below](#onapierror)) |
| `hooks` | object | `{ before, after }` request-level middleware ([below](#hooks-request-level)) |
| `databaseHooks` | object | before/after CRUD hooks for user/session/account/verification ([below](#databasehooks)) |
| `advanced` | object | cookies, ID gen, IP tracking, CSRF ([below](#advanced)) → [security-and-production.md](security-and-production.md) |
| `logger` | object | `level` / custom handler / `disableColors` |
| `telemetry` | object | `{ enabled, debug? }` — opt-in anonymous telemetry (off by default) |

## Important sub-objects

### `emailAndPassword`

| field | default | notes |
|---|---|---|
| `enabled` | `false` | turn email/password on |
| `disableSignUp` | `false` | block self-serve sign-up |
| `requireEmailVerification` | `false` | block sign-in until verified |
| `minPasswordLength` / `maxPasswordLength` | `8` / `128` | length bounds |
| `autoSignIn` | `true` | sign the user in right after sign-up |
| `sendResetPassword` | — | async `({ user, url, token }, request) => …` — you send the email |
| `resetPasswordTokenExpiresIn` | `3600` | seconds |
| `onPasswordReset` | — | async `({ user }, request)` hook after a reset |
| `revokeSessionsOnPasswordReset` | `false` | kill other sessions on reset |
| `password.hash` / `password.verify` | — | custom hashing functions |

`sendResetPassword` is **required** to use `requestPasswordReset` — Better Auth generates the token and URL, but never sends mail itself.

### `emailVerification`

`sendVerificationEmail` (async `({ user, url, token }, request)`) · `sendOnSignUp` (bool) · `sendOnSignIn` (bool) · `autoSignInAfterVerification` (bool) · `expiresIn` (seconds, default `3600`). Same rule: you own the actual send.

### `session`

`expiresIn` (default `604800` = 7d) · `updateAge` (default `86400` = 1d; how often a live session is refreshed) · `disableSessionRefresh` (bool) · `additionalFields` (object) · `storeSessionInDatabase` (bool) · `preserveSessionInDatabase` (bool) · `cookieCache: { enabled, maxAge }`. `cookieCache` trades a signed-cookie session snapshot for fewer DB reads — tuning and the cross-subdomain story live in [security-and-production.md](security-and-production.md).

### `account`

`encryptOAuthTokens` (bool) · `updateAccountOnSignIn` (bool) · `storeStateStrategy` (`"cookie"` | `"database"`) · `storeAccountCookie` (bool) · `accountLinking: { enabled, trustedProviders, allowDifferentEmails }`. Note OAuth state config moved here from `advanced` (now `account.storeStateStrategy` / `account.skipStateCookieCheck`). Linking semantics → [social-oauth.md](social-oauth.md).

### `user`

`modelName` (str) · `fields` (DB column remap) · `additionalFields` (object) · `changeEmail: { enabled, sendChangeEmailConfirmation, updateEmailWithoutVerification }` · `deleteUser: { enabled, sendDeleteAccountVerification, beforeDelete, afterDelete }`.

`user.additionalFields` adds typed columns and threads them through `$Infer` end to end:

```ts
user: {
  additionalFields: {
    role: { type: "string", input: false, required: false, defaultValue: "user" },
  },
}
```

Field options: `type` (`"string"|"number"|"boolean"|"date"` or array-of) · `required` · `input` (set `false` so a client can't supply it at sign-up — essential for fields like `role`) · `defaultValue` · `references` · `unique` · `fieldName`. Adding fields changes the schema — re-run `generate` (see [the CLI](#the-cli-better-authcli)).

### `rateLimit`

`enabled` (default on in prod) · `window` (default `60`s) · `max` (default `100`) · `customRules` (`{ "/path": { window, max } }`) · `storage` (`"memory"|"database"|"secondary-storage"`) · `modelName`. Production tuning + Redis-backed storage → [security-and-production.md](security-and-production.md).

### `advanced`

cookies, ID generation, IP/CSRF — summarized here, deep cookie/CSRF detail in [security-and-production.md](security-and-production.md):

`ipAddress: { ipAddressHeaders, disableIpTracking }` · `useSecureCookies` · `disableCSRFCheck` · `disableOriginCheck` · `crossSubDomainCookies: { enabled, additionalCookies, domain }` · `cookies: { session_token: { name, attributes } }` · `defaultCookieAttributes` · `cookiePrefix` · `database: { generateId, defaultFindManyLimit, experimentalJoins }` · `backgroundTasks: { handler }` · `skipTrailingSlashes`. `database.generateId` accepts a fn, `false`, `"serial"`, or `"uuid"` to control primary-key shape ([database-adapters.md](database-adapters.md)).

### `onAPIError`

`throw` (bool — surface errors as thrown exceptions instead of HTTP responses) · `onError` (`(error, ctx) => …`) · `errorURL` (redirect page for thrown errors).

### `hooks` (request-level)

Request middleware, **not** DB hooks. Wrap with `createAuthMiddleware` from `better-auth/api`:

```ts
import { createAuthMiddleware } from "better-auth/api";

hooks: {
  before: createAuthMiddleware(async (ctx) => { /* ctx.path, ctx.body, ctx.headers */ }),
  after:  createAuthMiddleware(async (ctx) => { /* ctx.context.returned */ }),
}
```

### `databaseHooks`

before/after CRUD interception per model:

```ts
databaseHooks: {
  user:         { create: { before, after }, update: { before, after } },
  session:      { create: { before, after }, update: { before, after } },
  account:      { create: { before, after }, update: { before, after } },
  verification: { create: { before, after }, update: { before, after } },
}
// a `before` hook returns { data: {...} } to mutate the record, or false to abort
```

## Server-side: `auth.api.*`

Call auth logic directly on the server (server actions, loaders, route handlers, RSC). Every method takes `{ body?, headers?, query?, asResponse?, returnHeaders? }`.

**`headers` is required for any session-aware call** — without it the session is always `null`, because Better Auth reads the session cookie out of those headers. In Node frameworks convert with `fromNodeHeaders(req.headers)` from `better-auth/node`.

```ts
import { headers } from "next/headers";

const session = await auth.api.getSession({ headers: await headers() });
// session => { user, session } | null

await auth.api.signInEmail({ body: { email, password }, headers: await headers() });
await auth.api.signUpEmail({ body: { name, email, password } });
await auth.api.signOut({ headers: await headers() });
await auth.api.verifyEmail({ query: { token } });
await auth.api.requestPasswordReset({ body: { email, redirectTo } }); // renamed from forgetPassword/forgotPassword (v1.4)
await auth.api.resetPassword({ body: { newPassword, token } });
await auth.api.changePassword({ body: { newPassword, currentPassword }, headers: await headers() });
await auth.api.updateUser({ body: { name }, headers: await headers() });
await auth.api.listSessions({ headers: await headers() });
await auth.api.revokeSession({ body: { token }, headers: await headers() });
```

Response shaping — by default these return parsed data; to forward auth cookies set by the call:

- `asResponse: true` → returns the raw `Response` (cookies/headers already attached — return it as-is).
- `returnHeaders: true` → returns `{ headers, response }` so you can copy `Set-Cookie` onto your own reply.

(In Next.js server actions, the `nextCookies()` plugin handles cookie forwarding for you — see [frameworks.md](frameworks.md).)

Error handling — server calls throw `APIError` from `better-auth/api`:

```ts
import { APIError } from "better-auth/api";

try {
  await auth.api.signInEmail({ body, headers });
} catch (e) {
  if (e instanceof APIError) {
    e.message; e.status; e.body;   // structured error detail
  }
}
// also exported from better-auth/api: isAPIError(), createAuthMiddleware
```

## The CLI (`@better-auth/cli`)

Run it against your discovered `auth.ts`. The canonical form is `npx @better-auth/cli@latest <cmd>`; v1.5+ also ships the shorter `npx auth@latest <cmd>` bin alias (both resolve to the same tool — prefer the explicit form for version-compat).

```bash
npx @better-auth/cli@latest generate    # write the DB schema for your ORM, or a Kysely SQL migration file
npx @better-auth/cli@latest migrate     # apply schema DIRECTLY to the DB — built-in Kysely adapter ONLY
npx @better-auth/cli@latest init        # scaffold Better Auth into a project
npx @better-auth/cli@latest secret      # print a fresh secret
npx @better-auth/cli@latest info        # diagnostic environment info
npx @better-auth/cli@latest upgrade     # (v1.5+) upgrade Better Auth to latest
```

Other package managers: `pnpm dlx`, `yarn dlx`, `bun x` (e.g. `pnpm dlx @better-auth/cli@latest generate`).

**`generate` ≠ `migrate`** — the most common CLI mistake. `migrate` only works for the built-in Kysely adapter (raw `pg`/`mysql`/`sqlite`). With **Drizzle or Prisma**, run `generate` to emit the schema, then run that ORM's own migrate (`drizzle-kit migrate`, `prisma migrate`). Rule of thumb: **Kysely/built-in → `migrate`; Drizzle/Prisma → `generate` then the ORM's tool.** Re-run `generate` whenever you add a schema plugin or a `user.additionalFields` column, or you'll hit "column/table does not exist" at runtime. Full schema flow → [database-adapters.md](database-adapters.md).

Key flags:

- `generate`: `-c, --cwd <dir>` · `--config <path>` · `--output <file>` · `-y, --yes`
- `migrate`: `-c, --cwd <dir>` · `--config <path>` · `-y, --yes`
- `info`: `--config <path>` · `--json`
- `init`: `--name` · `--framework` · `--plugins` · `--database` · `--package-manager`

`--config` defaults to auto-discovery (first `auth.ts` in `./`, `./lib`, `./utils`, or their `src/` variants). Pass it explicitly when your instance lives elsewhere or the CLI can't find it.

## Type inference (`auth.$Infer`)

Derive types straight from the instance — they automatically reflect `user.additionalFields` and `session.additionalFields`, so custom columns are typed end to end:

```ts
type Session = typeof auth.$Infer.Session;   // { user: User, session: Session }
type User    = typeof auth.$Infer.User;      // includes your additionalFields
```

The client mirrors this with `typeof authClient.$Infer.Session` (see [client.md](client.md)).

---

Sources: https://better-auth.com/docs (installation, concepts/cli, concepts/api, reference/options, concepts/typescript).
