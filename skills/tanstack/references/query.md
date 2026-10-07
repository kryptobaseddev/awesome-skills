# TanStack Query

> Verified 2026-10-07 against `@tanstack/react-query@5.104.1` docs and published source (TanStack CLI 0.71.1). Re-check with `tanstack doc query <path>` when the installed major differs.

## Contents
- When to use / when not to
- Packages
- Mental model
- Core API
- Patterns
- Traps
- Migration notes
- Go deeper

## When to use / when not to

- Use it for **server state**: data owned by an API, cached on the client, refetched and invalidated over time. It also covers mutations, optimistic UI, pagination, infinite scroll and SSR hydration.
- Do not use it for local UI state (use `useState` or a store) or for form state (TanStack Form).
- With TanStack Router or Start, Query owns the cache and the router loader only *warms* it. See `router.md` → TanStack Query integration.
- In a Server Components app that is just starting, the docs suggest using the framework's own fetching first. Query is for cases where you need client cache behaviour (`guides/advanced-ssr`).

## Packages

| Package | Purpose |
|---|---|
| `@tanstack/react-query` | React adapter. Re-exports all of `@tanstack/query-core`. Peer: `react ^18 \|\| ^19` |
| `@tanstack/react-query-devtools` | `ReactQueryDevtools`, `ReactQueryDevtoolsPanel` |
| `@tanstack/eslint-plugin-query` | lint rules, including exhaustive-deps for query keys |
| `@tanstack/react-query-next-experimental` | `ReactQueryStreamedHydration` for the Next.js app router (experimental) |
| `@tanstack/react-router-ssr-query` | Router/Start SSR integration (see `router.md`) |

```bash
npm i @tanstack/react-query && npm i -D @tanstack/react-query-devtools @tanstack/eslint-plugin-query
```

Other adapters, all at 5.104.1 unless noted: `@tanstack/vue-query` (`useQuery`), `@tanstack/solid-query` (`useQuery(() => ({...}))`, which takes an accessor), `@tanstack/svelte-query` **6.x** (`createQuery(() => ({...}))`, Svelte 5), and `@tanstack/angular-query-experimental` (`injectQuery(() => ({...}))`).

## Mental model

- **QueryClient** owns a `QueryCache` and a `MutationCache`. Create one per app in the browser, and one **per request** on the server.
- A **query key** (an array) is the cache identity, and it acts as the dependency array for `queryFn`. Every variable the fn reads must be in the key.
- **staleTime** (default `0`) decides when cached data counts as stale. **gcTime** (default 5 min) decides how long *unused* data stays in memory. The two are independent.
- A stale query refetches in the background when a new observer mounts, the window refocuses or the network reconnects. A failed query retries 3 times with backoff (0 times on the server).
- `status` describes the data (`pending` | `error` | `success`). `fetchStatus` describes the network (`fetching` | `paused` | `idle`). `isLoading` = `isPending && isFetching`.
- **queryOptions()** is an identity function that carries types. It is the shareable unit for hooks, `queryClient.query`, `setQueryData` and router loaders.
- A mutation does not touch the cache by itself. You call `invalidateQueries` / `setQueryData` from its callbacks.
- `queryClient.query()` (added in **5.102**) is the single imperative read-or-fetch API. `fetchQuery`, `prefetchQuery` and `ensureQueryData` are deprecated in its favour.

## Core API

