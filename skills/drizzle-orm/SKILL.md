---
name: drizzle-orm
description: "Expert guidance for Drizzle ORM and drizzle-kit, covering the v1.0.0-beta (RQBv2, defineRelations, new migration folder structure, consolidated validators) and stable 0.x releases. Includes Node 24 node:sqlite integration with drizzle-orm/node-sqlite driver, drizzle-orm/zod validation (createInsertSchema, createSelectSchema, createUpdateSchema, createSchemaFactory), schema design for all dialects (SQLite preferred, PostgreSQL, MySQL, MSSQL), migrations (generate/migrate), rapid prototyping (push), and drizzle-seed. Use when: (1) working with Drizzle ORM projects, (2) setting up or running migrations with drizzle-kit, (3) using Node 24 built-in node:sqlite with Drizzle, (4) validating data with drizzle-orm/zod or drizzle-zod, (5) upgrading from 0.x to v1 beta, (6) defining relations with defineRelations or RQBv2, (7) seeding databases with drizzle-seed, (8) configuring drizzle.config.ts, or (9) any Drizzle ORM question."
---

# Drizzle ORM Skill

## Version Verification (MANDATORY)

**Before writing any Drizzle code, verify current versions.** The beta evolves rapidly.

Run these checks at the start of every Drizzle task:
```bash
# Check latest stable and beta versions
npm view drizzle-orm dist-tags --json
npm view drizzle-kit dist-tags --json
```

Also check GitHub releases for breaking changes:
- https://github.com/drizzle-team/drizzle-orm/releases
- https://orm.drizzle.team/docs/latest-releases

**Last verified:** March 2026 — `drizzle-orm@beta` = `1.0.0-beta.18`, `drizzle-orm@latest` = `0.45.1`

If the user is on the beta, install with:
```bash
pnpm add drizzle-orm@beta
pnpm add -D drizzle-kit@beta
```

## Dialect Preference

Default to **SQLite** (especially with `node:sqlite`) unless the user specifies otherwise. All three major dialects are supported: SQLite, PostgreSQL, MySQL, plus MSSQL in the v1 beta.

## Node 24 + node:sqlite (Preferred SQLite Driver)

Node.js 22+ ships a built-in `node:sqlite` module (release candidate as of Node 25). No native addons needed — zero-dependency SQLite.

```typescript
import { drizzle } from "drizzle-orm/node-sqlite";

// Simple — pass a file path
const db = drizzle("sqlite.db");

// Explicit — use DatabaseSync directly
import { DatabaseSync } from "node:sqlite";
const sqlite = new DatabaseSync("sqlite.db");
const db = drizzle({ client: sqlite });

// In-memory
const db = drizzle(":memory:");

// With relations (v1 beta)
import { relations } from "./relations";
const db = drizzle("sqlite.db", { relations });
```

### node:sqlite API Essentials

```typescript
import { DatabaseSync } from "node:sqlite";

const database = new DatabaseSync("app.db");

// Execute raw SQL (no return value)
database.exec("PRAGMA journal_mode = WAL");
database.exec("PRAGMA foreign_keys = ON");

// Prepared statements
const stmt = database.prepare("SELECT * FROM users WHERE id = ?");
const row = stmt.get(1);        // Single row
const rows = stmt.all();        // All rows
stmt.run(params);               // INSERT/UPDATE/DELETE

// Iterate (memory-efficient for large result sets)
for (const row of stmt.iterate()) { /* ... */ }

// Custom functions
database.function("upper_custom", (str) => str.toUpperCase());

// Aggregate functions (Node 24+)
database.aggregate("sum_custom", {
  start: 0,
  step: (acc, val) => acc + val,
});

// Transaction check (Node 24+)
database.isTransaction; // boolean

// Tagged template queries (Node 24.9+, SQLTagStore)
const sql = database.createTagStore();
const user = sql.get`SELECT * FROM users WHERE id = ${1}`;
const allUsers = sql.all`SELECT * FROM users`;
sql.run`INSERT INTO users (name) VALUES (${"Alice"})`;

// Async backup
import sqlite from "node:sqlite";
await sqlite.backup(database, "backup.db");

// Cleanup (also supports `using` keyword)
database.close();
```

