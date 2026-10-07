---
name: tanstack
description: "Use the whole TanStack ecosystem correctly at its CURRENT versions, plus the TanStack CLI (`tanstack`, `npx @tanstack/cli`). Covers Start (server functions, middleware, SSR), Router, Query, Table v9, Form, DB, Store, Virtual, Pacer, Hotkeys, AI, Charts, Markdown, Highlight, Devtools, Intent (version-matched skills in node_modules) and Config. Use whenever code imports any @tanstack/* package, or the user wants to scaffold a TanStack app or add add-ons (tanstack create / add, .cta.json), fetch TanStack docs via the CLI, combine libraries (Table + Query + Virtual, Router + Query, Start + Form), or upgrade or debug TanStack code - even if they only say 'useQuery', 'createServerFn', 'useReactTable', 'createFileRoute', 'react-query' or 'TanStack'. APIs moved in 2025-2026 (Table v9, queryClient.query, Store 0.9, Start's Vite plugin), so code from memory is often wrong. Not for React, Next.js or Remix work that uses no TanStack library."
license: MIT
compatibility: >-
  Verified 2026-10-07 against @tanstack/cli 0.71.1 and the npm-latest releases named in each reference
  (Query 5.104, Router 1.170, Start 1.168, Table 9.2, Form 1.33, DB 0.12, Store 0.11, Virtual 3.14,
  Pacer 0.23, Hotkeys 0.11, AI 0.65, Charts 1.0, Markdown/Highlight 1.0, Intent 0.5). Needs Node 20+
  for the CLI and bundled preflight script. React is the primary adapter shown; Solid, Vue, Svelte,
  Angular, Preact, Lit and vanilla differences are noted per library.
metadata:
  author: kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-10-07 09:48:22"
  category: frontend
  tags: tanstack, react, frontend, cli, data-fetching, routing, tables, forms
---

# TanStack

TanStack is 18 libraries that share one philosophy (headless, type-safe, framework-agnostic core + thin adapters) and one
CLI. Most of them shipped breaking changes in the last year, so the main risk is not lack of knowledge but **confident,
outdated code**: `useReactTable` on Table v9, `ensureQueryData` on Query 5.102+, `new Store()` on Store 0.9+,
`app.config.ts` on current Start. This skill gets you to the right version-matched API before you write code.

## 1. Orient before writing code

Run the bundled preflight in the user's project (read-only):

```bash
node <skill-dir>/scripts/tanstack-preflight.mjs <project-dir>          # human summary
node <skill-dir>/scripts/tanstack-preflight.mjs <project-dir> --json   # for parsing
```

It reports the TanStack packages with their declared and installed versions, version-sensitive findings (for example
"Table v9: use useTable + tableFeatures"), whether `.cta.json` exists (so `tanstack add` works), and the
**version-matched skills shipped inside node_modules**. Then pick your sources in this order:

1. **Installed types are the final authority.** `node_modules/@tanstack/<pkg>/dist/**/*.d.ts` match what will compile. When
   docs, references and memory disagree, the types decide.
2. **Skills bundled with the installed package** (TanStack Intent). `npx -y @tanstack/intent@latest list`, then
   `npx -y @tanstack/intent@latest load <pkg>#<skill>` (the `#skill` part is required). They track the installed
   version, but the content can lag: DB's bundled skills targeted 0.6 and one Start example imports a path that no longer
   exists. Cross-check anything that conflicts with a reference's Traps section. See `references/intent.md`.
3. **Live docs through the CLI** (always latest; pass `--docs-version` for an older major):
   `npx -y @tanstack/cli@latest search-docs "<topic>" --library <id> --json`, then
   `npx -y @tanstack/cli@latest doc <id> <path> --json`. See section 4.
4. **This skill's references** for orientation, current APIs, traps and migration tables. Load only the file for the
   library you are touching (section 6).

Your memory of TanStack APIs is the last source, not the first. If the installed major is older than the reference
(the preflight says so), write code for the installed version and say that an upgrade path exists. Do not silently
upgrade the project.

## 2. Pick the library by who owns the state