```tsx
import {
  QueryClient, QueryClientProvider, queryOptions, useQuery, useSuspenseQuery,
  useMutation, useQueryClient, keepPreviousData, skipToken, noop,
} from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, gcTime: 5 * 60_000 } },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Todos />
      <ReactQueryDevtools />
    </QueryClientProvider>
  )
}

// Query key factory built from queryOptions: one place for key + fn + options
export const todoQueries = {
  all: () => ['todos'] as const,
  list: (filter: string) =>
    queryOptions({
      queryKey: [...todoQueries.all(), 'list', filter],
      queryFn: () => fetchTodos(filter),
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: [...todoQueries.all(), 'detail', id],
      queryFn: () => fetchTodo(id),
      staleTime: 5_000,
    }),
}

function Todos() {
  const { data, isPending, isError, error, isFetching } = useQuery(todoQueries.list('open'))
  if (isPending) return <p>Loading…</p>
  if (isError) return <p>{error.message}</p> // error: Error by default in v5
  return <ul>{data.map((t) => <li key={t.id}>{t.title}</li>)}</ul>
}

function TodoTitle({ id }: { id: number }) {
  // data is never undefined; loading → <Suspense>, errors → error boundary
  const { data } = useSuspenseQuery({ ...todoQueries.detail(id), select: (t) => t.title })
  return <h1>{data}</h1>
}

function AddTodo() {
  const qc = useQueryClient()
  const add = useMutation({
    mutationFn: (title: string) => postTodo(title),
    // return the promise so the mutation stays pending until the refetch finishes
    onSettled: () => qc.invalidateQueries({ queryKey: todoQueries.all() }),
  })
  return <button disabled={add.isPending} onClick={() => add.mutate('New')}>Add</button>
}

// Imperative read-or-fetch (5.102+)
await queryClient.query(todoQueries.detail(1))                            // fetches when stale
await queryClient.query({ ...todoQueries.detail(1), staleTime: 'static' }) // cache hit wins (old ensureQueryData)
void queryClient.query(todoQueries.detail(2)).catch(noop)                 // fire and forget (old prefetchQuery)
queryClient.setQueryData(todoQueries.detail(1).queryKey, (old) => old && { ...old, done: true })
```

Other v5 exports you will use: `useQueries({ queries, combine })`, `useSuspenseQueries`, `useInfiniteQuery` / `useSuspenseInfiniteQuery` / `infiniteQueryOptions`, `mutationOptions`, `useMutationState`, `useIsFetching`, `useIsMutating`, `usePrefetchQuery`, `usePrefetchInfiniteQuery`, `HydrationBoundary`, `dehydrate`, `hydrate`, `defaultShouldDehydrateQuery`, `QueryErrorResetBoundary`, `useQueryErrorResetBoundary`, `environmentManager`, and `experimental_streamedQuery`.

## Patterns

**Dependent or conditional query (type-safe):**
```tsx
const { data } = useQuery({
  queryKey: ['todos', filter],
  queryFn: filter ? () => fetchTodos(filter) : skipToken, // refetch() does NOT work with skipToken
})
// use `enabled: !!filter` instead when you need a manual refetch()
```

**Paginated query that keeps the previous page on screen:**
```tsx
const { data, isPlaceholderData } = useQuery({
  queryKey: ['projects', page],
  queryFn: () => fetchProjects(page),
  placeholderData: keepPreviousData,
})
```

**Infinite query:**
```tsx
const q = useInfiniteQuery({
  queryKey: ['projects'],
  queryFn: ({ pageParam }) => fetchProjects(pageParam),
  initialPageParam: 0,                                   // required in v5
  getNextPageParam: (lastPage) => lastPage.nextCursor,   // return null or undefined to stop
  maxPages: 3,                                           // optional; needs getPreviousPageParam too
})
// q.data.pages, q.fetchNextPage(), q.hasNextPage, q.isFetchingNextPage
// guard: hasNextPage && !isFetching && fetchNextPage()
```

**Optimistic update through the cache (5.89+ callback signature):**
```tsx
useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo, context) => {
    await context.client.cancelQueries({ queryKey: ['todos'] })
    const previousTodos = context.client.getQueryData(['todos'])
    context.client.setQueryData(['todos'], (old: Todo[] = []) => [...old, newTodo])
    return { previousTodos }                 // becomes `onMutateResult`
  },
  onError: (err, newTodo, onMutateResult, context) =>
    context.client.setQueryData(['todos'], onMutateResult?.previousTodos),
  onSettled: (data, error, variables, onMutateResult, context) =>
    context.client.invalidateQueries({ queryKey: ['todos'] }),
})
```
If only one place on screen shows the change, the simpler option is to render `mutation.variables` while `isPending`. There is nothing to roll back. Use `useMutationState({ filters: { mutationKey, status: 'pending' }, select: (m) => m.state.variables })` to read it from another component.

