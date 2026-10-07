# TanStack DB

> Verified 2026-10-07 against `@tanstack/db@0.12.1`, `@tanstack/react-db@0.5.5`, `@tanstack/query-db-collection@1.4.0` docs and package source (TanStack CLI 0.71.1). Pre-1.0: minors break, and the docs moved fast in Aug–Oct 2026. Re-check with `tanstack doc db <path>` when the installed minor differs.

## Contents
- When to use / when not to
- Packages
- Mental model
- Core API (DbClient descriptors, classic createCollection)
- Patterns (queries, mutations, actions, transactions, sync engines, SSR)
- Traps
- Migration notes
- Go deeper

## When to use / when not to
- Use when the client needs to **query across server data locally** (joins, filters, aggregates, sorted views) with sub-ms incremental updates, **optimistic writes with automatic rollback**, or data fed by a **sync engine** (Electric, PowerSync, RxDB, TrailBase).
- It sits on top of TanStack Query for REST: Query fetches, DB normalizes into collections and queries them. You can adopt one collection at a time.
- Don't use for: plain fetch-and-render screens (Query alone), form buffers (Form), small client UI state (Store / `useState`), or anything needing a stable 1.0 API contract today. Status: **beta, 0.x** (`latest` = 0.12.1, released 2026-10-06; 1.0 removals are already announced as dev warnings).

## Packages
| Need | Package |
|---|---|
| React (re-exports all of `@tanstack/db`) | `@tanstack/react-db` (react >=18) |
| Vue / Solid / Svelte / Angular | `@tanstack/vue-db`, `solid-db`, `svelte-db`, `angular-db` (Angular: import operators from `@tanstack/db`) |
| Core / vanilla | `@tanstack/db` |
| REST via TanStack Query | `@tanstack/query-db-collection` + `@tanstack/query-core` (peer `^5`) |
| ElectricSQL (Postgres shapes) | `@tanstack/electric-db-collection` |
| PowerSync / RxDB / TrailBase | `@tanstack/powersync-db-collection`, `rxdb-db-collection`, `trailbase-db-collection` |
| IndexedDB | `@tanstack/indexeddb-db-collection` |
| localStorage / in-memory | built in: `localStorageCollectionOptions`, `localOnlyCollectionOptions` |
| SQLite persistence (browser OPFS) | `@tanstack/browser-db-sqlite-persistence` + `@journeyapps/wa-sqlite` |
| Offline outbox | `@tanstack/offline-transactions` |
| Start Suspense streaming | `@tanstack/react-router-with-db` (0.1.0) |

```sh
npm i @tanstack/react-db @tanstack/query-db-collection @tanstack/query-core
```
Exactly one copy of `@tanstack/db` must be installed (check `pnpm ls @tanstack/db`).

## Mental model
- **Collection** = typed, keyed set of rows (`getKey`) filled by a sync adapter (`queryCollectionOptions`, `electricCollectionOptions`, …). It keeps **synced state** and an **optimistic overlay** separately.
- **Live query** = query builder (`from/where/join/select/groupBy/having/orderBy/limit/offset/distinct/findOne`) compiled to differential dataflow; the result is itself a collection, updated incrementally.
- **Mutations** (`insert/update/delete`) apply optimistically now, then call the collection's `onInsert/onUpdate/onDelete` (or an ambient transaction's `mutationFn`). Throw → rollback. Resolve → optimistic state drops and synced state must already contain the server truth (refetch / txid / direct write).
- **Transactions** group mutations: `createOptimisticAction` (intent action), `createTransaction` (manual commit/rollback), `createPacedMutations` (debounce/throttle/queue).
- **DbClient** (since db 0.8) owns materialized collections for one scope (browser app, SSR request, test). `collectionOptions(id, factory)` is a stable **descriptor**; `dbClient.collection(desc)` materializes it once per client. `DbProvider` lets React hooks resolve descriptors used in `q.from(...)`.
- **Sync modes**: `eager` (default, load all; <10k rows), `on-demand` (query predicates pushed to `queryFn` via `ctx.meta.loadSubsetOptions`), `progressive`.
- Query Collections treat each `queryFn` result as the **complete** state of that collection.

## Core API

