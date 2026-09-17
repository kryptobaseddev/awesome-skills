# `neon.ts` — Config as Code

`neon config` / `neon deploy` / `neon dev` / `neon checkout` all operate on a `neon.ts` file, so knowing
the CLI commands without knowing this file's shape gets you nowhere. This page covers the format; the
commands are in [platform-surfaces.md](platform-surfaces.md#config-as-code-neonts).

`neon.ts` is a TypeScript file you commit. It declares **which Neon services exist on the project** and
**how each branch is tuned**. The two halves are independent — use either alone.

It is declarative: it describes policy but does not apply it. `neon deploy` (alias for `neon config apply`)
provisions or updates the declared services, applies branch tuning, and pulls the branch's variables into
your local `.env`. Run it after every edit.

## Table of Contents

- [Getting one](#getting-one)
- [Shape](#shape)
- [Services](#services)
- [Functions](#functions)
- [Buckets](#buckets)
- [Branch policy](#branch-policy)
- [Typed env access](#typed-env-access)
- [Gotchas](#gotchas)

## What it does and doesn't cover

Covers: which services exist (`auth`, `dataApi`, `aiGateway`, `functions`, `buckets`) and per-branch tuning.
`neon deploy` provisions the declared services **and deploys function code** (it reads `source` and
`bundler`), then writes credentials to `.env.local`. `neon checkout` creates new branches from this policy,
so TTL and compute settings apply at creation.

Does **not** cover: triggers/cron, IP allow lists, VPC restrictions, roles, databases, or snapshots
schedules. Those stay CLI-only.

## Getting one

```bash
neon link                 # must be linked first
neon config init          # scaffolds neon.ts and installs the packages
neon config init --from-branch main   # seed it from a branch's live state
```

By hand: `npm install @neon/config`, which provides `defineConfig`. Two optional companions: `@neon/env`
(type-safe access to injected variables) and `@neon/config-runtime` (run inspect/plan/apply yourself
instead of through the CLI).

## Shape

```ts
// neon.ts
import { defineConfig } from "@neon/config/v1";

export default defineConfig({
  // Services — what exists on every branch
  auth: true,

  // Branch policy — per-branch tuning
  branch: (branch) => {
    if (branch.isDefault) return {};        // leave the default branch on project defaults
    if (!branch.exists) return { ttl: "7d" }; // new non-default branches auto-expire
    return {};                                // existing branches: change nothing
  },
});
```

Returning `{}` for existing branches is deliberate, not lazy: the closure runs against branches already in
use, and returning tuning there would overwrite settings someone else set.

## Services

Declare only what you use. Postgres is always present, so `DATABASE_URL` is injected without being declared.

| Field | Values | Default | Injects |
|---|---|---|---|
| `auth` | `true` / `false` / `{ enabled }` | `false` | `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL` |
| `dataApi` | `true` / `false` / `DataApiConfig` | `false` | `NEON_DATA_API_URL` |
| `aiGateway` | `true` / `false` / `{ enabled }` | `false` | `NEON_AI_GATEWAY_TOKEN`, `NEON_AI_GATEWAY_BASE_URL` |
| `functions` | record of slug → definition | none | `NEON_FUNCTION_<SLUG>_BASE_URL` per function |
| `buckets` | record of name → definition | none | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`, `AWS_REGION` |

`dataApi: true` uses Managed Better Auth as the JWT verifier, which requires `auth: true` as well — omitting
it is a TypeScript error at the `dataApi` field that spells out the fix.

**Version note:** `@neon/config` 1.6.0+ takes `aiGateway`, `functions` and `buckets` as top-level keys.
Declaring them under a `preview` block still works but warns on deploy. If a top-level key errors as
"unknown", the installed package is older than 1.6.0 — upgrade rather than moving the key back.

## Functions

Each key is the function's **slug** — the permanent identifier used in CLI commands and the invocation URL.

```ts
functions: {
  myrestapi: {
    name: "My REST API",       // human-readable label
    source: "./api/index.ts",  // entry file, relative to neon.ts
    env: { API_KEY: process.env.API_KEY ?? "" },
    bundler: "esbuild",        // "esbuild" | "none" | (fn) => Promise<FunctionBundle>
    dev: { port: 3001 },       // neon dev only; never affects deploy
  },
},
```

`dev.port` is **per function** — each declared function gets its own local port under `neon dev`, and an
omitted port is auto-assigned (a taken one fails rather than falling back). That is distinct from the CLI's
own `neon dev --port`, so two functions do not contend for one port.

**`neon.ts` cannot declare triggers.** The service keys are exactly `auth`, `dataApi`, `aiGateway`,
`functions` and `buckets` — there is no `triggers:` or `schedule:` key, and inventing one fails as an
unknown key. Cron scheduling stays an imperative CLI step: `neon deploy` ships the function, then
`neon triggers create --function-slug <slug> --name <name> --cron '<utc expr>'` schedules it. If a project
wants scheduling reproducible, script that call alongside the deploy; config-as-code does not cover it.

Slugs must match `^[a-z0-9]{1,20}$` — no separators — and are **immutable after first deployment**. That is
why `name` exists. Picking a slug is a one-way door, so pick a short generic one and put the readable
version in `name`.

`env` values resolve **at deploy time**, in the shell running `neon deploy` — not at function runtime.
`process.env.X` here captures your machine's value and bakes it in. Every value must be a defined string,
hence the `?? ""` fallback. Load a file first with `neon deploy --env .env.production`.

`bundler: "none"` ships a prebuilt directory as-is, in which case the entry must be `index.mjs` or
`index.js`; it is the config form of the CLI's `--no-bundle`. A function value lets a framework that
already emits build output deploy it unchanged.

## Buckets

```ts
buckets: {
  "my-bucket": { access: "private" },   // "private" (default) | "public_read"
},
```

Names follow S3 naming rules — hyphens are fine here, which is the **opposite** of the function-slug rule
two sections up (`^[a-z0-9]{1,20}$`, no separators). Both are record keys in the same config object with
contradictory constraints, so it is an easy one to get backwards.

The config field is `access`; the equivalent CLI flag on `neon buckets create` is `--access-level`. The
near-miss naming is real, not a typo in either place.

`public_read` makes objects reachable without credentials at the branch's storage endpoint — a deliberate
choice, not a convenience.

## Branch policy

The `branch` closure receives a read-only `BranchTarget` and returns `BranchTuning`. It can adjust
settings but cannot add or remove services.

**`BranchTarget`** (what you get): `name`, `id?`, `exists`, `isDefault?`, `isProtected?`, `parentId?`,
`expiresAt?`. During *pre-create* evaluation `exists` is `false` and `id` / `isDefault` / `isProtected` are
unset — so guard on `exists` before reading them.

**`BranchTuning`** (what you return):

| Field | Notes |
|---|---|
| `parent` | Parent branch name or ID |
| `protected` | Mark the branch protected |
| `ttl` | `"7d"`, `"2h"`, or seconds. **Max 30 days.** Validated at deploy time, not by TypeScript — a bad value compiles fine and fails on deploy |
| `postgres.computeSettings.autoscalingLimitMinCu` | 0.25, 0.5, every integer 1–16, even sizes 18–56 |
| `postgres.computeSettings.autoscalingLimitMaxCu` | For a range keep both bounds ≤ 16 and ≤ 8 CU apart; above 16 is fixed-size (min must equal max) |
| `postgres.computeSettings.suspendTimeout` | Idle suspend; `false` disables it |

A TTL on new non-default branches is the single highest-value policy here — it makes abandoned preview
branches clean themselves up instead of accruing storage.

## Typed env access

```bash
npm install @neon/env
```

```ts
import { parseEnv } from "@neon/env";
import config from "./neon";

const env = parseEnv(config);
env.postgres.databaseUrl;          // DATABASE_URL
env.postgres.databaseUrlUnpooled;  // DATABASE_URL_UNPOOLED
env.branch.name;                   // NEON_BRANCH
env.auth.baseUrl;                  // when auth: true
env.dataApi.url;                   // when dataApi enabled
env.aiGateway.apiKey;              // when aiGateway enabled
env.storage.accessKeyId;           // when buckets declared
```

`parseEnv` validates `process.env` against the declared services and throws a clear error on anything
missing or empty — the failure lands at startup instead of at the first query.

**Without writing secrets to disk**, `@neon/env` ships a `neon-env` binary:

```bash
neon-env run -- npm run dev        # inject the branch's vars into a command
neon-env export                     # dotenv lines on stdout
neon-env export --format json
```

This is the runtime counterpart to the on-disk `neon env pull`; pair it with `neon link --no-env-pull` when
you'd rather keep nothing in the working tree.

`fetchEnv` is the programmatic sibling — it fetches a branch's env from Neon and returns the same typed
shape. Unlike the `neon-env` CLI it reads **no** env vars or credential files on your behalf, so the API key
must be passed explicitly or it throws:

```ts
const env = await fetchEnv(config, { projectId: "...", branch: "main", apiKey: process.env.NEON_API_KEY });
```

## Gotchas

- **`env` resolves at deploy time.** A function reading a secret from `neon.ts` `env` gets whatever was in
  the deploying shell, frozen. Rotating that secret requires a redeploy.
- **Slugs are immutable.** Renaming means a new function and a new URL.
- **`ttl` isn't type-checked.** Over 30 days compiles and fails at deploy.
- **`neon dev` is stricter than `env pull`.** A declared function whose env value is unset is skipped by
  `env pull` but stops `dev`, `deploy`, and `neon-env run`.
- **"keys can be lifted out of preview"** on deploy means you're on 1.6.0+ and should move `functions` /
  `buckets` / `aiGateway` to the top level. **"unknown keys"** means the opposite: the package is older than
  1.6.0 and doesn't know the top-level form yet.
