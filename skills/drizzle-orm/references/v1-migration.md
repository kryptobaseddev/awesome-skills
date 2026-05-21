# Drizzle ORM v1 Migration Guide

Complete guide for upgrading from drizzle-orm 0.x to 1.0.0-beta.

## Table of Contents

- [Step-by-Step Upgrade](#step-by-step-upgrade)
- [Relations v2 (RQBv2)](#relations-v2-rqbv2)
- [Query Changes](#query-changes)
- [Schema Changes](#schema-changes)
- [Drizzle Kit Changes](#drizzle-kit-changes)
- [Validator Package Consolidation](#validator-package-consolidation)
- [New Features in v1](#new-features-in-v1)
- [Removed/Deprecated APIs](#removeddeprecated-apis)

## Step-by-Step Upgrade

### 1. Install beta packages
```bash
pnpm add drizzle-orm@beta
pnpm add -D drizzle-kit@beta
```

### 2. Run `drizzle-kit up`
Converts old `journal.json`-based migration folder to new folder-per-migration structure:
```bash
pnpm drizzle-kit up
```

### 3. Update validator imports
```typescript
// OLD
import { createInsertSchema } from "drizzle-zod";
// NEW
import { createInsertSchema } from "drizzle-orm/zod";

// Then remove old package
pnpm remove drizzle-zod
```

### 4. Update relations (incremental)
You can migrate incrementally. During transition:
- Old `relations()` import moves to `drizzle-orm/_relations`
- Old queries use `db._query.table.findMany()`
- New queries use `db.query.table.findMany()` with object-based where

Full migration details: https://orm.drizzle.team/docs/relations-v1-v2

## Relations v2 (RQBv2)

### Old (0.x) — Per-table relation definitions
```typescript
import { relations } from "drizzle-orm";

export const usersRelation = relations(users, ({ one, many }) => ({
  invitee: one(users, {
    fields: [users.invitedBy],
    references: [users.id],
  }),
  posts: many(posts),
}));

export const postsRelation = relations(posts, ({ one }) => ({
  author: one(users, {
    fields: [posts.authorId],
    references: [users.id],
  }),
}));
```

### New (v1) — Centralized `defineRelations`
```typescript
import { defineRelations } from "drizzle-orm";
import * as schema from "./schema";

export const relations = defineRelations(schema, (r) => ({
  users: {
    invitee: r.one.users({
      from: r.users.invitedBy,
      to: r.users.id,
    }),
    posts: r.many.posts(),
  },
  posts: {
    author: r.one.users({
      from: r.posts.authorId,
      to: r.users.id,
    }),
  },
}));
```

### Key differences
- `fields` renamed to `from`, `references` renamed to `to`
- Single centralized location instead of per-table
- `r.one.tableName()` / `r.many.tableName()` syntax
- DB instance takes `{ relations }` instead of `{ schema }`

### Many-to-many via junction table (NEW)
```typescript
export const relations = defineRelations(schema, (r) => ({
  users: {
    groups: r.many.groups({
      from: r.users.id.through(r.usersToGroups.userId),
      to: r.groups.id.through(r.usersToGroups.groupId),
    }),
  },
}));
```

### Split across files with `defineRelationsPart`
```typescript
import { defineRelationsPart } from "drizzle-orm";

const usersRelations = defineRelationsPart(schema, (r) => ({
  users: { posts: r.many.posts() },
}));

const postsRelations = defineRelationsPart(schema, (r) => ({
  posts: { author: r.one.users({ from: r.posts.authorId, to: r.users.id }) },
}));
```

### Required relations (NEW)
```typescript
posts: r.many.posts({
  from: r.users.id,
  to: r.posts.authorId,
  optional: false, // TypeScript requires author to exist
}),
```

### Database initialization change
```typescript
// OLD
import * as schema from "./schema";
const db = drizzle(process.env.DATABASE_URL, { schema });

// NEW
import { relations } from "./relations";
const db = drizzle(process.env.DATABASE_URL, { relations });
```

## Query Changes

### Where clause — callback to object
```typescript
// OLD (callback-based)
db.query.users.findMany({
  where: (users, { eq }) => eq(users.id, 1),
});

// NEW (object-based)
db.query.users.findMany({
  where: { id: 1 },
});

// Complex filters
db.query.users.findMany({
  where: {
    AND: [
      { OR: [
        { RAW: (table) => sql`LOWER(${table.name}) LIKE 'john%'` },
        { name: { ilike: "jane%" } },
      ]},
    ],
  },
});
```

### Column alias (NEW)
```typescript
const query = db
  .select({ age: users.age.as("ageOfUser"), id: users.id.as("userId") })
  .from(users);
```

### BigInt preservation (NEW)
BigInt values in JSON/RQB results are now returned as strings to prevent data loss:
```
// Old: { bigint: 5044565289845416000 }  // Partial data loss
// New: { bigint: "5044565289845416380" } // Preserved
```

## Schema Changes

### PostgreSQL arrays
```typescript
// OLD (chainable)
column.array().array()

// NEW (string argument)
column.array("[][]")
column.array("[][][]")
```

### RLS tables
```typescript
// OLD
const users = pgTable("users", { ... }).enableRLS();

// NEW
const users = pgTable.withRLS("users", { ... });
```

### MySQL mode removed
```typescript
// OLD
const db = drizzle(url, { mode: "planetscale", schema });

// NEW — auto-detected
const db = drizzle(url, { relations });
```

### Custom types (new RQBv2 fields)
```typescript
const customBytes = customType<{
  data: Buffer;
  driverData: Buffer;
  jsonData: string;  // NEW
}>({
  dataType: () => "bytea",
  fromJson: (value) => Buffer.from(value.slice(2), "hex"),       // NEW
  forJsonSelect: (id, sql, dims) =>                               // NEW
    sql`${id}::text${sql.raw("[]".repeat(dims ?? 0))}`,
});
```

## Drizzle Kit Changes

| Change | Details |
|--------|---------|
| Folder structure | `journal.json` removed; individual folders with `migration.sql` + `snapshot.json` |
| `drizzle-kit up` | Converts old journal format to new v3 folder format |
| `drizzle-kit drop` | Removed entirely |
| `drizzle-kit check` | New — detects non-commutative migration conflicts |
| `drizzle-kit pull --init` | New — creates migration table, marks first pull as applied |
| `drizzle-kit migrate` | Versioned migration table (adds `name`, `applied_at` columns) |
| `--ignore-conflicts` | New flag for `generate` to bypass commutativity checks |
| `schemaFilter` | Now manages all schemas in code by default; supports globs |
| `strict` flag | Silently deprecated in push config |
| Loader | Migrated from `esbuild-register` to `tsx`; top-level await supported |
| Alternation engine | Completely rewritten; tests from ~600 to 3000+ |

## Validator Package Consolidation

| Old Package | New Import (v1) |
|-------------|-----------------|
| `drizzle-zod` | `drizzle-orm/zod` |
| `drizzle-valibot` | `drizzle-orm/valibot` |
| `drizzle-typebox` | `drizzle-orm/typebox` |
| `drizzle-arktype` | `drizzle-orm/arktype` |

## New Features in v1

| Feature | Since | Description |
|---------|-------|-------------|
| MSSQL support | beta.2 | Full Microsoft SQL Server support |
| `through` for M:N | beta.2 | Many-to-many via junction tables |
| Column `.as()` | beta.2 | Column alias in select |
| `optional: false` | beta.2 | Required relations at type level |
| Native Bun/Deno | beta.2 | Native runtime support in drizzle-kit |
| Effect logger/cache | beta.13 | Native Effect integration |
| Top-level await | beta.13 | In config and schema files via jiti |
| node:sqlite support | beta.13+ | Built-in Node.js SQLite driver |

## Removed/Deprecated APIs

| API | Replacement |
|-----|-------------|
| `relations()` | `defineRelations()` (or `drizzle-orm/_relations` for compat) |
| `db.query` (v1 style) | `db._query` (compat bridge for old where syntax) |
| `.enableRLS()` | `pgTable.withRLS()` |
| `drizzle-kit drop` | Manual deletion of migration folders |
| `journal.json` | Folder-based structure |
| `mode: "planetscale"` | Removed (auto-detected) |
| `{ schema }` in drizzle() | `{ relations }` |
| `getTableColumns()` | `getColumns()` |
| Separate validator packages | `drizzle-orm/zod`, `drizzle-orm/valibot`, etc. |

## Official Resources

- Upgrade guide: https://orm.drizzle.team/docs/upgrade-v1
- Relations migration: https://orm.drizzle.team/docs/relations-v1-v2
- Release notes: https://orm.drizzle.team/docs/latest-releases
- GitHub releases: https://github.com/drizzle-team/drizzle-orm/releases