### drizzle-kit + node:sqlite

As of beta.18, `drizzle-kit` fully supports `node:sqlite` for migrations, push, and studio. It auto-detects `node:sqlite` at runtime — no extra driver install needed.

### drizzle.config.ts for node:sqlite

```typescript
import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "sqlite",
  schema: "./src/schema.ts",
  out: "./drizzle",
  dbCredentials: {
    url: "sqlite.db",
  },
});
```

### When to Use node:sqlite vs better-sqlite3

| Factor | node:sqlite | better-sqlite3 |
|--------|-------------|-----------------|
| Dependencies | Zero (built-in) | Native addon (node-gyp) |
| Node version | 22+ (flag), 24+ (no flag) | Any |
| Stability | Release candidate | Mature/stable |
| Performance | Good, improving | Highly optimized |
| Extensions | `loadExtension()` supported | `loadExtension()` supported |
| Drizzle driver | `drizzle-orm/node-sqlite` | `drizzle-orm/better-sqlite3` |

**Prefer node:sqlite** for new projects on Node 24+. Use better-sqlite3 if you need maximum perf, older Node versions, or `db.transaction()` helper (node:sqlite requires manual BEGIN/COMMIT).

### Recommended SQLite Pragmas

```typescript
const database = new DatabaseSync("app.db");
database.exec("PRAGMA journal_mode = WAL");
database.exec("PRAGMA synchronous = NORMAL");
database.exec("PRAGMA foreign_keys = ON");
database.exec("PRAGMA cache_size = -64000");     // 64MB
database.exec("PRAGMA temp_store = MEMORY");
```

## v1 Beta: Breaking Changes from 0.x

See [references/v1-migration.md](references/v1-migration.md) for the complete migration guide.

### Key Changes Summary

| Area | 0.x | v1 Beta |
|------|-----|---------|
| Relations | `relations()` per-table | `defineRelations()` centralized |
| Relation fields | `fields` / `references` | `from` / `to` |
| DB init | `drizzle(url, { schema })` | `drizzle(url, { relations })` |
| RQB where | Callback: `(t, ops) => eq(t.id, 1)` | Object: `{ id: 1 }` |
| Validators | `drizzle-zod` (separate pkg) | `drizzle-orm/zod` (built-in) |
| Migrations | `journal.json` + flat files | Folder-per-migration |
| PG arrays | `.array().array()` | `.array('[][]')` |
| RLS | `.enableRLS()` | `pgTable.withRLS()` |
| MySQL mode | `mode: "planetscale"` | Removed (auto-detected) |
| `getTableColumns()` | Available | Renamed to `getColumns()` |

### Relations v2 (RQBv2)

```typescript
import { defineRelations } from "drizzle-orm";
import * as schema from "./schema";

export const relations = defineRelations(schema, (r) => ({
  users: {
    posts: r.many.posts(),
    profile: r.one.profiles({
      from: r.users.id,
      to: r.profiles.userId,
    }),
  },
  posts: {
    author: r.one.users({
      from: r.posts.authorId,
      to: r.users.id,
    }),
  },
}));

// Many-to-many via junction table
export const relations = defineRelations(schema, (r) => ({
  users: {
    groups: r.many.groups({
      from: r.users.id.through(r.usersToGroups.userId),
      to: r.groups.id.through(r.usersToGroups.groupId),
    }),
  },
}));
```

Split across files with `defineRelationsPart`:
```typescript
import { defineRelationsPart } from "drizzle-orm";
const usersRelations = defineRelationsPart(schema, (r) => ({
  users: { posts: r.many.posts() },
}));
```