| The user needs… | Use | Not |
|---|---|---|
| Fetch, cache, refetch, mutate server data | **Query** | Store or `useEffect` + `useState` |
| Live joins, filtering across collections, optimistic multi-row writes, sync engines (Electric, PowerSync) | **DB** (on top of Query or a sync engine) | Query alone, once you are joining client-side |
| Client-only shared state (UI prefs, wizard state, cart) | **Store** (`createStore` / `createAtom`) | Query |
| URLs, nested layouts, typed links, search-param state, loaders | **Router** | ad-hoc `window.location` |
| Router plus SSR, server functions, API routes, middleware, deployment | **Start** (built on Router) | Router + a hand-rolled server |
| Table/datagrid logic: sorting, filtering, grouping, selection, pinning, sizing | **Table** (v9) | a component library, if the user wants full control of markup |
| Thousands of rows, list items, grid cells or chat messages | **Virtual** | rendering everything |
| Form state, field validation (Standard Schema), arrays, multi-step | **Form** | uncontrolled inputs + manual state |
| Debounce, throttle, rate limit, queue, batch | **Pacer** | `setTimeout` in effects |
| Keyboard shortcuts, sequences, held-key state | **Hotkeys** | raw `keydown` listeners |
| LLM chat, tool calls, approvals, streaming, provider adapters | **AI** | hand-rolled SSE parsing |
| Charts (SVG/Canvas grammar) | **Charts** v1 (`@tanstack/charts`) | the 2023 `react-charts` package |
| Markdown parsing/rendering (incl. streamed AI text) and syntax highlighting | **Markdown** / **Highlight** | — |
| One devtools panel for all of the above | **Devtools** | several floating devtools |
| Shipping or loading agent skills inside npm packages | **Intent** | — |
| Building and publishing a library package (maintainers) | **Config** | app projects (it is not for apps) |

Composition (Table + Query + Router search params, Table + Virtual, Form + Start, AI + Start, and others) is in
`references/compositions.md`. Read it whenever two or more TanStack libraries meet in one feature. Most bugs there come
from two libraries both owning the same state.

## 3. Scaffolding and add-ons with the CLI

```bash
npx -y @tanstack/cli@latest create --list-add-ons --framework react --json      # what exists right now
npx -y @tanstack/cli@latest create --addon-details drizzle --json                # options, deps, exclusivity
npx -y @tanstack/cli@latest create my-app --framework react \
  --add-ons tanstack-query,form,drizzle --add-on-config '{"drizzle":{"database":"sqlite"}}' \
  --deployment cloudflare --toolchain biome --no-examples -y
cd my-app && npx -y @tanstack/cli@latest add table --forced                     # later additions
```

The rules that bite (all observed on 0.71.1; full list in `references/cli.md`):
- **Pick at most one add-on per exclusive category** (deploy, auth, orm, database, linter). The CLI does *not* reject
  `prisma,drizzle`; it scaffolds both.
- **`--router-only` silently drops** `--deployment`, `--add-ons` and templates (exit 0). If the user wants hosting, auth,
  an ORM or server code, they want Start; leave the flag off.
- **`tanstack add` needs `.cta.json`** (only CLI-scaffolded projects have it; without it the command exits 0 and does
  nothing) and **blocks on a confirmation prompt** unless you pass `--forced`.
- **Add-on ids depend on the framework and are case-sensitive** (`tRPC`, `oRPC`; Solid has no `tRPC`, `prisma`, `drizzle`,
  `clerk`, `table`, `db`, `ai`). Always list them with the same `--framework`.
- Optionized add-ons default silently (Prisma and Drizzle default to Postgres). Pass `--add-on-config`.
- `--no-tailwind` is a no-op now; `--blank` gives a minimal app without Tailwind. `tanstack mcp` is gone.
- `ecosystem --json` crashes in 0.71.1; use `curl -s https://tanstack.com/api/data/partners`. Partner ids are not add-on ids.
- `pin-versions` in 0.71.1 adds unpublished versions; pin with the package manager instead.
- The `table` add-on installs Table v9, but in projects with examples enabled its demo page is v8 code that breaks `vite build`;
  installing `@tanstack/react-table` directly avoids both that and the demo-only `@faker-js/faker` dependency.
- Scaffolded integrations are not guaranteed to fit together: Drizzle's sqlite option uses `better-sqlite3`, which cannot run on
  Cloudflare Workers, and auth add-ons are not wired to the ORM. Inspect the generated db/auth files against the deployment target.
