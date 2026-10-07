# TanStack Start

> Verified 2026-10-07 against `@tanstack/react-start@1.168.60` docs + its published `.d.ts` (TanStack CLI 0.71.1). Router `@tanstack/react-router@1.170.41`. Re-check with `tanstack doc start framework/react/<path>` when the installed major differs.

## Contents
When to use · Packages · Mental model · Core API (files, server fns, server routes, middleware, execution control, env) · Patterns (auth, SSR modes, SPA/prerender, streaming, Query, hosting) · Traps · Migration notes · Go deeper

## When to use / when not to
- Use for a full-stack React (or Solid) app on TanStack Router: SSR/streaming, type-safe RPC (`createServerFn`), HTTP endpoints, middleware, deploy anywhere via Vite (or Rsbuild).
- Docs still label Start a **Release Candidate**: the API is stable, but it has no 1.0 tag.
- Use plain TanStack Router instead when you know you need none of SSR, server functions, server routes, or middleware.
- Not Next.js. Do not write `"use server"`, `getServerSideProps`, `app/layout.tsx`, `app.config.ts`, or `vinxi`.

## Packages
| Need | Package |
|---|---|
| React framework | `@tanstack/react-start` + `@tanstack/react-router` |
| Solid framework | `@tanstack/solid-start` + `@tanstack/solid-router` (`latest` 1.168.x = solid-js 1; `rc` tag 2.0.0-rc.x requires `solid-js@2` + `@solidjs/web`) |
| Build | `vite` (peer `>=7`; current 8.x) + `@vitejs/plugin-react`, or `@rsbuild/core@^2` + `@rsbuild/plugin-react` |
| Query SSR glue | `@tanstack/react-query` + `@tanstack/react-router-ssr-query` |
| Static server fns (experimental) | `@tanstack/start-static-server-functions` |
| Hosting | `nitro` (`nitro/vite`, v3 still published as beta), `@cloudflare/vite-plugin` + `wrangler`, `@netlify/vite-plugin-tanstack-start` |

```bash
npm i @tanstack/react-start @tanstack/react-router react react-dom
npm i -D vite @vitejs/plugin-react typescript @types/react @types/react-dom @types/node
# or scaffold: npx @tanstack/cli@latest create
```

## Mental model
- **Everything is isomorphic by default.** Route `loader`/`beforeLoad` run on the server for the first request and **in the browser on client navigation**. A loader is not a server-only boundary.
- `createServerFn` is the server boundary. The compiler swaps its body for an RPC stub in the client bundle. During SSR it is called directly, with no fetch.
- Server routes are `createFileRoute(path)({ server: { handlers } })` in `src/routes`. They are the raw HTTP surface, for webhooks, public APIs, and files.
- Middleware comes in two kinds. **Request** middleware (`createMiddleware()`) wraps every request: SSR, server routes, and server fns. **Function** middleware (`createMiddleware({ type: 'function' })`) wraps server fns only and gets `.client()` + `.validator()`.
- `src/start.ts` (`createStart`) is optional. It holds global middleware, `defaultSsr`, and `serverFns.fetch`. Creating it **switches off the auto-installed CSRF middleware**.
- `src/router.tsx` must export `getRouter()`, which returns a **new** router every call because Start builds one per SSR request.
- `src/server.ts` and `src/client.tsx` are optional entry overrides. The defaults are used when they are absent.

## Core API