### SSR-safe / current shape (descriptors + DbClient)
```tsx
import { QueryClient } from '@tanstack/query-core'
import { queryCollectionOptions } from '@tanstack/query-db-collection'
import { DbClient, DbProvider, collectionOptions, eq, useDbClient, useLiveQuery } from '@tanstack/react-db'

type Todo = { id: string; text: string; completed: boolean; createdAt: string }

export const todoCollection = collectionOptions('todos', (client) =>
  queryCollectionOptions<Todo>({
    id: 'todos',
    queryKey: ['todos'],
    queryClient: client.requireDependency<QueryClient>('queryClient'),
    queryFn: async () => (await fetch('/api/todos')).json(),
    getKey: (t) => t.id,
    onUpdate: async ({ transaction }) => {
      await Promise.all(transaction.mutations.map((m) =>
        fetch(`/api/todos/${m.original.id}`, { method: 'PATCH', body: JSON.stringify(m.changes) })))
      // pre-1.0: Query Collection auto-refetches after this resolves
    },
  }),
)

const queryClient = new QueryClient()
const dbClient = new DbClient({ queryClient })      // dependencies are looked up by key
const useTodos = () => useDbClient().collection(todoCollection)

function Todos() {
  const todos = useTodos()
  const { data = [], isLoading } = useLiveQuery({
    query: (q) => q.from({ todo: todoCollection })           // descriptor resolved via DbProvider
      .where(({ todo }) => eq(todo.completed, false))
      .orderBy(({ todo }) => todo.createdAt, 'desc'),
  })
  if (isLoading) return null
  return data.map((t) => (
    <li key={t.id} onClick={() => todos.update(t.id, (d) => { d.completed = !d.completed })}>{t.text}</li>
  ))
}
export const App = () => <DbProvider client={dbClient}><Todos /></DbProvider>
```

### Classic shape (still supported, client-only apps)
```ts
import { createCollection } from '@tanstack/react-db'
export const todos = createCollection(queryCollectionOptions({
  queryKey: ['todos'], queryFn: fetchTodos, queryClient, getKey: (t: Todo) => t.id,
}))
// useLiveQuery({ query: (q) => q.from({ todo: todos }) }) ; todos.insert(...)
```
Module singletons leak across SSR requests; use descriptors for SSR, tests, multi-tenant.

`useLiveQuery` returns `{ data, state, collection, status, isLoading, isReady, isError, isIdle, isCleanedUp }`; also accepts a pre-created collection: `useLiveQuery(liveCollection)`. Other React hooks: `useLiveSuspenseQuery` (data always defined), `useLiveInfiniteQuery(queryFn, { pageSize })`, `usePacedMutations`, `useLiveQueryEffect`, `HydrationBoundary`, `useOptionalDbClient`.

## Patterns

### Query builder
```ts
import { and, avg, coalesce, count, eq, gt, ilike, inArray, not, sum, upper } from '@tanstack/react-db'

q.from({ todo: todoCollection })
  .join({ list: listCollection }, ({ todo, list }) => eq(list.id, todo.listId), 'inner') // or .leftJoin/.innerJoin/.rightJoin/.fullJoin
  .where(({ todo, list }) => and(eq(list.active, true), not(todo.completed), ilike(todo.text, '%milk%')))
  .select(({ todo, list }) => ({ id: todo.id, text: upper(todo.text), listName: coalesce(list.name, 'Inbox') }))

q.from({ order: orders })
  .groupBy(({ order }) => order.customerId)
  .select(({ order }) => ({ customerId: order.customerId, total: sum(order.amount), n: count(order.id) }))
  .having(({ $selected }) => gt($selected.total, 1000))
  .orderBy(({ $selected }) => $selected.total, 'desc')
  .limit(10)

q.from({ user: users }).where(({ user }) => eq(user.id, id)).findOne()   // single row | undefined
```
Outside React: `createLiveQueryCollection((q) => …)` (module scope, reuse), `queryOnce((q) => …)` for one-shot snapshots (loaders, scripts). Hierarchical results: put a subquery in `select` (child = live collection) or wrap with `toArray(...)` for plain arrays.

### Optimistic CRUD
```ts
const c = useDbClient().collection(todoCollection)
const tx = c.insert({ id: crypto.randomUUID(), text: 'x', completed: false, createdAt: new Date().toISOString() })
c.update(id, (draft) => { draft.text = 'y' })      // draft proxy, never pass an object
c.update(id, { metadata: { reason: 'edit' } }, (d) => { d.text = 'z' })
c.delete([id1, id2])
c.insert(row, { optimistic: false })                  // wait for server before showing
await tx.when('settled')                              // rejects on rollback
```
Handlers receive `{ transaction, collection }`; each `transaction.mutations[i]` has `type`, `key`, `original`, `modified`, `changes`, `metadata`.

### Intent action across collections
```ts
import { createOptimisticAction } from '@tanstack/react-db'
const likePost = createOptimisticAction<string>({
  onMutate: (postId) => { posts.update(postId, (d) => { d.likes += 1 }) },   // MUST be sync
  mutationFn: async (postId) => { await api.like(postId); await posts.utils.refetch() },
})
likePost(postId)
```