- Run `tanstack clean-demos --dry-run`, then `-y`, before building real features, so demo routes do not ship.

For an existing project the CLI did not create, install packages directly (each reference lists them per framework).

## 4. Pulling docs on demand

```bash
npx -y @tanstack/cli@latest libraries --json                         # ids, latest major, frameworks, docsUrl
npx -y @tanstack/cli@latest search-docs "optimistic updates" --library query --framework react --limit 5 --json
npx -y @tanstack/cli@latest doc query framework/react/guides/optimistic-updates --json
npx -y @tanstack/cli@latest doc table framework/react/guide/migrating --json
```
The doc path is the part of a search result's `url` after `/docs/`, without the `#anchor`. Search first instead of
guessing; a wrong path exits 1 with `Document not found`. Every reference ends with a verified **Go deeper** list of paths.
Library ids: `start router query table charts form db ai intent virtual pacer hotkeys markdown highlight store config devtools cli`.
CLI groups: state = query, db, ai, store; headlessUI = table, charts, form, hotkeys, markdown, highlight;
performance = virtual, pacer; tooling = intent, config, devtools, cli. Start and Router are ungrouped.

## 5. Version breaks to check before you write a line

The 2025-2026 changes that make code from memory wrong. Each reference's Traps and Migration sections cover the rest.

| Library | Old code (fails or is deprecated) | Current |
|---|---|---|
| Table 9 | `useReactTable`, `getCoreRowModel()`, `sortingFn`, `table.getState()`, pinning `left/right` | `useTable({ features: tableFeatures({ rowSortingFeature, sortedRowModel: createSortedRowModel(), sortFns }) })`, `sortFn`, `table.state` / `table.atoms`, `start/end`; methods cannot be destructured from `row` |
| Query 5.102+ | `ensureQueryData` / `prefetchQuery` / `fetchQuery` | `queryClient.query({ ...opts, staleTime: 'static' })` (ensure) or `.query(opts).catch(noop)` (prefetch); v5: object signatures, `gcTime`, `isPending`, no query `onSuccess` |
| Router + Query | `routerWithQueryClient` (`@tanstack/react-router-with-query`, frozen at 1.130), manual dehydrate | `setupRouterSsrQueryIntegration({ router, queryClient })` from `@tanstack/react-router-ssr-query`, QueryClient created inside `getRouter()` |
| Router | `TanStackRouterVite`, `@tanstack/router-devtools`, `redirect({ code })` | `tanstackRouter()` listed before `react()`, `@tanstack/react-router-devtools`, `redirect({ statusCode })`; search reaches loaders only through `loaderDeps` |
| Start | `app.config.ts` + vinxi, `createAPIFileRoute`, `registerGlobalMiddleware`, `serverOnly`, `getWebRequest` | `tanstackStart()` Vite plugin (before `viteReact()`), `createFileRoute(p)({ server: { handlers } })`, `createStart()` in `src/start.ts`, `createServerOnlyFn`, `getRequest`; server fn `.validator()` (`.inputValidator()` is deprecated again since 1.168.25) |
| Start security | loaders reading secrets; route `beforeLoad` as auth | loaders also run in the browser, so secrets belong in `createServerFn`; auth middleware goes on every server fn / server route. Creating `src/start.ts` turns off automatic CSRF, so add `createCsrfMiddleware` yourself |
| Store 0.9+ | `new Store`, `new Derived`, `new Effect`, `useStore` | `createStore`, `createStore(() => …)` for derived values, `store.subscribe` returns `{ unsubscribe }`, `useSelector(store, sel, { compare })` |
| Form 1 | `validatorAdapter: zodValidator()` | pass Standard Schemas (zod 3.24+/4, valibot, arktype) directly; `onSubmit` gets un-transformed input, so parse it yourself |
| DB 0.8+ | module-level `createCollection` in SSR, `useLiveQuery(fn, deps)` | `collectionOptions` + `DbClient`/`DbProvider`; `useLiveQuery({ query })`; `where` needs `eq()`, not `===` |
| Virtual 3 | `useVirtual`, `size`, `parentRef`, `measureRef` | `useVirtualizer({ count, getScrollElement, estimateSize })`, `measureElement` + `data-index` |
| AI | `openai()` + `model:`, root `temperature`/`maxTokens`, `request.json()` | `openaiText('model')` and other activity factories, `modelOptions` with provider keys, `chatParamsFromRequest(request)`, `toServerSentEventsResponse` |
| Pacer | reading hook state without a selector, `cancel()` to abort | pass a selector (3rd arg) or nothing re-renders; `abort()` stops in-flight async work |
| Charts 1 | `react-charts` `options={{ primaryAxis }}` | `@tanstack/charts` + `defineChart`, marks, `scales.x/y` (both required) |
| Markdown/Highlight | `@tanstack/react-markdown` | does not exist: use the `/react` subpath; bridge with `createTanStackMarkdownHighlighter()` |