### Files and config
```
src/routes/__root.tsx   # required, document shell
src/router.tsx          # required, export function getRouter()
src/routeTree.gen.ts    # generated on dev/build
src/start.ts            # optional: createStart (global middleware, defaultSsr)
src/server.ts           # optional: createServerEntry({ fetch })
src/client.tsx          # optional: hydrateRoot(document, <StartClient />)
vite.config.ts          # tanstackStart() plugin
```
```ts
// vite.config.ts
import { defineConfig } from 'vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'

export default defineConfig({
  server: { port: 3000 },
  resolve: { tsconfigPaths: true }, // Vite 8 built-in; Vite 7 uses vite-tsconfig-paths
  plugins: [tanstackStart(), viteReact()], // react plugin AFTER start
})
```
`tanstackStart()` options (from the plugin schema): `srcDirectory` (default `src`), `router` (generator options such as `routesDirectory`, plus `basepath`), `server.build.staticNodeEnv`, `serverFns` (`base` default `/_serverFn`, `disableCsrfMiddlewareWarning`, `generateFunctionId`), `spa`, `prerender`, `pages`, `sitemap`, and `importProtection`. **There is no `target` option.** Rsbuild uses `@tanstack/react-start/plugin/rsbuild`.

```tsx
// src/router.tsx
import { createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'
export function getRouter() {
  return createRouter({ routeTree, scrollRestoration: true })
}

// src/routes/__root.tsx
import type { ReactNode } from 'react'
import { Outlet, createRootRoute, HeadContent, Scripts } from '@tanstack/react-router'
export const Route = createRootRoute({
  head: () => ({ meta: [{ charSet: 'utf-8' }, { name: 'viewport', content: 'width=device-width, initial-scale=1' }, { title: 'App' }] }),
  shellComponent: RootDocument, // always SSR'd; wraps component/errorComponent/notFound
  component: Outlet,
})
function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html><head><HeadContent /></head>
      <body>{children}<Scripts /></body></html>
  )
}
```
Solid: imports come from `@tanstack/solid-router`. The Vite plugin is `vite-plugin-solid` with `viteSolid({ ssr: true })`, placed after `tanstackStart()`. The root renders `<HydrationScript />` (from `solid-js/web`) in `<head>` and wraps children in `<Suspense>`.

### Server functions
```ts
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { z } from 'zod'

export const getPost = createServerFn({ method: 'GET' })          // GET is the default
  .validator(z.object({ id: z.string() }))                       // Standard Schema or (d: T) => T
  .handler(async ({ data, context }) => db.post.find(data.id))

await getPost({ data: { id: '1' } })              // always one `data` arg
await getPost({ data: { id: '1' }, headers: { 'X-Trace': 'a' } })
const fn = useServerFn(getPost)                   // in components: routes thrown redirect()/notFound()
```
- POST functions can accept `FormData`. Use the validator to check `data instanceof FormData`.
- Inputs and outputs are type-checked for serializability (`strict` is on by default). `createServerFn({ strict: false | { input: false } | { output: false } })` relaxes the types only. A handler may return a `Response`.
- `throw redirect({ to })` / `throw notFound()` from `@tanstack/react-router` work inside handlers.
- Request and response helpers live in `@tanstack/react-start/server`: `getRequest`, `getRequestHeader(s)`, `getRequestIP`, `setResponseHeader(s)`, `setResponseStatus`, `getCookie(s)`, `setCookie`, `deleteCookie`, `useSession`/`getSession`/`updateSession`/`clearSession`.
- File convention from the docs: `x.functions.ts` (createServerFn wrappers, importable anywhere), `x.server.ts` (server-only helpers), plain `.ts` (shared schemas).

### Server routes (API routes)
```ts
// src/routes/api/users/$id.ts
import { createFileRoute } from '@tanstack/react-router'
export const Route = createFileRoute('/api/users/$id')({
  server: {
    middleware: [authMiddleware],                       // all methods
    handlers: {
      GET: async ({ request, params, context }) => Response.json({ id: params.id }),
    },
    // or per-method middleware:
    // handlers: ({ createHandlers }) => createHandlers({ POST: { middleware: [m], handler: async ({ request }) => new Response('ok') } }),
  },
})
```
The same file may also export a `component`. Splat params arrive as `params._splat`. Escape a literal dot with `users[.]json.ts`. `users.ts`, `users.index.ts`, and `users/index.ts` all claim `/users`, and duplicates error.

