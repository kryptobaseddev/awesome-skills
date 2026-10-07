# TanStack Router

> Verified 2026-10-07 against `@tanstack/react-router@1.170.41` docs and published source (`@tanstack/router-plugin@1.168.42`, `@tanstack/react-router-ssr-query@1.167.3`, TanStack CLI 0.71.1). Re-check with `tanstack doc router <path>` when the installed major differs.

## Contents
- When to use / when not to
- Packages
- Mental model
- Core API
- Patterns (search params, auth guard, TanStack Query, code splitting)
- Traps
- Migration notes
- Go deeper

## When to use / when not to

- Use it for a fully type-safe client router in a React or Solid SPA. It gives typed paths, params, search params and loader data, plus built-in SWR loader caching and preloading.
- Use **TanStack Start** instead when you need server functions, a full-document SSR server or deployment adapters. Start is Router plus a server; every API below still applies inside Start.
- **Router without Start:** scaffold with `npx @tanstack/cli create --router-only` (add `--framework solid` for Solid), or install it manually (below). Router-only SSR exists (`@tanstack/react-router/ssr/server` and `/ssr/client`), but the docs call it experimental. Prefer Start for SSR.
- It is not React Router or Next.js. Do not write `react-router-dom` imports, `src/pages/`, `app/layout.tsx`, `getServerSideProps` or Remix `loader`/`action` exports (`guide/ssr`).

## Packages

| Package | Purpose |
|---|---|
| `@tanstack/react-router` | runtime and hooks. Peer: `react`/`react-dom` >=18 |
| `@tanstack/router-plugin` (dev) | file-based route generation plus auto code-splitting. `@tanstack/router-plugin/vite` (also `/rspack`, `/webpack`, `/esbuild`) |
| `@tanstack/router-cli` (dev) | `tsr generate` / `tsr watch`. Only for setups with no supported bundler; has no code-splitting |
| `@tanstack/react-router-devtools` | `TanStackRouterDevtools` |
| `@tanstack/zod-adapter` | `zodValidator`, `fallback`. Needed for **Zod v3 only** |
| `@tanstack/react-router-ssr-query` | Query SSR integration. Peers: `@tanstack/react-query >=5.102`, `@tanstack/react-router >=1.170.33` |

```bash
npm i @tanstack/react-router @tanstack/react-router-devtools && npm i -D @tanstack/router-plugin
```

The Solid packages follow the same pattern: `@tanstack/solid-router`, `@tanstack/solid-router-devtools`, `@tanstack/solid-router-ssr-query`. The plugin takes `target: 'solid'`.

## Mental model

- The **route tree** is the source of truth for types. File-based routing generates `src/routeTree.gen.ts` from `src/routes/`. Never edit that file; lint, format and VSCode should ignore it.
- `declare module '@tanstack/react-router' { interface Register { router: typeof router } }` is what makes *bare* `Link`, `useNavigate` and `useSearch` imports type-safe. Without it, everything falls back to loose `string`.
- The loading lifecycle has three phases:
  1. `params.parse` → `validateSearch` (top-down matching)
  2. `beforeLoad` (**serial**, parent first; a throw stops all children)
  3. `loader` + component preload (**parallel**)
- **Context** is hierarchical dependency injection. Router `context` comes in through `createRootRouteWithContext<T>()()`, each `beforeLoad` return merges into it for children, and loaders read `context`.
- Loaders have a built-in SWR cache keyed on pathname + `loaderDeps`. `staleTime` defaults to 0 (revalidates in the background), preloads stay fresh for 30s, and `gcTime` is 5 min.
- Search params are JSON-parsed, validated per route, merged parent→child, and treated as typed state.
- With TanStack Query, **Query owns the cache**. The loader only warms it (`queryClient.query`) and the component reads it (`useSuspenseQuery`).

## Core API

```ts
// vite.config.ts: the router plugin MUST come before the React plugin
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { tanstackRouter } from '@tanstack/router-plugin/vite'

export default defineConfig({
  plugins: [tanstackRouter({ target: 'react', autoCodeSplitting: true }), react()],
})
```

```tsx
// src/routes/__root.tsx
import { createRootRouteWithContext, Link, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import type { QueryClient } from '@tanstack/react-query'

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: () => (
    <>
      <Link to="/" activeProps={{ className: 'font-bold' }}>Home</Link>
      <Outlet />
      <TanStackRouterDevtools />
    </>
  ),
  notFoundComponent: () => <p>Not found</p>,
})
```