### Object-Based Where (v1)

```typescript
// Simple equality
db.query.users.findMany({ where: { id: 1 } });

// Complex filters
db.query.users.findMany({
  where: {
    OR: [
      { name: { like: "John%" } },
      { name: { ilike: "jane%" } },
    ],
    age: { gte: 18 },
  },
});

// Raw SQL in where
db.query.users.findMany({
  where: { RAW: (table) => sql`LOWER(${table.name}) = 'admin'` },
});
```

### Backward Compatibility

You do NOT have to migrate everything at once:
- Old relations: `import { relations } from "drizzle-orm/_relations"`
- Old queries: `db._query.table.findMany()` (callback-based where still works)

## Schema Design

### SQLite (Preferred)

```typescript
import { sqliteTable, text, integer, real, blob } from "drizzle-orm/sqlite-core";

export const users = sqliteTable("users", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  age: integer("age"),
  active: integer("active", { mode: "boolean" }).default(true),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull()
    .$defaultFn(() => new Date()),
});

export const posts = sqliteTable("posts", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  content: text("content"),
  userId: integer("user_id").references(() => users.id),
});
```

### PostgreSQL

```typescript
import { pgTable, serial, text, integer, timestamp, pgEnum } from "drizzle-orm/pg-core";

export const roleEnum = pgEnum("role", ["admin", "user"]);

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  role: roleEnum("role").default("user"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
```

### Multiple Schema Files

```typescript
// drizzle.config.ts
export default defineConfig({
  schema: "./src/schema/**/*.ts",
});
```

## Zod Validation (drizzle-orm/zod)

**v1 beta:** `import { ... } from "drizzle-orm/zod"` (built-in, `drizzle-zod` deprecated)
**Stable 0.x:** `import { ... } from "drizzle-zod"` (separate package, `drizzle-orm@0.36.0+`, `zod@3.25.1+`)

### Generate Schemas

```typescript
import { createInsertSchema, createSelectSchema, createUpdateSchema } from "drizzle-orm/zod";

const userInsertSchema = createInsertSchema(users);   // For INSERT validation
const userSelectSchema = createSelectSchema(users);   // For SELECT result validation
const userUpdateSchema = createUpdateSchema(users);   // For UPDATE (all fields optional)
```

| Function | Generated Fields | Excluded |
|----------|-----------------|----------|
| `createSelectSchema` | All columns, all required | None |
| `createInsertSchema` | Required/optional based on defaults | `generatedAlwaysAs` columns |
| `createUpdateSchema` | All optional | `generatedAlwaysAs` columns |

Works with tables, views (`createSelectSchema` only), and enums (`createSelectSchema` only).

### Refinements

```typescript
import { z } from "zod";

const userInsertSchema = createInsertSchema(users, {
  email: (schema) => schema.email(),           // Callback: extend
  name: (schema) => schema.min(1).max(100),    // Callback: extend
  preferences: z.object({ theme: z.string() }), // Direct: overwrite entirely
});
```

**Custom types** generate `z.any()` — always override them:
```typescript
const selectSchema = createSelectSchema(team, {
  customCol: z.string(), // Override z.any() for custom column types
});
```

### Schema Factory (Advanced)

```typescript
import { createSchemaFactory } from "drizzle-orm/zod";
import { z } from "@hono/zod-openapi";

// Custom Zod instance (e.g., OpenAPI)
const { createInsertSchema } = createSchemaFactory({ zodInstance: z });

// Type coercion
const { createInsertSchema } = createSchemaFactory({
  coerce: { date: true }, // or coerce: true for all types
});
```

### Type Inference

```typescript
import { z } from "zod";
type UserInsert = z.infer<typeof userInsertSchema>;
type UserSelect = z.infer<typeof userSelectSchema>;

// Drizzle's native inference (complementary)
type User = typeof users.$inferSelect;
type NewUser = typeof users.$inferInsert;
```