### Middleware
```ts
import { createMiddleware, createStart, createCsrfMiddleware } from '@tanstack/react-start'

export const authMiddleware = createMiddleware().server(async ({ next, request }) => {
  const session = await auth.getSession({ headers: request.headers })
  if (!session) throw new Error('Unauthorized')
  return next({ context: { session } })              // merged into downstream context
})

export const withWorkspace = createMiddleware({ type: 'function' })
  .middleware([authMiddleware])                      // function mw may depend on request mw (not vice versa)
  .validator(z.object({ workspaceId: z.string() }))
  .client(async ({ next }) => next({ headers: { 'X-Client': 'web' }, sendContext: { tz: 'UTC' } }))
  .server(async ({ next, data, context }) => next({ context: { ws: data.workspaceId } }))

// src/start.ts  (global)
export const startInstance = createStart(() => ({
  requestMiddleware: [createCsrfMiddleware({ filter: (ctx) => ctx.handlerType === 'serverFn' }), authLogger],
  functionMiddleware: [loggingMiddleware],
  // defaultSsr: false,
  // serverFns: { fetch: customFetch },
}))
```
Execution order: global middleware first, then dependency-first through the chain. Use `sendContext` for client→server or server→client context. Client-sent context is untrusted, so validate it *and* authorize it on the server. Header precedence, lowest to highest: earlier middleware, later middleware, call site. Custom `fetch` applies on the client only.

### Execution control (all from `@tanstack/react-start`)
| API | Behavior |
|---|---|
| `createServerFn()` | RPC; runs on the server, callable from the client |
| `createServerOnlyFn(fn)` | runs on the server; **throws** on the client |
| `createClientOnlyFn(fn)` | runs on the client; **throws** on the server |
| `createIsomorphicFn().server(fn).client(fn)` | per-env implementation; the missing side is a no-op returning `undefined` |
| `<ClientOnly fallback>` / `useHydrated()` | from `@tanstack/react-router`; render after hydration |
| `import '@tanstack/react-start/server-only'` / `'.../client-only'` | marks a whole file (same as the `.server.*` / `.client.*` suffix) |

### Environment variables
- Server: `process.env.ANYTHING` inside handlers, middleware `.server()`, and server-route handlers.
- Client: only `import.meta.env.VITE_*` (Rsbuild uses `PUBLIC_*`). Values are **inlined at build time**.
- To give the client a runtime value, return it from a server fn.
- `.env`, `.env.local`, `.env.[mode]` are loaded automatically. Type them in `src/env.d.ts` (`ImportMetaEnv` + `NodeJS.ProcessEnv`).
- `process.env.NODE_ENV` is statically replaced in server builds (`server.build.staticNodeEnv: true`). Turn it off for one-artifact multi-env deploys, and then set `NODE_ENV=production` at runtime yourself.

## Patterns

### 1. Loader → server fn → invalidate after mutation
```tsx
const getCount = createServerFn().handler(() => readCount())
const addCount = createServerFn({ method: 'POST' }).validator((n: number) => n)
  .handler(async ({ data }) => writeCount(data))
export const Route = createFileRoute('/')({ loader: () => getCount(), component: Home })
function Home() {
  const router = useRouter(); const count = Route.useLoaderData()
  return <button onClick={async () => { await addCount({ data: 1 }); await router.invalidate() }}>{count}</button>
}
```

### 2. Auth (cookie session + guard + data-boundary check)
```ts
import { useSession } from '@tanstack/react-start/server'
export const useAppSession = () =>
  useSession<{ userId?: string }>({ name: 'app-session', password: process.env.SESSION_SECRET!, cookie: { httpOnly: true, sameSite: 'lax', secure: true } })
export const getCurrentUserFn = createServerFn().handler(async () => {
  const s = await useAppSession(); return s.data.userId ? getUser(s.data.userId) : null
})
// routes/_authed.tsx: UX guard only
export const Route = createFileRoute('/_authed')({
  beforeLoad: async ({ location }) => {
    const user = await getCurrentUserFn()
    if (!user) throw redirect({ to: '/login', search: { redirect: location.href } })
    return { user }
  },
})
```
The guard is UX, not security. **Every** server fn or server route that returns or mutates private data needs `.middleware([authMiddleware])` or an in-handler check. Give root responses carrying session data `headers: () => ({ 'Cache-Control': 'private, no-store' })`. After login or logout, call `await router.invalidate()`. Hosted options in the docs are Clerk, WorkOS, Better Auth, and Auth.js.