```tsx
// src/routes/posts.$postId.tsx  →  /posts/$postId
import { createFileRoute, notFound } from '@tanstack/react-router'

export const Route = createFileRoute('/posts/$postId')({
  loader: async ({ params }) => {
    const post = await fetchPost(params.postId)
    if (!post) throw notFound()
    return { post }
  },
  pendingComponent: () => <p>Loading…</p>,   // shown after pendingMs (1000) for at least pendingMinMs (500)
  errorComponent: ({ error, reset }) => (
    <p>{error instanceof Error ? error.message : String(error)}</p> // error is `unknown`
  ),
  notFoundComponent: () => <p>No such post</p>,
  component: PostPage,
})

function PostPage() {
  const { post } = Route.useLoaderData()
  const { postId } = Route.useParams()
  return <h1>{post.title}</h1>
}
```

```tsx
// src/main.tsx
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { routeTree } from './routeTree.gen'

const queryClient = new QueryClient()
const router = createRouter({
  routeTree,
  context: { queryClient },          // required, because the root declares it
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,        // let Query decide freshness
  scrollRestoration: true,
})

declare module '@tanstack/react-router' {
  interface Register { router: typeof router }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
  </QueryClientProvider>,
)
```

**File naming:**

| Name | Meaning |
|---|---|
| `__root.tsx` | root route |
| `a.b.tsx` or `a/b.tsx` | nested |
| `$id` | path param |
| `_layout` | pathless layout |
| `posts_` | un-nest from parent |
| `-components/` | ignored by the router |
| `(group)/` | adds no URL segment |
| `index.tsx` | exact-parent match |
| `route.tsx` | the directory's own route |
| `script[.]js.tsx` | escaped segment |

**Code-based routing:** build routes with `createRootRoute`, then `createRoute({ getParentRoute: () => rootRoute, path: '/about', component })`, then `rootRoute.addChildren([...])`.

**Navigation:**
- `<Link to="/posts/$postId" params={{ postId }} search={(prev) => ({ ...prev, page: 2 })}>`
- `useNavigate({ from: Route.fullPath })`, then `navigate({ search: (p) => ({ page: p.page + 1 }) })`
- `<Navigate>` and `router.navigate()`
- `linkOptions({...})` for reusable options in `Link`, `navigate` and `redirect`
- Relative targets `"."` and `".."`
- Outside a route component: `getRouteApi('/posts')` gives `useLoaderData`, `useParams`, `useSearch`, `useRouteContext` and `useLoaderDeps`. For shared components, pass `useSearch({ strict: false })`.

## Patterns

**Validated search params (Zod v4 or any Standard Schema, no adapter):**
```tsx
import { z } from 'zod'
import { createFileRoute, stripSearchParams } from '@tanstack/react-router'
const productSearch = z.object({
  page: z.number().default(1),
  sort: z.enum(['newest', 'oldest', 'price']).catch('newest'),
})
export const Route = createFileRoute('/shop/products/')({
  validateSearch: productSearch,                                // Valibot / ArkType / Effect: same, no adapter
  loaderDeps: ({ search: { page, sort } }) => ({ page, sort }), // ONLY the keys the loader uses
  loader: ({ deps }) => fetchProducts(deps),
  search: { middlewares: [stripSearchParams({ page: 1, sort: 'newest' })] },
})
// Zod v3: validateSearch: zodValidator(schema) and fallback(z.number(), 1).default(1)
//   from '@tanstack/zod-adapter'; otherwise .default() makes `search` REQUIRED on every <Link>.
```
`retainSearchParams(['key'])` and `stripSearchParams(defaults)` are exported from `@tanstack/react-router`. Validation errors set `error.routerCode === 'VALIDATE_SEARCH'` and render `errorComponent`.

**Auth guard with a pathless layout:**
```tsx
// src/routes/_authenticated.tsx
import { createFileRoute, redirect, isRedirect } from '@tanstack/react-router'
export const Route = createFileRoute('/_authenticated')({
  beforeLoad: async ({ location }) => {
    try {
      const user = await verifySession()
      if (!user) throw redirect({ to: '/login', search: { redirect: location.href } })
      return { user }                    // merged into context for every child route
    } catch (e) {
      if (isRedirect(e)) throw e         // do not swallow the redirect
      throw redirect({ to: '/login', search: { redirect: location.href } })
    }
  },
})
```
A route guard only gates UI. Every API or server function that returns private data must authorize the request itself (`guide/authenticated-routes`).