### Manual / draft transaction
```ts
import { createTransaction } from '@tanstack/react-db'
const tx = createTransaction({ autoCommit: false, mutationFn: async ({ transaction }) => api.batch(transaction.mutations) })
tx.mutate(() => { todos.update(a, (d) => { d.status = 'reviewed' }) })     // synchronous scope only
await tx.commit()   // or tx.rollback()
```
Collection `onInsert/onUpdate/onDelete` are NOT called for mutations inside a manual transaction. Local-only collections in a manual tx need `localData.utils.acceptMutations(transaction)` inside `mutationFn`.

### Sync engine (Electric)
```ts
import { electricCollectionOptions } from '@tanstack/electric-db-collection'
export const todos = collectionOptions(electricCollectionOptions({
  id: 'todos', schema: todoSchema, getKey: (t) => t.id,
  shapeOptions: { url: '/api/todos', params: { table: 'todos' } },     // your proxy to Electric
  onInsert: async ({ transaction, collection }) => {
    const { txid } = await api.todos.create(transaction.mutations[0].modified)
    await collection.utils.awaitTxId(txid)          // backend: SELECT pg_current_xact_id()::xid::text
  },
}))
```
No txid available → `collection.utils.awaitMatch(...)`.

### Local state collections
```ts
import { createCollection, localOnlyCollectionOptions, localStorageCollectionOptions } from '@tanstack/react-db'
const prefs = createCollection(localStorageCollectionOptions({ id: 'prefs', storageKey: 'app-prefs', getKey: (p) => p.id }))
const ui = createCollection(localOnlyCollectionOptions({ id: 'ui', getKey: (r) => r.id, initialData: [] }))
prefs.insert({ id: 'theme', mode: 'dark' })     // no handlers needed; persisted + cross-tab
```

### SSR (Start / Next)
Server: `const db = new DbClient({ queryClient }); await db.collection(desc).preload()` (or `await db.preloadLiveQuery({ query })` to ship only the result) then `db.dehydrate()` through the loader. Browser: one `DbClient` in `useState`, `<DbProvider client={db}><HydrationBoundary state={state}>…`. Start streaming: `routerWithDbClient(router, dbClient)` from `@tanstack/react-router-with-db`. Call `await dbClient.cleanup()` when a scope ends.

### Live updates without refetch (WebSocket/SSE into a Query Collection)
`collection.utils.writeInsert/writeUpdate/writeDelete/writeUpsert/writeBatch(() => …)` write straight to synced state (no optimistic layer). In a handler, await the write, then `return { refetch: false }`.