### 3. Selective SSR
`ssr: true` (default) | `'data-only'` (loader runs on the server, component renders on the client) | `false` (both run on the client) | `({ params, search }) => ...` (runs server-only, and `params`/`search` are `{ status, value | error }`).
- A child can only become **more** restrictive than its parent.
- Set the global default with `createStart(() => ({ defaultSsr: false }))`.
- With root `ssr: false`, `shellComponent` still SSRs `<html>`.
- The first non-SSR route renders its `pendingComponent` as the server fallback.

### 4. SPA mode / prerendering / static
```ts
tanstackStart({ spa: { enabled: true } })   // root-only prerender -> /_shell.html; rewrite 404s to it
tanstackStart({
  prerender: { enabled: true, crawlLinks: true, autoStaticPathsDiscovery: true, filter: ({ path }) => !path.startsWith('/admin') },
  pages: [{ path: '/my-page', prerender: { enabled: true } }],
})
```
- SPA hosts must still route `/_serverFn/*` (or your `serverFns.base`) and your server-route prefixes (e.g. `/api/*`) to the server before the catch-all `/* /_shell.html 200`.
- Auto-discovery skips param routes, `_` layout routes, and component-less routes.
- Static server fns: put `.middleware([staticFunctionMiddleware])` **last** in the chain (experimental).

### 5. Streaming
- Deferred loader data: return an **unawaited** promise from the loader and render it with `<Await promise fallback>{(d) => ...}</Await>` (router feature, streamed during SSR).
- Server fns can stream: return a typed `ReadableStream<T>`, or make the handler an `async function*`. The client consumes the generator with `for await (const m of await fn())`.

### 6. TanStack Query
Create `QueryClient` **inside `getRouter()`**, pass it as `context: { queryClient }`, and call `setupRouterSsrQueryIntegration({ router, queryClient })`. The integration provides `QueryClientProvider` and dehydration, so do not add a second provider. In loaders, `await context.queryClient.query(opts)` (Query ≥5.102; `ensureQueryData` on older versions) and read with `useSuspenseQuery(opts)` in the component.

### 7. Hosting
| Target | Setup (docs, Oct 2026) |
|---|---|
| Cloudflare Workers | `cloudflare({ viteEnvironment: { name: 'ssr' } })` **before** `tanstackStart()`. `wrangler.jsonc` sets `"main": "@tanstack/react-start/server-entry"` and `nodejs_compat`. Deploy with `wrangler deploy`. |
| Netlify | `netlify()` from `@netlify/vite-plugin-tanstack-start`, anywhere in the plugins. `npx netlify deploy`, or `netlify.toml` with `publish = "dist/client"`. |
| Node / Docker / Vercel / Railway | `nitro()` from `nitro/vite`; `node .output/server/index.mjs`. Vercel and Railway follow the Nitro steps. |
| Bun | `nitro({ preset: 'bun' })` (React 19 only), or the example `server.ts`. |
| Rsbuild + Node | `dist/server/index.js` exports `{ fetch }`; e.g. `srvx --prod -s ../client dist/server/index.js` |

Custom server entry, e.g. to pass typed request context:
```ts
// src/server.ts
import handler, { createServerEntry } from '@tanstack/react-start/server-entry'
export default createServerEntry({ fetch: (req) => handler.fetch(req, { context: { tenant: 'x' } }) })
// type it via: declare module '@tanstack/react-router' { interface Register { server: { requestContext: {...} } } }
```

