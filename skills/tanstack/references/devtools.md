# TanStack Devtools

> Verified 2026-10-07 against `@tanstack/react-devtools@0.10.13`, `@tanstack/devtools@0.15.0`, `@tanstack/devtools-vite@0.8.5` docs and published type declarations (TanStack CLI 0.71.1). **Alpha**: the API can change in any minor. Re-check with `tanstack doc devtools <path>` when the installed version differs.

## Contents
When to use · Packages · Mental model · Core API · Patterns · Traps · Migration notes · Go deeper

## When to use / when not to

- Use it as **one** devtools shell (`<TanStackDevtools>`) that hosts tabs ("plugins") for Query, Router, Form, Pacer, Hotkeys, Table, AI, a11y and your own panels, side by side (up to 3 panes open at once).
- Use `@tanstack/devtools-vite` for go-to-source, console piping (browser logs in the terminal and server logs in the browser), the server event bus (which AI devtools need), and production stripping.
- Skip the shell if you only want Query or Router devtools. The standalone floating components (`ReactQueryDevtools`, `TanStackRouterDevtools`) still work on their own.
- Not a debugger or profiler. Each plugin only shows what its library emits.

## Packages

| Role | Package (React) | Other frameworks |
|---|---|---|
| Shell adapter | `@tanstack/react-devtools` (peer: react/react-dom >=16.8) | `@tanstack/{preact,solid,vue,svelte,angular}-devtools` |
| Core shell (vanilla, Solid-built) | `@tanstack/devtools` | every adapter re-exports it |
| Vite plugin | `@tanstack/devtools-vite` (peer: vite ^6, ^7 or ^8) | optional for Vue, Svelte and Angular |
| Plugin event client (for authors) | `@tanstack/devtools-event-client` | |
| Server bus (non-Vite) | `@tanstack/devtools-event-bus` (`/server` → `ServerEventBus`) | |

First-party plugin packages. **All export names below were checked against the published `.d.ts` files:**

| Library | Package | Export to pass in `plugins` |
|---|---|---|
| Query | `@tanstack/react-query-devtools` | `{ name, render: <ReactQueryDevtoolsPanel /> }` |
| Router | `@tanstack/react-router-devtools` | `{ name, render: <TanStackRouterDevtoolsPanel /> }` |
| Form | `@tanstack/react-form-devtools` | `formDevtoolsPlugin()` (also `FormDevtoolsPanel`) |
| Pacer | `@tanstack/react-pacer-devtools` | `pacerDevtoolsPlugin()` (also `PacerDevtoolsPanel`) |
| Hotkeys | `@tanstack/react-hotkeys-devtools` | `hotkeysDevtoolsPlugin()` (also `HotkeysDevtoolsPanel`) |
| Table (v9) | `@tanstack/react-table-devtools` | `tableDevtoolsPlugin()` + `useTanStackTableDevtools(table)` |
| AI | `@tanstack/react-ai-devtools` | `aiDevtoolsPlugin()` (also `AiDevtoolsPanel`) |
| Accessibility | `@tanstack/devtools-a11y` | `createA11yPlugin` (from the marketplace registry; options unverified) |

```bash
npm i -D @tanstack/react-devtools @tanstack/devtools-vite
npm i -D @tanstack/react-query-devtools @tanstack/react-router-devtools @tanstack/react-form-devtools
```

## Mental model

- **Shell**: `<TanStackDevtools>` mounts once at the app root. It owns the trigger button, the panel, tabs, settings, the PiP window, hotkeys and the source inspector.
- **Plugin**: `{ id?, name, render, defaultOpen? }`. `render` is a JSX element or `(el, { theme, devtoolsOpen }) => JSX`. The `xxxDevtoolsPlugin()` factories return this object already built.
- **Event system**: libraries emit typed events through `EventClient` (`@tanstack/devtools-event-client`). The shell listens. With `connectToServerBus: true` the client also talks to a server bus over WebSocket/SSE, which `devtools-vite` starts for you.
- **Vite plugin** = source injection (`data-tsd-source` attrs) + server event bus + console piping + enhanced logs + marketplace installer + production stripping. It must be the **first** Vite plugin.
- **Production**: three independent mechanisms. (1) The Vite plugin swaps devtools imports for empty modules on build. (2) Plugin packages and the event client become no-ops when `NODE_ENV !== 'development'`, and each has a `/production` subpath that is never stripped. (3) Non-Vite apps must gate the import themselves.
- The shell persists open panels, position and settings in localStorage, and **that overrides `defaultOpen`**.