**TanStack Query integration (current, Query ≥5.102):**
```tsx
import { noop, queryOptions, useSuspenseQuery } from '@tanstack/react-query'
const postsQuery = queryOptions({ queryKey: ['posts'], queryFn: fetchPosts })

export const Route = createFileRoute('/posts')({
  // blocking: data is in the cache before render; the cache wins if present
  loader: ({ context }) => context.queryClient.query({ ...postsQuery, staleTime: 'static' }),
  component: () => {
    const { data } = useSuspenseQuery(postsQuery) // subscribe; SSR-streams under the integration
    return <ul>{data.map((p) => <li key={p.id}>{p.title}</li>)}</ul>
  },
})

// non-blocking: start the fetch, do not await or return it (it streams to the client under SSR)
loader: ({ context, params }) => { void context.queryClient.query(userQuery(params.id)).catch(noop) }
```
The Router docs (`integrations/query`) say that `ensureQueryData` and `prefetchQuery`, used in earlier guides, are **deprecated in favour of `queryClient.query`**. Use `staleTime: 'static'` to get the `ensureQueryData` behaviour and `.catch(noop)` to get the `prefetchQuery` behaviour.

**SSR (Start, or Router SSR) with Query:** use `setupRouterSsrQueryIntegration` from `@tanstack/react-router-ssr-query`. It handles dehydration, hydration, streaming, `redirect()` thrown from queries or mutations, and wraps `QueryClientProvider`.
```tsx
export function getRouter() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } }) // per request!
  const router = createRouter({
    routeTree, context: { queryClient }, defaultPreload: 'intent', defaultPreloadStaleTime: 0,
  })
  setupRouterSsrQueryIntegration({ router, queryClient /* , wrapQueryClient: false, handleRedirects: false,
    dehydrateOptions, hydrateOptions */ })
  return router
}
```
Only `useSuspenseQuery` and loader-started queries run on the server. Plain `useQuery` fetches on the client after hydration.

**Code splitting:**
- `autoCodeSplitting: true` in the plugin is the recommended option (bundler plugin only, not `tsr`).
- Manual alternative: `posts.lazy.tsx` with `createLazyFileRoute('/posts')({ component, pendingComponent, errorComponent, notFoundComponent })`. These four options are the only ones allowed there.
- Code-based routes: `createRoute({...}).lazy(() => import('./posts.lazy').then((d) => d.Route))` with `createLazyRoute`.
- `__root.tsx` is never split.

## Traps

1. **No `Register` declaration.** `Link to` accepts any string and hooks return loose unions. Declare `Register { router: typeof router }` once (`guide/creating-a-router`).
2. **Plugin order.** The docs require `tanstackRouter()` to come **before** `react()` in Vite `plugins` (`installation/with-vite`). Getting this wrong is a common cause of broken code-splitting (unverified).
3. **`TanStackRouterVite`** is the old export name; it survives only as an alias. Import `tanstackRouter` from `@tanstack/router-plugin/vite`. The old package `@tanstack/router-devtools` was replaced by **`@tanstack/react-router-devtools`**.
4. **`ensureQueryData` / `prefetchQuery` in loaders** are deprecated (Query 5.102+). Use `context.queryClient.query({...opts, staleTime: 'static'})`, or `void ...query(opts).catch(noop)`. A bare `query(opts)` with the default `staleTime: 0` **refetches on every navigation** when data exists (`integrations/query`).
5. **Double caching with Query.** The router's own preload freshness (30s) hides Query's `staleTime`. Set `defaultPreloadStaleTime: 0` (`guide/preloading`).
6. **Module-scope QueryClient in SSR** leaks one user's data into another user's HTML. Create it inside `getRouter()`. Do not also add your own `QueryClientProvider` or `dehydrate` call next to the integration; if you own the provider, pass `wrapQueryClient: false`.
7. **Reading `search` in `loader`.** Loaders do not receive `search`. Expose the values through `loaderDeps`, and return **only the keys used**. Returning the whole `search` object reloads the loader on every unrelated search change (`guide/data-loading`).
8. **Zod v3 `.default()` / `.catch()`.** Without `zodValidator` + `fallback`, `.default()` makes `search` required on every `Link`, and `.catch()` turns the types into `unknown`. With Zod v4, pass the schema directly; the adapter is unnecessary (`guide/search-params`).
9. **`errorComponent` `error` is `unknown`** (React and Vue). Narrow it with `error instanceof Error` before reading `.message`.
10. **Swallowed redirects.** `throw redirect()` inside try/catch gets caught by your own catch. Re-throw it when `isRedirect(e)`. Do not call `navigate` from `beforeLoad`/`loader` (deprecated); throw `redirect` instead.
11. **`NotFoundRoute` / `notFoundRoute`** are deprecated, and `notFound()` / `notFoundComponent` do not work while you still use them. Leaf routes have no `<Outlet>`, so they cannot catch not-found errors themselves; use `notFoundComponent` on a parent or `defaultNotFoundComponent`.
12. **Wrong `from`** passes type-checking but throws at runtime when it does not match the rendered route. In shared components use `strict: false` or `to="."`.
13. **Hand-editing the `createFileRoute('/path')` string.** The plugin or CLI writes and updates that path automatically when files are created, moved or renamed. Keep the dev server or `tsr watch` running instead of fixing it by hand (`routing/routing-concepts`).
14. **Hooks inside `loader`/`beforeLoad`** break the Rules of Hooks. Pass hook values through `<RouterProvider context={{...}}>` instead.
15. **Code splitting with `tsr` only.** `autoCodeSplitting` does nothing without the bundler plugin.
16. **`throw redirect({ code })`** is deprecated; use `statusCode`. Route `parseParams`/`stringifyParams` are deprecated; use `params: { parse, stringify }`. `preSearchFilters`/`postSearchFilters` are deprecated; use `search.middlewares`.

