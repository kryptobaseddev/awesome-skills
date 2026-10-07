# Composing TanStack libraries

> Verified 2026-10-07. Every pairing below names which library owns which state, because almost every composition bug is two
> libraries both believing they own the same thing. Full code lives in the per-library references named in each row.

## Ownership rules (read these first)

| State | Owner | Not |
|---|---|---|
| Data that lives on a server (lists, records, search results) | **Query** (or **DB** when you need live joins/optimistic multi-collection writes) | Store, React state, Router loader return values held forever |
| What the URL should reproduce: page, sort, filters, tab, selected id | **Router** search params (`validateSearch`) | Table internal state, Store |
| Draft values the user is editing, validation, submit status | **Form** | Query cache, Store |
| Client-only shared UI state (sidebar, theme, cart before checkout) | **Store** (atoms/`createStore`) | Query |
| Table view state (sorting, selection, sizing, pinning) | **Table** (its own Store atoms) — lift a slice out only when another owner must control it | duplicating it in both `state` and `initialState` |
| Which rows/columns are mounted | **Virtual** | Table pagination (pagination and virtualization are alternatives for the same rows) |
| When a function runs (debounce, throttle, rate limit, queue, batch) | **Pacer** | `setTimeout` inside effects |
| Keyboard bindings | **Hotkeys** | ad-hoc `keydown` listeners |
| Server boundary (secrets, DB access, auth checks) | **Start** server functions / server routes / middleware | Router loaders (they also run in the browser) |

## Pairings

| Pairing | Wiring | Where the code is |
|---|---|---|
| **Start ⊃ Router** | Start *is* Router plus a server: same `createFileRoute`, loaders, search params. `src/router.tsx` exports `getRouter()` that builds a fresh router per request. | `start.md` → Files and config |
| **Router + Query** | `setupRouterSsrQueryIntegration({ router, queryClient })` from `@tanstack/react-router-ssr-query`; pass `queryClient` in router `context`; loaders call `context.queryClient.query({...opts, staleTime: 'static'})` (5.102+; older code uses the now-deprecated `ensureQueryData`); components read with `useSuspenseQuery(opts)`; set `defaultPreloadStaleTime: 0` so Query decides freshness. Search params flow to loaders only through `loaderDeps`. | `router.md` → Patterns; `query.md` → SSR |
| **Start + Query mutations** | Mutation calls a server function; on success `queryClient.invalidateQueries({ queryKey })` and, if loaders hold data, `router.invalidate()`. | `start.md` pattern 1 |
| **Table + Query** (server-side table) | Register only the *features* (no sorted/filtered/paginated row models); `manualPagination/manualSorting/manualFiltering: true`; put every server-owned slice in the `queryKey`; `placeholderData: keepPreviousData`; `rowCount` from the response; `getRowId` from the record; reset `pageIndex` yourself when sort/filter changes. | `table.md` pattern 1 |
| **Table + Router** | Make sort/filter/page URL state: read them from `Route.useSearch()`, write with `navigate({ search: (prev) => ({ ...prev, page }) })`, and pass them into the table as controlled `state`. Then Table + Query reads the same values. | `router.md` search params + `table.md` pattern 1 |
| **Table + Virtual** | Table produces `table.getRowModel().rows`; Virtual decides which indexes render: `useVirtualizer({ count: rows.length, getScrollElement, estimateSize, overscan })`. Use `display: grid` / absolute rows with `translateY(virtualRow.start)`; key rows by `virtualRow.key`; measure with `measureElement` + `data-index` for variable heights. Do not also paginate the same rows. | `table.md` pattern 5; `virtual.md` |
| **Virtual + Query infinite** | `useInfiniteQuery` pages → flatten → `count = hasNextPage ? rows.length + 1 : rows.length`; when the last virtual item is the loader row, `fetchNextPage()` (guard on `isFetchingNextPage`). | `virtual.md` pattern 4 |
| **Table + Form** (editable grid) | Form owns the draft rows (`form.Field name={`rows[${row.index}].price`}` with array-field naming); Table owns layout/sort/selection over `form.state.values.rows` or the original data. Commit via one submit (or per-row submit) that calls a mutation. Keep `getRowId` stable so sorting does not move edits to another record. | `form.md` → Arrays; `table.md` |
| **Table + Pacer** | Debounce the *value* that drives filtering, not the table: `const [debounced] = useDebouncedValue(filterInput, { wait: 300 })`, then pass `debounced` into table state (client-side) or the `queryKey` (server-side). | `pacer.md` pattern 1 |
| **Table + Hotkeys** | `useHotkey('Mod+A', () => table.toggleAllRowsSelected(true))`, arrow-key row focus, `Escape` to clear selection. Scope with `target` (a ref with `tabIndex`) so shortcuts do not fire elsewhere; leave `ignoreInputs` at its default so typing in filter inputs is not hijacked. | `hotkeys.md` |
| **Table + Store** | Table v9 state *is* Store atoms (`table.atoms.<slice>`, `table.store`). To share a slice (e.g. selection) with the rest of the app, create the atom yourself and pass it via the table's `atoms` option instead of syncing with effects. | `table.md` → state; `store.md` |
| **Form + Start** | Validate on the client with Standard Schema; re-validate in the server function (`createServerFn().validator(schema)`); never trust client validation. | `form.md` → TanStack Start server validation |
| **DB + Query** | A Query Collection uses a `QueryClient` underneath; DB adds live queries, joins and optimistic transactions on top. Each `queryFn` result replaces the collection contents. | `db.md` |
| **AI + Start** | `chat()` runs in a server route (`createFileRoute(...)({ server: { handlers: { POST } } })`) and returns `toServerSentEventsResponse(...)`; the client uses `useChat` with an SSE connection. The AI core is framework-agnostic — it works the same behind Hono, Express or Next.js. | `ai.md` |
| **AI + Markdown/Highlight** | Stream assistant text into TanStack Markdown's document model and highlight code blocks with Highlight. Each library also works alone. | `markdown-highlight.md` |
| **Devtools + everything** | One `<TanStackDevtools plugins={[...]}>` panel hosts Query, Router, Form, Pacer, Hotkeys, Table, AI panels; most need a `key`/name on the instance to show up. | `devtools.md` |

## Stack recipes

- **Full-stack CRUD app**: `tanstack create app --add-ons tanstack-query,form,table,drizzle --add-on-config '{"drizzle":{"database":"postgresql"}}' --deployment <host> -y`,
  then Router search params for list state → Table + Query (manual) → Form + server function → invalidate.
- **SPA without a server**: `tanstack create app --router-only -y`, then add `@tanstack/react-query` by hand and pass `queryClient` through router context.
- **Large dataset viewer**: Table (client row models) + Virtual rows; Pacer-debounced global filter; Hotkeys for navigation. No pagination.
- **Local-first / realtime**: DB collections (Query, Electric or PowerSync) + live queries; Query alone if you only need fetch-and-cache.
- **AI assistant**: Start server route + AI `chat()` + `useChat`; Markdown + Highlight to render the stream; Virtual end-anchored list for long threads.