## 6. References (load only what the task touches)

| Library / topic | File |
|---|---|
| CLI: create flags, add-on catalogue, `add`, add-on/template authoring, JSON discovery, observed traps | `references/cli.md` |
| Combining libraries, state ownership, stack recipes | `references/compositions.md` |
| Start: files, server functions, server routes, middleware, env, selective SSR, SPA/prerender, hosting | `references/start.md` |
| Router: file/code routes, search params, loaders, context, code splitting, Query integration | `references/router.md` |
| Query: queryOptions, mutations, invalidation, optimistic, infinite, SSR, v4→v5→5.102 | `references/query.md` |
| Table v9: features, row models, server-side mode, selection, pinning, grouping, virtualization | `references/table.md` |
| Virtual: dynamic sizes, window, grid, infinite, chat/end-anchored | `references/virtual.md` |
| Form: fields, validation, arrays, form composition, Start server validation | `references/form.md` |
| DB: collections, live queries, optimistic transactions, sync engines, SSR | `references/db.md` |
| Store: atoms, stores, selectors, adapters | `references/store.md` |
| Pacer: debounce/throttle/rate-limit/queue/batch, async variants | `references/pacer.md` |
| Hotkeys: bindings, sequences, recorder, scoping, input safety | `references/hotkeys.md` |
| AI: `chat()`, `useChat`, tools, approvals/interrupts, providers, Start routes | `references/ai.md` |
| Charts | `references/charts.md` |
| Markdown + Highlight | `references/markdown-highlight.md` |
| Devtools: unified panel, plugins, Vite plugin, production stripping | `references/devtools.md` |
| Intent: load version-matched skills, allowlist, maintainer workflow | `references/intent.md` |
| Config (library maintainers only) | `references/config.md` |

For a production chat workspace (persistence, reconnects, approvals UX, scaling), a dedicated `tanstack-ai-chat`
skill goes deeper than `references/ai.md`. Use it if it is installed.

## 7. Adapter naming across frameworks

Concepts and options are identical across adapters; only the entry points change. React and Preact use `use*` hooks
(`useQuery`, `useTable`, `useForm`). Solid usually takes options as an accessor function, and the hook prefix varies:
Solid Query is `useQuery(() => ({...}))`, while Pacer and Hotkeys use `create*` (`createDebouncedValue`). Vue uses `use*`
composables with refs, Angular `inject*` (`injectQuery(() => ({...}))`), Svelte Query 6 `createQuery(() => ({...}))` on
Svelte 5 runes, and Lit uses controllers. Check the reference before assuming a prefix. Package names follow `@tanstack/<framework>-<library>` (`@tanstack/solid-router`, `@tanstack/vue-query`),
except where a reference says otherwise: Charts, Markdown and Highlight use subpaths, and `svelte-query` is on major 6.
Check `tanstack libraries --json` → `frameworks` before promising an adapter. Start and Router support React and Solid only.

## 8. Before you call it done

- The code matches the **installed** major (preflight), not the newest docs.
- Typecheck and build (`tsc --noEmit`, `vite build`). Start's import protection only fails at build time, not in dev,
  so a passing `vite dev` proves less.
- Router: the route tree is regenerated (dev server or `tsr generate`) and `routeTree.gen.ts` is not hand-edited.
- No secrets in loaders or module scope. Server-only code lives in server functions, server routes or `*.server.*` files.
- Devtools are stripped from production (Vite plugin first, or gated imports).
- For scaffolds: `.cta.json#chosenAddOns` matches what the user asked for (the CLI drops or duplicates intent silently),
  and demo files are cleaned.
- Tell the user which library versions you targeted, and about any upgrade path you deliberately left alone.