### Common Patterns

```typescript
// Single source of truth: schema -> validation -> types
export const users = sqliteTable("users", { /* ... */ });
export const userInsertSchema = createInsertSchema(users, {
  email: (s) => s.email(),
});
export type UserInsert = z.infer<typeof userInsertSchema>;

// Form validation (omit server-managed fields)
export const userFormSchema = userInsertSchema.omit({ id: true, createdAt: true });

// PATCH endpoint (partial update)
export const userPatchSchema = userUpdateSchema;

// Pick specific fields
export const loginSchema = userInsertSchema.pick({ email: true });
```

For complete Zod column type mappings, see [references/zod-mappings.md](references/zod-mappings.md).

## Drizzle Kit Commands

### Migration Philosophy

**Always use `generate` + `migrate` for everything except throwaway local prototyping.**

### Generate Migrations

```bash
npx drizzle-kit generate
```

Creates SQL migration files by diffing current schema against last snapshot.

**v1 beta folder structure:**
```
drizzle/
  20250220153045_brave_wolverine/
    migration.sql
    snapshot.json
```

**0.x folder structure:**
```
drizzle/
  _meta/journal.json
  0000_init.sql
  0001_add_email.sql
```

### Apply Migrations

```bash
npx drizzle-kit migrate
```

Or at runtime:
```typescript
import { drizzle } from "drizzle-orm/node-sqlite";
import { migrate } from "drizzle-orm/node-sqlite/migrator";

const db = drizzle("sqlite.db");
await migrate(db, { migrationsFolder: "./drizzle" });
```

### Push (Prototyping Only)

```bash
npx drizzle-kit push  # ONLY for throwaway local databases
```

### Other Commands

| Command | Purpose |
|---------|---------|
| `drizzle-kit up` | Upgrade migration folder (0.x -> v1 format) |
| `drizzle-kit check` | Detect non-commutative migration conflicts |
| `drizzle-kit pull` | Introspect existing database schema |
| `drizzle-kit pull --init` | Introspect + mark as applied |
| `drizzle-kit generate --custom --name=X` | Custom migration file |
| `drizzle-kit generate --ignore-conflicts` | Bypass commutativity checks |
| `drizzle-kit studio` | Visual database browser |

## Configuration

```typescript
import { defineConfig } from "drizzle-kit";

export default defineConfig({
  out: "./drizzle",
  dialect: "sqlite",                   // "sqlite" | "postgresql" | "mysql" | "mssql"
  schema: "./src/schema.ts",
  dbCredentials: {
    url: "sqlite.db",                  // SQLite: file path
    // url: process.env.DATABASE_URL,  // PG/MySQL: connection string
  },
  migrations: {
    prefix: "timestamp",               // "timestamp" | "unix" | "supabase" | "none"
    table: "__drizzle_migrations__",
  },
  verbose: true,
});
```

## Seeding

See [references/seeding.md](references/seeding.md) for drizzle-seed generators, versioning, and refinements.

```typescript
import { seed, reset } from "drizzle-seed";
import * as schema from "./schema";

await reset(db, schema);
await seed(db, schema, { count: 100, seed: 12345 });
```

## Best Practices

1. **Verify versions** before writing Drizzle code (`npm view drizzle-orm dist-tags`)
2. **Always use migrations** for production (`generate` + `migrate`)
3. **Prefer node:sqlite** on Node 24+ for zero-dependency SQLite
4. **Use drizzle-orm/zod** on v1 beta (not the separate `drizzle-zod` package)
5. **Review generated SQL** before applying migrations
6. **Commit migration files** to version control
7. **Use defineRelations** on v1 beta (not per-table `relations()`)
8. **Pin seed version** for deterministic test data
9. **Set WAL mode** for SQLite: `database.exec("PRAGMA journal_mode = WAL")`
10. **Enable foreign keys** for SQLite: `database.exec("PRAGMA foreign_keys = ON")`