**SSR with framework loaders (Remix, Next pages router, and similar):** create a `new QueryClient()` per request, `await queryClient.query(...)`, return `dehydrate(queryClient)`, then wrap the page in `<HydrationBoundary state={dehydratedState}>`. Set a default `staleTime > 0` so the client does not refetch straight away. For streaming pending queries, set `defaultOptions.dehydrate.shouldDehydrateQuery: (q) => defaultShouldDehydrateQuery(q) || q.state.status === 'pending'`. For a browser singleton, use `environmentManager.isServer()`.

**Global types through `Register`:**
```ts
declare module '@tanstack/react-query' {
  interface Register { defaultError: AxiosError } // also: queryMeta, mutationMeta, queryKey, mutationKey
}
```

## Traps

1. **Positional signatures.** `useQuery(['todos'], fn)`, `invalidateQueries(['todos'])` and `getQueryData(key, filters)` fail to compile in v5 because every hook and client method takes **one object**. Write `useQuery({ queryKey, queryFn })` and `invalidateQueries({ queryKey })`. The codemod is `remove-overloads` (`guides/migrating-to-v5`).
2. **`cacheTime`** is a type error in TypeScript and is silently ignored in JavaScript. Rename it to **`gcTime`**. It is not "how long data stays fresh"; `staleTime` is.
3. **`isLoading` changed meaning.** v4 `isLoading` is v5 **`isPending`** (`status: 'pending'`). v5 `isLoading` is the old `isInitialLoading` (`isPending && isFetching`). A disabled query sits in `isPending` forever, so a spinner keyed on `isPending` never stops. Use `isLoading` for spinners on lazy queries.
4. **`onSuccess` / `onError` / `onSettled` on `useQuery`** were removed in v5 (they remain on mutations). Derive state in render, use `useEffect` on `data`, or use `QueryCache({ onError })` for global toasts.
5. **`keepPreviousData: true`** was removed. Write `placeholderData: keepPreviousData` and read `isPlaceholderData` (not `isPreviousData`).
6. **Deprecated imperative methods (5.102+).** `fetchQuery`, `prefetchQuery`, `ensureQueryData`, `fetchInfiniteQuery`, `prefetchInfiniteQuery` and `ensureInfiniteQueryData` still work but are marked for removal in v6. Replacements:
   - `fetchQuery(o)` → `query(o)`
   - `prefetchQuery(o)` → `query(o).catch(noop)`
   - `ensureQueryData(o)` → `query({ ...o, staleTime: 'static' })`

   **Trap inside the trap:** plain `query(o)` uses `o.staleTime`, which defaults to `0`, so it **refetches** whenever data exists and is stale. Add `staleTime: 'static'` to get the old "use the cache if present" behaviour (`guides/migrating-to-v5#imperative-queryclient-methods`).
7. **`staleTime: 'static'` vs `Infinity`.** `invalidateQueries` *can* refetch an `Infinity` query but has **no effect** on a `'static'` one, and `'static'` also blocks `refetchOn*: 'always'`. Do not put `'static'` in a `queryOptions` that you later expect to invalidate. Put it only at the loader call site (`guides/important-defaults`).
8. **Mutation callback arity changed (around 5.89).** The signatures are now `onMutate(variables, context)` and `onError/onSuccess(…, variables, onMutateResult, context)`, plus `onSettled(data, error, variables, onMutateResult, context)`, where `context.client` is the QueryClient. Older code that reads the 3rd argument as "context" still works positionally but is misnamed. Code that expects only 3 arguments will not see `context.client` (`guides/mutations`).
9. **Infinite queries without `initialPageParam`** fail to type-check, and `queryFn: ({ pageParam = 0 })` defaults are no longer used. Manual `fetchNextPage({ pageParam })` was removed.
10. **`Hydrate` / `useHydrate`** no longer exist. Use `<HydrationBoundary state>`, which hydrates queries only (not mutations).
11. **`useErrorBoundary`** was renamed to **`throwOnError`**. `useSuspenseQuery` cannot be disabled (`enabled` / `placeholderData` are not options), and it only throws to the boundary when there is no cached data.
12. **A shared server QueryClient leaks data between users.** On the server, create the client per request (Router/Start: inside `getRouter()`). In the browser, do not create it in a component body without `useState` or a module singleton, or React throws it away when it suspends.
13. **`gcTime: 0` with SSR** causes hydration errors because data is collected before render. The docs suggest a minimum of `2 * 1000` (`guides/ssr`).
14. **`isServer`** is deprecated. Use `environmentManager.isServer()`.
15. **`setQueryDefaults` order.** Registrations now *merge*, so register from the most generic key to the most specific.
16. **Server Actions as `queryFn`** (Next.js) run serially and can leave queries stuck in pending. Use them for mutations only (`guides/advanced-ssr`).

