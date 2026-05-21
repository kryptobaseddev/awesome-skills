# Drizzle Seed Reference

Complete reference for `drizzle-seed` — database seeding for Drizzle ORM.

**Requirements:** `drizzle-orm@0.36.4+`
**Install:** `pnpm add drizzle-seed`

## Table of Contents

- [Basic Usage](#basic-usage)
- [Options](#options)
- [Reset](#reset)
- [Refinements](#refinements)
- [Generators](#generators)
- [Weighted Random](#weighted-random)
- [Versioning](#versioning)

## Basic Usage

```typescript
import { drizzle } from "drizzle-orm/node-sqlite";
import { seed } from "drizzle-seed";
import * as schema from "./schema";

const db = drizzle("sqlite.db");
await seed(db, schema); // 10 rows per table by default
```

## Options

```typescript
await seed(db, schema, {
  count: 1000,     // Rows per table (default: 10)
  seed: 12345,     // Deterministic data (different seed = different data)
  version: "2",    // Pin generator version for stability
});
```

## Reset

```typescript
import { reset } from "drizzle-seed";
await reset(db, schema); // Truncates all tables with CASCADE
```

## Refinements

Customize seed generation per-table:

```typescript
await seed(db, schema).refine((f) => ({
  users: {
    columns: {
      name: f.fullName(),
      email: f.email(),
      age: f.int({ minValue: 18, maxValue: 80 }),
    },
    count: 50, // Override global count for this table
    with: {
      posts: 10, // Create 10 posts per user
    },
  },
  posts: {
    columns: {
      title: f.valuesFromArray({
        values: ["Title A", "Title B", "Title C"],
      }),
    },
  },
}));
```

## Generators

### Numbers
| Generator | Parameters | Description |
|-----------|-----------|-------------|
| `f.int()` | `{ minValue?, maxValue?, isUnique? }` | Random integer |
| `f.number()` | `{ minValue?, maxValue?, precision?, isUnique? }` | Random float |
| `f.intPrimaryKey()` | — | Auto-incrementing integer |

### Text
| Generator | Parameters | Description |
|-----------|-----------|-------------|
| `f.string()` | `{ isUnique? }` | Random string |
| `f.uuid()` | — | UUID v4 |
| `f.loremIpsum()` | `{ sentencesCount? }` | Lorem ipsum text |

### Personal Data
| Generator | Parameters | Description |
|-----------|-----------|-------------|
| `f.firstName()` | `{ isUnique? }` | First name |
| `f.lastName()` | `{ isUnique? }` | Last name |
| `f.fullName()` | `{ isUnique? }` | Full name |
| `f.email()` | — | Email address |
| `f.phoneNumber()` | `{ template?: "###-###-####" }` | Phone number |

### Location
| Generator | Parameters | Description |
|-----------|-----------|-------------|
| `f.country()` | `{ isUnique? }` | Country name |
| `f.city()` | `{ isUnique? }` | City name |
| `f.streetAddress()` | `{ isUnique? }` | Street address |
| `f.postcode()` | `{ isUnique? }` | Postal code |

### Dates
| Generator | Parameters | Description |
|-----------|-----------|-------------|
| `f.date()` | `{ minDate?, maxDate? }` | Random date |
| `f.timestamp()` | — | Timestamp |
| `f.datetime()` | — | Datetime |

### Utilities
| Generator | Parameters | Description |
|-----------|-----------|-------------|
| `f.default()` | `{ defaultValue }` | Static value |
| `f.valuesFromArray()` | `{ values, isUnique? }` | Pick from array |
| `f.boolean()` | — | Random boolean |
| `f.json()` | — | Random JSON |

All generators accept optional `arraySize` parameter for generating arrays.

## Weighted Random

### Weighted column values
```typescript
columns: {
  price: f.weightedRandom([
    { weight: 0.3, value: f.int({ minValue: 10, maxValue: 100 }) },
    { weight: 0.7, value: f.number({ minValue: 100, maxValue: 300, precision: 100 }) },
  ]),
}
```

### Weighted relationship counts
```typescript
with: {
  details: [
    { weight: 0.6, count: [1, 2, 3] },      // 60%: 1-3 details
    { weight: 0.3, count: [5, 6, 7] },      // 30%: 5-7 details
    { weight: 0.1, count: [8, 9, 10] },     // 10%: 8-10 details
  ],
}
```

## Versioning

Pin seed output to specific generator versions:

```typescript
await seed(db, schema, { version: "2" });
```

| Version | Since | Changes |
|---------|-------|---------|
| v1 | 0.1.1 | Initial release |
| v2 | 0.2.1 | Fixed `string()`, `interval({ isUnique: true })` |

**Why:** Ensures consistent test data across drizzle-seed updates. Different seed versions produce different data even with the same seed number.

## Testing Workflow

```typescript
import { seed, reset } from "drizzle-seed";

beforeEach(async () => {
  await reset(db, schema);
  await seed(db, schema, { seed: 12345, count: 50 });
});

test("user query", async () => {
  // Deterministic seeded data available
});
```