## Core API

```tsx
// src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { ReactQueryDevtoolsPanel } from '@tanstack/react-query-devtools'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { formDevtoolsPlugin } from '@tanstack/react-form-devtools'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    <TanStackDevtools
      config={{ position: 'bottom-right', hideUntilHover: true }}
      eventBusConfig={{ connectToServerBus: true }}
      plugins={[
        { name: 'TanStack Query', render: <ReactQueryDevtoolsPanel />, defaultOpen: true },
        { name: 'TanStack Router', render: <TanStackRouterDevtoolsPanel /> },
        formDevtoolsPlugin(),
      ]}
    />
  </StrictMode>,
)
```

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'

export default defineConfig({
  plugins: [
    devtools(), // FIRST
    // react(), tanstackStart(), ...
  ],
})
```

`config` keys: `defaultOpen`, `hideUntilHover`, `position` (`top-left|top-right|bottom-left|bottom-right|middle-left|middle-right`, used when `triggerMode: 'fixed'`), `triggerMode` (`'floating'` default, draggable; or `'fixed'`), `panelLocation` (`top|bottom`), `openHotkey`, `inspectHotkey` (default Shift+Alt+CtrlOrMeta), `requireUrlFlag` + `urlFlag`, `triggerImage`.
`eventBusConfig` keys: `debug`, `connectToServerBus`, `port`.
`devtools()` options: `eventBusConfig { port, debug, enabled }`, `editor { name, open(path, line, col) }`, `enhancedLogs { enabled }`, `removeDevtoolsOnBuild` (default `true`), `logging`, `injectSource { enabled, ignore { files, components } }`, `consolePiping { enabled, levels }`. The package also exports `defineDevtoolsConfig`.
Other adapters: Vue, Svelte and Angular plugins use `component` instead of `render`. Angular uses `<tanstack-devtools [plugins]>` or `provideTanStackDevtools` from `@tanstack/angular-devtools/provider`.

## Patterns

**Router panel inside the shell.** The panel finds the router through context, so render the shell inside the router tree (in Start, the root route's component) or pass the instance:

```tsx
{ name: 'TanStack Router', render: <TanStackRouterDevtoolsPanel router={router} /> }
```

**Table v9.** This takes three steps. A table without `key` is skipped and logs `Missing table key`:

```tsx
import { tableDevtoolsPlugin, useTanStackTableDevtools } from '@tanstack/react-table-devtools'

function Users() {
  const table = useTable({ key: 'users-table', features, columns, data })
  useTanStackTableDevtools(table)
  return <UsersTable table={table} />
}
// root: <TanStackDevtools plugins={[tableDevtoolsPlugin()]} />
```

**Pacer.** Only utilities created with a `key` show up: `new Debouncer(fn, { key: 'Search', wait: 300 })`.

**AI devtools need the server bus.** Pass `aiDevtoolsPlugin()` plus `eventBusConfig={{ connectToServerBus: true }}`. Under Vite, `devtools-vite` starts the bus on port 4206. Under Next.js or any non-Vite setup, start it yourself in `instrumentation.ts`:

```ts
export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs' && process.env.NODE_ENV === 'development') {
    const { ServerEventBus } = await import('@tanstack/devtools-event-bus/server')
    await new ServerEventBus().start()
  }
}
```

**Non-Vite production gating.** Put the shell in its own module and import it only in development:

```tsx
const Devtools = process.env.NODE_ENV === 'development'
  ? (await import('./devtools-setup')).default
  : () => null