## Migration notes

| v4 | v5 (5.104) |
|---|---|
| `useQuery(key, fn, opts)` | `useQuery({ queryKey, queryFn, ...opts })` |
| `cacheTime` | `gcTime` |
| `status: 'loading'`, `isLoading` | `status: 'pending'`, `isPending` |
| `isInitialLoading` | `isLoading` |
| `keepPreviousData: true`, `isPreviousData` | `placeholderData: keepPreviousData`, `isPlaceholderData` |
| `useErrorBoundary` | `throwOnError` |
| `suspense: true` on `useQuery` | `useSuspenseQuery` / `useSuspenseInfiniteQuery` / `useSuspenseQueries` |
| `onSuccess/onError/onSettled` on queries | removed |
| `refetchInterval: (data, query) =>` | `refetchInterval: (query) =>` (data at `query.state.data`) |
| `remove()` from `useQuery` | `queryClient.removeQueries({ queryKey })` |
| `isDataEqual` | `structuralSharing: (old, new) => …` |
| `Hydrate`, `useHydrate` | `HydrationBoundary` |
| `context` option / `contextSharing` | pass `queryClient` as the hook's 2nd argument |
| `refetchPage` | `maxPages` |
| `hashQueryKey` | `hashKey` |
| error type `unknown` | `Error` (override through `Register.defaultError`) |
| infinite `pageParam` default in fn | `initialPageParam` required |
| `fetchQuery` / `prefetchQuery` / `ensureQueryData` (v5 <5.102) | `queryClient.query` (+ `.catch(noop)` / `staleTime: 'static'`) |
| `fetchInfiniteQuery` / `prefetchInfiniteQuery` / `ensureInfiniteQueryData` | `queryClient.infiniteQuery` |
| `onMutate` return passed as `context` (3rd arg) | named `onMutateResult`; 4th arg `context` = `{ client, meta, mutationKey }` |
| `isServer` | `environmentManager.isServer()` |

Minimums: React 18, TypeScript 4.7 (Chrome 91, Safari 15).

## Go deeper

- `tanstack doc query framework/react/guides/migrating-to-v5`: every v4→v5 break and the codemod
- `tanstack doc query framework/react/guides/query-options`: the queryOptions helper and select
- `tanstack doc query framework/react/guides/important-defaults`: staleTime, gcTime, retry, `'static'`
- `tanstack doc query framework/react/guides/mutations`: callbacks, scopes, persisting mutations
- `tanstack doc query framework/react/guides/optimistic-updates`: the UI approach vs the cache approach
- `tanstack doc query framework/react/guides/query-invalidation`: prefix, exact and predicate matching
- `tanstack doc query framework/react/guides/infinite-queries`: cursors, maxPages, bi-directional lists
- `tanstack doc query framework/react/guides/disabling-queries`: `enabled`, `skipToken`, lazy queries
- `tanstack doc query framework/react/guides/suspense`: suspense hooks and error resets
- `tanstack doc query framework/react/guides/prefetching`: `query`, `usePrefetchQuery`, router integration
- `tanstack doc query framework/react/guides/ssr`: per-request client and HydrationBoundary
- `tanstack doc query framework/react/guides/advanced-ssr`: RSC, streaming pending queries
- `tanstack doc query framework/react/typescript`: Register, typing errors and meta
- `tanstack doc query framework/react/devtools`: devtools setup