## Traps
1. **`.inputValidator()` is deprecated.** Writing it from memory fails → since react-start 1.168.25 the canonical name is `.validator()`, on both `createServerFn` and function middleware, and the compiler emits warnings for `inputValidator`. Fix: use `.validator()`. (`guide/server-functions`, `.d.ts` `@deprecated`)
2. **Adding `src/start.ts` removes CSRF protection.** Without `start.ts`, Start auto-installs CSRF for server fns. Once the file exists it does not, and you only get a dev warning. Fix: add `createCsrfMiddleware({ filter: (ctx) => ctx.handlerType === 'serverFn' })` to `requestMiddleware`. Behind a proxy, also pass `origin`. (`guide/middleware#csrf-middleware`)
3. **Secrets in loaders.** `process.env.SECRET` in a `loader` ships to, or runs in, the browser on client navigation. Fix: read it inside a server fn and call that from the loader. (`guide/execution-model`)
4. **Module-scope env reads.** `const k = process.env.KEY` at top level leaks into the client bundle *and* is `undefined` on Workers, where env is per-request. Fix: read env inside handlers, or use `createServerOnlyFn(() => process.env.KEY)`. On Workers you can also use `import { env } from 'cloudflare:workers'`. (`guide/environment-variables`)
5. **`beforeLoad` as security.** Server fns are public endpoints reachable without the route, so a guard alone protects nothing. Fix: attach auth middleware to every private server fn and route. (`guide/authentication-server-primitives`)
6. **Plugin order.** If `viteReact()` comes before `tanstackStart()`, route generation and server-fn compilation break. Cloudflare's plugin goes **first**. (`build-from-scratch`, `guide/hosting`)
7. **Module-scope router or QueryClient.** `export const router = createRouter(...)` or a global `QueryClient` shares state across SSR requests and leaks one user's data into another's HTML. Fix: build them inside `getRouter()`. (`guide/routing`, `guide/tanstack-query`)
8. **Self-fetching your own API in SSR loaders.** `fetch('/api/x')` from a loader has no origin on the server and adds a hop. Fix: call a server fn, or share a service module with the server route. Use server routes only for external callers.
9. **`verbatimModuleSyntax: true`** in tsconfig can leak server code into client bundles. Keep it off. (`build-from-scratch`)
10. **Dynamic `await import('./x.functions')`** of server fns can break the compiler. Use static imports, which are safe in client files. (`guide/server-functions`)
11. **Import protection** is on by default. A client-reachable import of `*.server.*` or of `@tanstack/react-start/server` warns and mocks in dev but **fails `vite build`**. Use those imports only from server fn handlers, middleware `.server()`, or `.server.ts` files. Type-only imports are fine. (`guide/import-protection`)
12. **`VITE_` vars are build-time.** Setting `VITE_X` only on the host at runtime does nothing. Fix: set it during `vite build`, or pass a runtime value through a server fn. A `VITE_` secret is public. (`guide/environment-variables`)
13. **`public` Cache-Control on identity-dependent responses** lets a CDN serve one user's data to another. Use `private` plus `Vary: Cookie, Authorization`, or `no-store`. (`guide/server-functions`)
14. **Hydration mismatch** from `Date`, `Intl` locale or time zone, or random IDs. Fix: make the server deterministic (locale and tz from a cookie via middleware), or use `<ClientOnly>`, `useHydrated()`, or `ssr: 'data-only'`. Use `suppressHydrationWarning` only as a last resort. (`guide/hydration-errors`)
15. **Stale bundled skill.** `@tanstack/react-start@1.168.60` ships `skills/.../06-low-level-flight-api-route.tsx` that imports `createAPIFileRoute` from `@tanstack/react-start/api`. That export path does not exist in the package `exports`. Do not copy it.
16. **SSR inheritance.** A child `ssr: true` under a parent with `ssr: false` stays `false`, because inheritance only tightens. (`guide/selective-ssr`)

## Migration notes
Older Start (vinxi era ≤1.120; Vite plugin landed in 1.121.0, 2025-06-10; RC line 1.132.0, 2025-09-23) → current 1.168.x. Every "old" name below is **absent** from 1.168.60 exports (grepped).