```

**Deliberately shipping devtools to production.** Set `devtools({ removeDevtoolsOnBuild: false })`, install `@tanstack/devtools` as a regular dependency (not a devDependency), and import plugins from their `/production` subpath (for example `@tanstack/react-pacer-devtools/production`).

## Traps

1. **Importing `FormDevtools` from `@tanstack/react-form`.** The devtools `configuration` page shows this, but neither package exports `FormDevtools`. Use `formDevtoolsPlugin()` from `@tanstack/react-form-devtools` (form `framework/react/guides/devtools`; confirmed in the package `.d.ts`). The marketplace registry's `importName: 'FormDevtoolsPlugin'` (PascalCase) is also wrong: the export is `formDevtoolsPlugin`.
2. **Passing the floating component as a plugin.** `render: <ReactQueryDevtools />` or `<TanStackRouterDevtools />` mounts a second floating trigger inside the panel. Inside the shell, use the `…Panel` exports (`ReactQueryDevtoolsPanel`, `TanStackRouterDevtoolsPanel`) or the `xxxDevtoolsPlugin()` factories (devtools `quick-start`).
3. **`devtools()` placed after other Vite plugins.** Source injection and stripping then miss transformed code. It must be first in the `plugins` array (`vite-plugin`).
4. **Assuming production stripping works without Vite.** `removeDevtoolsOnBuild` only exists in the Vite plugin. In Next.js, webpack or Rspack the shell ships unless you gate the import yourself (`production`).
5. **Flipping `removeDevtoolsOnBuild: false` and expecting panels to work.** Plugin packages and `EventClient` still no-op in production because they check `NODE_ENV`, independently of the Vite flag. You also need the `/production` imports (`production`, pacer `devtools`, hotkeys `devtools`, table `devtools`).
6. **AI or server-side panels empty.** `connectToServerBus: true` is missing, or there is no server bus because you are not on Vite. Start `ServerEventBus` manually (ai `getting-started/devtools`).
7. **Table plugin mounted but shows nothing.** The table was never registered with `useTanStackTableDevtools(table)`, or it has no `key` option (table `devtools`). Only Table v9 has devtools.
8. **Pacer plugin shows nothing.** The utility has no `key` option and therefore never registers (pacer `devtools`).
9. **`defaultOpen` seems ignored.** localStorage state from earlier sessions wins, and only the first 3 `defaultOpen` plugins open (`plugin-configuration`). Clear the stored settings to test.
10. **Router panel blank or throwing.** The shell is mounted outside `RouterProvider` and no `router` prop was passed (router `devtools`).
11. **Standalone Router devtools hidden in a prod-mode staging build.** `TanStackRouterDevtools` renders nothing when `NODE_ENV === 'production'`. Use `TanStackRouterDevtoolsInProd` or `TanStackRouterDevtoolsPanelInProd` (router `devtools`). For Query, lazy-import `@tanstack/react-query-devtools/production` (query `framework/react/devtools`).

## Migration notes

| Before | Now |
|---|---|
| Floating `<ReactQueryDevtools />` + `<TanStackRouterDevtools />`, each with its own trigger | Both still exported and supported. Preferred: one `<TanStackDevtools plugins=[…Panel]>` shell |
| `@tanstack/router-devtools` (older name, still published in lockstep) | Docs import from `@tanstack/react-router-devtools` / `@tanstack/solid-router-devtools` |
| Form devtools via `FormDevtools` component | `formDevtoolsPlugin()` from `@tanstack/react-form-devtools` |
| Manual `NODE_ENV` gating of every devtools import | `devtools-vite` strips the shell on build. Plugin packages self-no-op outside development |
| Hand-wiring each library's devtools | Marketplace tab installs a plugin and injects its import (Vite dev server only) |

## Go deeper

- `tanstack doc devtools quick-start`: every framework's setup
- `tanstack doc devtools vite-plugin`: all `devtools()` options
- `tanstack doc devtools production`: stripping, `/production` subpaths
- `tanstack doc devtools configuration`: `config` / `eventBusConfig` keys
- `tanstack doc devtools framework/react/adapter`: plugin type, RSC note
- `tanstack doc devtools source-inspector`: go-to-source, hotkey
- `tanstack doc devtools framework/react/guides/custom-plugins`: build your own plugin
- `tanstack doc devtools third-party-plugins`: marketplace registry format
- `tanstack doc table devtools`: Table `key` + registration hook
- `tanstack doc ai getting-started/devtools`: AI panel, server bus
- `tanstack doc router devtools`: standalone Router devtools, InProd
- `tanstack doc query framework/react/devtools`: standalone Query devtools