## Traps
1. **`todo.completed === false` in `.where`** → evaluates to a boolean immediately; throws `InvalidWhereExpressionError`. Use `eq`, `gt`, `and`, `not`, … Same for `||`/ternaries in `.select` → `coalesce`/`caseWhen`. (`guides/live-queries`)
2. **`useLiveQuery((q) => …, [deps])`** → the dependency-array form is deprecated (dev warning) and removed in 1.0. Use `useLiveQuery({ query })`; identity is derived from the query IR. Opaque `.fn.where/.fn.select` needs an explicit `queryKey` (1.0 will throw without it). (`framework/react/overview`)
3. **`const todos = useLiveQuery(...)` then `todos.map`** → it returns an object; destructure `{ data }`. Disabled queries return `data: undefined` → default `{ data = [] }`.
4. **Calling `refetch()` inside a Query Collection handler** → double fetch: pre-1.0 the collection auto-refetches after `onInsert/onUpdate/onDelete`. Either rely on it, or refetch/direct-write yourself and `return { refetch: false }`. In 1.0 auto-refetch is removed, so new code that refetches explicitly and returns `{ refetch: false }` is forward-compatible. (`collections/query-collection#controlling-refetch-behavior`)
5. **Handler resolves before the server truth is in synced state** → optimistic row drops and the old value flickers back. Await refetch / `awaitTxId` / `writeUpsert` before returning. (`guides/mutations`)
6. **`queryFn` returning `[]` on error or a partial page** → full-state sync deletes every row not returned. Throw on error; for subsets use `syncMode: 'on-demand'` or separate collections. (`collections/query-collection#full-state-sync`)
7. **One collection per filter/page** → don't; one business-scoped collection + on-demand `loadSubsetOptions`. Scope values (tenant, project) belong in the descriptor id AND `queryKey`. (`collections/query-collection`)
8. **`collectionOptions({...})` without `id`, or `collectionOptions('x')` without factory** → throws. Two descriptors with the same id resolve to the first one materialized.
9. **Module-level `createCollection` + SSR** → shared across requests, `queryClient` captured globally. Use descriptors + per-request `DbClient` + `client.requireDependency('queryClient')`. (`guides/ssr`)
10. **`collection.update(id, { ...row, x })`** → wrong signature; pass a draft callback. Changing the key in a draft throws `KeyUpdateNotAllowedError`; duplicate insert throws `DuplicateKeyError`.
11. **Mutating with no handler and no ambient transaction** → `MissingInsertHandlerError` (Update/Delete variants).
12. **`async onMutate`** in `createOptimisticAction` → `OnMutateMustBeSynchronousError`. Generate ids with `crypto.randomUUID()` / `safeRandomUUID()`, not awaited calls. Server-assigned ids need a view-key mapping or non-optimistic insert (`guides/mutations#handling-temporary-ids`).
13. **Collection mutations after `await` inside `tx.mutate(...)`** → they don't join the transaction; the ambient scope is synchronous.
14. **Preloading / `loadSubset` inside a `mutationFn`** → can deadlock: sync commits queue behind the mutation that waits on them.
15. **`.limit()`/`.offset()` without `.orderBy()`**, `.distinct()` without `.select()`, `.having()` without `.groupBy()`, non-equality or `or()` join conditions, `q.from(collection)` without an alias object → each throws a dedicated error. Result order is undefined without `orderBy`. (`guides/live-queries`)
16. **`eq(row.x, null)`** → SQL three-valued logic, matches nothing; use `isNull(x)` / `isUndefined(x)`. `NaN` equals itself and sorts last.
17. **Filtering `data` with JS `.filter()`** → loses incremental maintenance; push it into `.where`.
18. **`useLiveSuspenseQuery` without an ErrorBoundary** → errors throw during render.
19. **`InvalidSourceError … is not a Collection` / `DuplicateDbInstanceError`** → two copies of `@tanstack/db`; dedupe via overrides or a Vite alias.
20. **`gcTime: 0` on live query collections** → *disables* GC (opposite of Query). Use a small positive value.
21. **`tx.isPersisted.promise`** → deprecated alias; use `tx.when('settled')`.
22. **`getNextPageParam` on `useLiveInfiniteQuery`** → now rejected; it widens a local ordered query, it is not Query's `useInfiniteQuery`. Server paging = on-demand Query Collection.
23. **Virtual props** (`$synced`, `$origin`, `$key`, `$collectionId`) are on every live row; `$synced` only means "no pending local write", not server-confirmed. Never write them back.

## Migration notes
| Older (≤0.7 / early React adapter) | Current (db 0.12, react-db 0.5) |
|---|---|
| `useLiveQuery((q) => …, deps)` | `useLiveQuery({ query })`, `queryKey` only for opaque `.fn.*` |
| module `createCollection(...)` singleton | `collectionOptions(id, factory)` + `new DbClient()` + `dbClient.collection(desc)` (createCollection still works) |
| import collection in components to mutate | `useDbClient().collection(desc)` under `<DbProvider client>` |
| `queryClient` passed into options | `client.requireDependency<QueryClient>('queryClient')` with `new DbClient({ queryClient })` (direct still supported as fallback) |
| no SSR story | `preload()` / `preloadLiveQuery` → `dehydrate()` → `HydrationBoundary` / `hydrate()` |
| `tx.isPersisted.promise` | `tx.when('settled')` |
| implicit Query Collection refetch after handlers | still on (pre-1.0); return `{ refetch: false }` to opt out; removed in 1.0 |
| `useLiveInfiniteQuery(..., { getNextPageParam })` | option rejected; use `pageSize` + on-demand server paging |

## Go deeper
- `tanstack doc db overview` - model, sync modes, examples
- `tanstack doc db quick-start` - DbClient + Query Collection setup
- `tanstack doc db installation` - every adapter package
- `tanstack doc db framework/react/overview` - hooks, query identity, queryKey
- `tanstack doc db guides/live-queries` - full builder + operator reference
- `tanstack doc db guides/mutations` - handlers, actions, transactions, paced, temp ids
- `tanstack doc db guides/ssr` - DbClient, dehydrate/hydrate, migration guide
- `tanstack doc db collections/query-collection` - refetch rules, direct writes, on-demand
- `tanstack doc db collections/electric-collection` - txid / awaitMatch
- `tanstack doc db collections/local-storage-collection` - persisted local state
- `tanstack doc db collections/local-only-collection` - in-memory + acceptMutations
- `tanstack doc db guides/schemas` - Standard Schema input/output types
- `tanstack doc db guides/error-handling` - error classes, rollback
- `tanstack doc db guides/offline-transactions` - outbox and retry
- `tanstack doc db guides/sqlite-persistence` - OPFS/SQLite persistence
- `tanstack doc db framework/react/reference/functions/useLiveQuery` - hook typings
