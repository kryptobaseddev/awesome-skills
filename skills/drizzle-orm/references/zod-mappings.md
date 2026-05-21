# Drizzle to Zod Type Mappings

Complete reference of how Drizzle column types map to Zod validation schemas.

## Table of Contents

- [Boolean](#boolean)
- [Date](#date)
- [String](#string)
- [Number](#number)
- [BigInt](#bigint)
- [JSON](#json)
- [Enum](#enum)
- [Array](#array)
- [Buffer](#buffer)
- [Custom Types](#custom-types)

## Boolean

| Drizzle | Zod |
|---------|-----|
| `pg.boolean()` | `z.boolean()` |
| `mysql.boolean()` | `z.boolean()` |
| `sqlite.integer({ mode: "boolean" })` | `z.boolean()` |

## Date

| Drizzle | Zod |
|---------|-----|
| `pg.date({ mode: "date" })` | `z.date()` |
| `pg.timestamp({ mode: "date" })` | `z.date()` |
| `mysql.date({ mode: "date" })` | `z.date()` |
| `mysql.datetime({ mode: "date" })` | `z.date()` |
| `mysql.timestamp({ mode: "date" })` | `z.date()` |
| `sqlite.integer({ mode: "timestamp" })` | `z.date()` |
| `sqlite.integer({ mode: "timestamp_ms" })` | `z.date()` |

## String

### Generic String
| Drizzle | Zod |
|---------|-----|
| `pg.text()` | `z.string()` |
| `pg.varchar()` | `z.string().max(N)` |
| `pg.char()` | `z.string().length(N)` |
| `pg.numeric()` | `z.string()` |
| `pg.cidr()` / `pg.inet()` / `pg.macaddr()` | `z.string()` |
| `pg.date({ mode: "string" })` | `z.string()` |
| `pg.timestamp({ mode: "string" })` | `z.string()` |
| `mysql.text()` / `mysql.varchar()` / `mysql.char()` | `z.string()` |
| `mysql.decimal()` | `z.string()` |
| `mysql.date({ mode: "string" })` | `z.string()` |
| `sqlite.text({ mode: "text" })` | `z.string()` |
| `sqlite.numeric()` | `z.string()` |

### UUID
| Drizzle | Zod |
|---------|-----|
| `pg.uuid()` | `z.string().uuid()` |

### Enum String
| Drizzle | Zod |
|---------|-----|
| `pg.text({ enum: [...] })` | `z.enum([...])` |
| `mysql.text({ enum: [...] })` | `z.enum([...])` |
| `sqlite.text({ enum: [...] })` | `z.enum([...])` |

## Number

| Drizzle | Zod |
|---------|-----|
| `pg.integer()` / `pg.smallint()` | `z.number().int()` |
| `pg.serial()` / `pg.smallserial()` | `z.number().int()` |
| `pg.real()` / `pg.doublePrecision()` | `z.number()` |
| `mysql.int()` / `mysql.smallint()` / `mysql.tinyint()` | `z.number().int()` |
| `mysql.float()` / `mysql.double()` | `z.number()` |
| `mysql.serial()` | `z.number().int()` |
| `sqlite.integer()` | `z.number().int()` |
| `sqlite.real()` | `z.number()` |

## BigInt

| Drizzle | Zod |
|---------|-----|
| `pg.bigint()` / `pg.bigserial()` | `z.bigint()` |
| `mysql.bigint()` | `z.bigint()` |

**Note (v1 beta):** BigInt values in RQB/JSON results are returned as strings to prevent data loss.

## JSON

| Drizzle | Zod |
|---------|-----|
| `pg.json()` / `pg.jsonb()` | `z.any()` |
| `mysql.json()` | `z.any()` |
| `sqlite.text({ mode: "json" })` | `z.any()` |

**Always override JSON columns** with a specific schema:
```typescript
const schema = createSelectSchema(table, {
  metadata: z.object({ key: z.string() }),
});
```

## Enum

| Drizzle | Zod |
|---------|-----|
| `pgEnum("role", ["admin", "user"])` | `z.enum(["admin", "user"])` |
| `mysql.mysqlEnum("role", [...])` | `z.enum([...])` |

## Array (PostgreSQL)

| Drizzle | Zod |
|---------|-----|
| `pg.integer().array()` | `z.array(z.number().int())` |
| `pg.text().array()` | `z.array(z.string())` |

## Buffer

| Drizzle | Zod |
|---------|-----|
| `pg.bytea()` | `z.instanceof(Buffer)` |
| `mysql.binary()` / `mysql.varbinary()` | `z.string()` |
| `sqlite.blob({ mode: "buffer" })` | `z.instanceof(Buffer)` |

## Custom Types

Custom types always generate `z.any()`. Override them:
```typescript
const citext = customType<{ data: string }>({
  dataType() { return "citext"; },
});

const schema = createSelectSchema(table, {
  name: z.string(), // Override z.any()
});
```

## Nullability Rules

- **Select schemas:** Nullable columns become `z.type().nullable()`
- **Insert schemas:** Nullable columns become `z.type().nullable().optional()`
- **Update schemas:** All columns become `z.type().optional()` (nullable preserved)
- **Refinement callbacks** run before nullability is applied
- **Direct schema overrides** replace nullability entirely