| Old | Current |
|---|---|
| `app.config.ts` + `defineConfig` from `@tanstack/start/config`, `vinxi dev` | `vite.config.ts` with `tanstackStart()` from `@tanstack/react-start/plugin/vite`; scripts `vite dev` / `vite build` |
| package `@tanstack/start` | `@tanstack/react-start` / `@tanstack/solid-start` |
| `app/` source dir | `src/` (configurable via `srcDirectory`) |
| `tanstackStart({ target: 'netlify' \| 'node-server' ... })` | no `target`; add a host plugin (`nitro()`, `cloudflare()`, `netlify()`) |
| `tanstackStart({ customViteReactPlugin: true })` / implicit React plugin (old name unverified) | add `viteReact()` yourself, after `tanstackStart()` |
| `tsr: {...}` plugin key (old name unverified) | `router: {...}` |
| `createAPIFileRoute('/api/x')({ GET })` (`@tanstack/react-start/api`) → then `createServerFileRoute().methods({...})` | `createFileRoute('/api/x')({ server: { handlers: { GET } } })` |
| `export function createRouter()` in `router.tsx` | `export function getRouter()` (new instance per call) |
| `ssr.tsx` with `createStartHandler({ createRouter })(defaultStreamHandler)` | optional `src/server.ts` with `createServerEntry({ fetch })` from `@tanstack/react-start/server-entry` |
| `registerGlobalMiddleware({ middleware })` in `global-middleware.ts` | `src/start.ts` → `createStart(() => ({ requestMiddleware, functionMiddleware }))` |
| `serverOnly(fn)` / `clientOnly(fn)` | `createServerOnlyFn(fn)` / `createClientOnlyFn(fn)` |
| `getWebRequest()` / `getEvent()` (h3-era; `getEvent` unverified) | `getRequest()` from `@tanstack/react-start/server` |
| `.validator()` → `.inputValidator()` (RC) → | `.validator()` again (1.168.25+; `inputValidator` deprecated) |
| `vite-tsconfig-paths` plugin | still works on Vite 7; Vite 8 uses `resolve.tsconfigPaths: true` |
| nitro target config inside `tanstackStart` | goes into the `nitro()` Vite plugin |

## Go deeper
- `tanstack doc start framework/react/build-from-scratch`: minimal setup, files.
- `tanstack doc start framework/react/guide/server-functions`: validator, errors, context helpers.
- `tanstack doc start framework/react/guide/server-routes`: handlers, createHandlers, params.
- `tanstack doc start framework/react/guide/middleware`: request/function middleware, CSRF, start.ts.
- `tanstack doc start framework/react/guide/execution-model`: isomorphic rules, env-only fns.
- `tanstack doc start framework/react/guide/environment-variables`: VITE_/PUBLIC_, runtime env.
- `tanstack doc start framework/react/guide/selective-ssr`: ssr true/false/data-only.
- `tanstack doc start framework/react/guide/spa-mode`: shell, redirects.
- `tanstack doc start framework/react/guide/static-prerendering`: prerender options.
- `tanstack doc start framework/react/guide/hosting`: Cloudflare, Netlify, Nitro, Bun.
- `tanstack doc start framework/react/guide/authentication`: sessions, guards.
- `tanstack doc start framework/react/guide/authentication-server-primitives`: data-boundary auth.
- `tanstack doc start framework/react/guide/import-protection`: server/client leak rules.
- `tanstack doc start framework/react/guide/tanstack-query`: per-router QueryClient, SSR.
- `tanstack doc start framework/react/guide/hydration-errors`: mismatch strategies.
- `tanstack doc start framework/react/guide/streaming-data-from-server-functions`: streams, generators.
- `tanstack doc start framework/react/guide/server-entry-point`: custom server.ts, request context.
- `tanstack doc start framework/react/migrate-from-next-js`: Next.js migration.
- `tanstack doc start framework/solid/build-from-scratch`: Solid setup.
- `tanstack doc router guide/deferred-data-loading`: Await, streamed loader data.
