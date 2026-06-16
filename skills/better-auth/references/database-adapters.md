# Better Auth — database adapters

How to pass a `database` to `betterAuth()`, what schema it creates, and how to apply that schema per ORM. Part of [the skill overview](../SKILL.md).

## Contents

- [Three ways to pass `database`](#three-ways-to-pass-database)
- [Built-in Kysely (raw driver)](#built-in-kysely-raw-driver)
- [Drizzle — `drizzleAdapter`](#drizzle--drizzleadapter)
- [Prisma — `prismaAdapter`](#prisma--prismaadapter)
- [MongoDB — `mongodbAdapter`](#mongodb--mongodbadapter)
- [The 4 core tables](#the-4-core-tables)
- [generate vs migrate](#generate-vs-migrate)
- [Customizing table & field names](#customizing-table--field-names)
- [ID generation](#id-generation)
- [Plugins add tables](#plugins-add-tables)
- [Secondary storage (Redis)](#secondary-storage-redis)

## Three ways to pass `database`

`database` accepts exactly **one of three shapes**. Picking the wrong one is the first thing to get right, because it decides whether `migrate` works.

```ts
import { betterAuth } from "better-auth";
// v1.5+ also ships a tree-shakeable entry: import { betterAuth } from "better-auth/minimal";
```

| Shape | Example | `migrate` works? |
|---|---|---|
| **Raw driver instance** (built-in Kysely) | `database: new Pool({ ... })` | Yes — this is the only path that supports `migrate` |
| **Kysely `{ dialect, type }`** | `database: { dialect, type: "postgres" }` | Yes (still the built-in Kysely engine) |
| **Adapter factory call** | `database: drizzleAdapter(db, { provider: "pg" })` | No — the ORM runs its own migrations |

The reason: only the built-in Kysely adapter knows how to introspect and ALTER your tables. Drizzle and Prisma own their own migration tooling, so Better Auth defers to them (see [generate vs migrate](#generate-vs-migrate)).

## Built-in Kysely (raw driver)

Pass a raw driver instance and Better Auth wraps it in Kysely for you — **no adapter import**. This is the lowest-friction path and the only one where `npx @better-auth/cli@latest migrate` applies schema directly.

```ts
// PostgreSQL — pg Pool
import { betterAuth } from "better-auth";
import { Pool } from "pg";
export const auth = betterAuth({
  database: new Pool({ connectionString: "postgres://user:password@localhost:5432/database" }),
});
```

```ts
// MySQL — mysql2/promise createPool
import { betterAuth } from "better-auth";
import { createPool } from "mysql2/promise";
export const auth = betterAuth({
  database: createPool({ host: "localhost", user: "root", password: "password", database: "database", timezone: "Z" }),
  // timezone:"Z" keeps stored dates consistent (UTC) instead of local-server time
});
```

```ts
// SQLite — better-sqlite3 (use new Database(":memory:") for tests)
import { betterAuth } from "better-auth";
import Database from "better-sqlite3";
export const auth = betterAuth({ database: new Database("database.sqlite") });
```

**Explicit Kysely dialect form** — use when you need a custom dialect (LibSQL/Turso, Cloudflare D1, or non-default pool config). `database` takes `{ dialect, type }`:

```ts
import { betterAuth } from "better-auth";
import { Kysely, PostgresDialect } from "kysely";
import { Pool } from "pg";
export const auth = betterAuth({
  database: {
    dialect: new PostgresDialect({ pool: new Pool({ connectionString: "..." }) }),
    type: "postgres", // "postgres" | "mysql" | "sqlite" | "mssql"
  },
});
```

You can also pass a fully-built `new Kysely({ dialect })` instance directly as `database`. The `{ dialect, type }` shape is documented under "Other Relational Databases" — if the `type` enum key gives you trouble, confirm it against that page for your version.

## Drizzle — `drizzleAdapter`

```ts
import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "@/db"; // your drizzle instance
export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: "pg", // "pg" | "mysql" | "sqlite"  — REQUIRED
  }),
});
```

Signature: `drizzleAdapter(db, { provider, schema?, usePlural? })`.

| Option | Type | Notes |
|---|---|---|
| `provider` | `"pg" \| "mysql" \| "sqlite"` | Required — must match your Drizzle dialect |
| `schema` | object | Your Drizzle schema, used to map Better Auth model names → your table exports |
| `usePlural` | boolean | Set `true` if your table variables are pluralized (`users`, `sessions`, …) |

> Import-path note: the subpath `better-auth/adapters/drizzle` is the safe default. v1.5+ also added a dedicated tree-shakeable package, `@better-auth/drizzle-adapter` (pairs with `better-auth/minimal`). Both appear in current docs — use the subpath unless you've deliberately opted into the minimal build.

**Mapping when your table names differ.** Better Auth wants a model named `user`, but your export is `users`. Bridge it either in the adapter's `schema`:

```ts
database: drizzleAdapter(db, {
  provider: "sqlite",
  schema: { ...schema, user: schema.users },
}),
```

…or via the auth config (and let `schema` pass through untouched):

```ts
database: drizzleAdapter(db, { provider: "sqlite", schema }),
user: { modelName: "users" },
```

Rename a **field** either in the Drizzle column def (`varchar("email_address")`) or via `user: { fields: { email: "email_address" } }`. See [Customizing table & field names](#customizing-table--field-names).

## Prisma — `prismaAdapter`

```ts
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
export const auth = betterAuth({
  database: prismaAdapter(prisma, {
    provider: "sqlite", // must match your schema.prisma datasource
  }),
});
```

Signature: `prismaAdapter(prismaClient, { provider })`. `provider` is required and must equal your `schema.prisma` datasource provider — `"sqlite" | "postgresql" | "mysql" | "cockroachdb" | "sqlserver" | "mongodb"`.

> Prisma 7+: if your `schema.prisma` sets a custom client `output` path, import `PrismaClient` from **that path**, not `@prisma/client` — otherwise the generated client won't be found.

## MongoDB — `mongodbAdapter`

```ts
import { betterAuth } from "better-auth";
import { mongodbAdapter } from "better-auth/adapters/mongodb";
import { MongoClient } from "mongodb";
const client = new MongoClient("mongodb://localhost:27017/database");
const db = client.db();
export const auth = betterAuth({
  database: mongodbAdapter(db, { client }), // pass the Db as the 1st arg
});
```

Signature: `mongodbAdapter(db, { client? })`. The first argument is the `Db` instance (`client.db()`). Pass `{ client }` to enable transactions — without a client, database transactions are disabled. MongoDB is schemaless, so **`generate` and `migrate` do not apply** — there's nothing to scaffold or migrate.

## The 4 core tables

Every install creates these four tables (column types shown for default `string` IDs; `?` = nullable). Plugins extend this set — see [Plugins add tables](#plugins-add-tables).

| Table | Column | Type |
|---|---|---|
| **user** | id | string (PK) |
| | name | string |
| | email | string (unique) |
| | emailVerified | boolean (default false) |
| | image | string? |
| | createdAt / updatedAt | Date |
| **session** | id | string (PK) |
| | userId | string (FK → user.id, cascade) |
| | token | string (unique) |
| | expiresAt | Date |
| | ipAddress / userAgent | string? |
| | createdAt / updatedAt | Date |
| **account** | id | string (PK) |
| | userId | string (FK → user.id, cascade) |
| | accountId | string |
| | providerId | string |
| | accessToken / refreshToken | string? |
| | accessTokenExpiresAt / refreshTokenExpiresAt | Date? |
| | scope / idToken | string? |
| | password | string? (email-password credential hash) |
| | createdAt / updatedAt | Date |
| **verification** | id | string (PK) |
| | identifier | string |
| | value | string |
| | expiresAt | Date |
| | createdAt / updatedAt | Date |

The generator also adds indexes on `session.userId`, `account.userId`, and `verification.identifier`.

## generate vs migrate

Two different CLI verbs, and the difference trips up most integrators. The canonical command is `npx @better-auth/cli@latest …` (short alias: `npx auth@latest …`).

- **`generate`** — emits the schema **for your ORM/adapter**: `auth-schema.ts` (Drizzle), appended models in `schema.prisma` (Prisma), or an SQL file (Kysely). Flags: `--output <path>`, `--config <path-to-auth.ts>`, `--yes` (skip confirm). It writes files; it does **not** touch the database.
- **`migrate`** — applies schema **directly to the DB**, but **only with the built-in Kysely adapter**. For any other adapter the CLI errors out and tells you to `generate` then use your ORM's own migrate. So Drizzle and Prisma users run `generate`, then hand off to `drizzle-kit` / `prisma`.

Per-adapter workflow:

| Adapter | generate | apply |
|---|---|---|
| Built-in Kysely (raw pg/mysql/sqlite) | optional | `npx @better-auth/cli@latest migrate` |
| Drizzle | `generate` → `auth-schema.ts` | `npx drizzle-kit generate` + `npx drizzle-kit migrate` |
| Prisma | `generate` → `schema.prisma` | `npx prisma migrate dev` (or `npx prisma db push`) |
| MongoDB | n/a | n/a (schemaless) |

## Customizing table & field names

Map Better Auth's model/field names onto your existing schema. Type inference always uses the **original** names (`user.name`, never `user.full_name`), so this is purely a storage-layer rename.

```ts
export const auth = betterAuth({
  user: {
    modelName: "users",
    fields: { name: "full_name", email: "email_address" },
  },
  session: {
    modelName: "user_sessions",
    fields: { userId: "user_id" },
  },
});
```

## ID generation

Default IDs are random strings. Override under `advanced.database`:

| Setting | Effect |
|---|---|
| `generateId: false` | Let the DB generate IDs (defaults / auto-increment) |
| `generateId: "serial"` | Auto-incrementing numeric IDs (Postgres serial / SQLite autoincrement) |
| `generateId: "uuid"` | UUID string IDs |
| `generateId: (options) => string \| false` | Custom per-model; `options.model` is the model name, return `false` to defer to the DB |

```ts
betterAuth({
  database: db,
  advanced: { database: { generateId: "serial" } },
});

// mixed: DB-serial user IDs, UUID elsewhere
betterAuth({
  database: db,
  advanced: { database: { generateId: (o) =>
    (o.model === "user" || o.model === "users") ? false : crypto.randomUUID() } },
});
```

`useNumberId: boolean` is the **legacy** global toggle for numeric IDs across all tables. Avoid it for mixed-ID setups — because it's global it forces every table numeric; reach for the `generateId` callback instead. With numeric IDs, generated Drizzle `id` columns become `integer("id").generatedByDefaultAsIdentity().primaryKey()` (pg) / `integer("id", { mode: "number" }).primaryKey({ autoIncrement: true })` (sqlite), and `userId` FKs become `integer`.

## Plugins add tables

Plugins extend the schema automatically — `twoFactor` adds a `twoFactor` table, `passkey` adds `passkey`, `username` adds `username`/`displayUsername` columns to `user`, and so on. **After adding a schema plugin, re-run `generate` (and apply it).** Forgetting this is the #1 plugin error — "column/table does not exist" at runtime. Rename plugin fields via the plugin's own `schema` option:

```ts
import { twoFactor } from "better-auth/plugins";
betterAuth({
  plugins: [twoFactor({ schema: { user: { fields: { twoFactorEnabled: "two_factor_enabled" } } } })],
});
```

See [plugins.md](plugins.md) for the full catalog and which plugins touch the schema.

## Secondary storage (Redis)

`secondaryStorage` is a separate concern from the primary `database` adapter — it offloads sessions/rate-limit state to Redis (or any `get`/`set`/`delete` store) for performance. Configure it alongside, not instead of, `database`. Details and the production setup live in [security-and-production.md](security-and-production.md).

---

Sources: https://better-auth.com/docs