## Migration notes

| Older v1 / pre-1.1xx | Current 1.170 |
|---|---|
| `TanStackRouterVite()` | `tanstackRouter({ target: 'react' })` |
| `@tanstack/router-devtools` | `@tanstack/react-router-devtools` |
| `new Router()`, `new Route()`, `new RootRoute()`, `new FileRoute()` | `createRouter`, `createRoute`, `createRootRoute(WithContext)`, `createFileRoute` |
| `rootRouteWithContext` (deprecated alias) | `createRootRouteWithContext<T>()()` |
| `notFoundRoute` option / `NotFoundRoute` | `notFoundComponent` + `throw notFound()` |
| `parseParams` / `stringifyParams` | `params: { parse, stringify }` |
| `preSearchFilters` / `postSearchFilters` | `search: { middlewares: [...] }`, `retainSearchParams`, `stripSearchParams` |
| `navigate()` inside `beforeLoad`/`loader` | `throw redirect({...})` |
| `redirect({ code })` | `redirect({ statusCode })` |
| `<ScrollRestoration />` | `createRouter({ scrollRestoration: true })` |
| `startTransition` on Link/RouterProvider | removed (always uses transitions) |
| `useBlocker(blockerFn, condition)` | `useBlocker({ shouldBlockFn })` |
| `queryClient.ensureQueryData` / `prefetchQuery` in loaders | `queryClient.query({...o, staleTime: 'static'})` / `.catch(noop)` |
| manual `dehydrate`/`hydrate`/`Wrap` router options for Query | `setupRouterSsrQueryIntegration` |
| `zodValidator` everywhere | Zod v4 / Standard Schema passed directly; adapter only for Zod v3 |

`autoCodeSplitting` defaults to `false` in v1 and will default to `true` in v2 (`api/file-based-routing`).

## Go deeper

- `tanstack doc router integrations/query`: Query SSR integration, `queryClient.query`
- `tanstack doc router guide/external-data-loading`: Router as coordinator for Query
- `tanstack doc router guide/data-loading`: lifecycle, loaderDeps, staleTime, errors
- `tanstack doc router guide/search-params`: validation, adapters, middlewares
- `tanstack doc router guide/router-context`: typed context, DI, beforeLoad merging
- `tanstack doc router guide/authenticated-routes`: beforeLoad redirect guards
- `tanstack doc router guide/code-splitting`: auto, `.lazy.tsx`, getRouteApi
- `tanstack doc router guide/automatic-code-splitting`: split groupings and options
- `tanstack doc router guide/not-found-errors`: notFound, notFoundMode, migration
- `tanstack doc router guide/type-safety`: Register, `from`, `strict: false`
- `tanstack doc router guide/navigation`: Link, useNavigate, relative paths
- `tanstack doc router guide/link-options`: reusable `linkOptions`
- `tanstack doc router guide/preloading`: intent preload, external caches
- `tanstack doc router routing/file-naming-conventions`: file-route token table
- `tanstack doc router routing/code-based-routing`: createRoute and addChildren trees
- `tanstack doc router installation/with-vite`: plugin config defaults
- `tanstack doc router installation/with-router-cli`: `tsr generate/watch` without a bundler
- `tanstack doc router api/file-based-routing`: all generator options
- `tanstack doc router guide/ssr`: Router-only SSR (experimental)
- `tanstack doc router how-to/migrate-from-react-router`: migrating from React Router v7
- `tanstack doc start framework/react/guide/tanstack-query`: Start and Query, per request
