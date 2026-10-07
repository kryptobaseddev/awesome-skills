# TanStack Store

> Verified 2026-10-07 against `@tanstack/store@0.11.2` / `@tanstack/react-store@0.11.2` docs and package source (TanStack CLI 0.71.1). Re-check with `tanstack doc store <path>` when the installed minor differs (pre-1.0: minors break).

## When to use / when not to
- Use for small, framework-agnostic client state shared outside React's tree (module-level), with fine-grained selector subscriptions. It is the signals engine under Form, Router devtools, Pacer, etc.
- Pick the right owner first:

| State | Owner |
|---|---|
| Server data (fetch, cache, refetch) | TanStack Query |
| Server data you query/join locally with optimistic writes, or sync-engine data | TanStack DB |
| Component-local UI state | `useState` / `useReducer` |
| Form edit buffer + validation | TanStack Form |
| URL-shareable state (filters, tabs) | Router search params |
| Cross-component client state (cart, UI prefs, wizard) not in the URL | **TanStack Store** |

- Not a persistence layer, devtools-heavy app store, or middleware framework: no built-in persist/undo/devtools.

## Packages
| Framework | Package | Read hook |
|---|---|---|
| core / vanilla | `@tanstack/store` | `store.subscribe` |
| React | `@tanstack/react-store` (react 16.8–19; ReactDOM only, no RN adapter) | `useSelector` |
| Preact | `@tanstack/preact-store` | `useSelector` |
| Vue 2/3 | `@tanstack/vue-store` | `useSelector` → `Readonly<Ref>` |
| Solid | `@tanstack/solid-store` | `useSelector` → `Accessor` |
| Svelte 5 | `@tanstack/svelte-store` | `useSelector` |
| Angular 19+ | `@tanstack/angular-store` | `injectSelector` → `Signal`, `injectAtom` |
| Lit 3 / Octane | `@tanstack/lit-store` / `@tanstack/octane-store` | — |

Adapters re-export everything from `@tanstack/store`. No devtools package.
```sh
npm i @tanstack/react-store
```

## Mental model
- Since 0.9 the core is a signals graph (alien-signals). Two primitives: **atoms** (`createAtom`) and **stores** (`createStore`, a class wrapper over an atom with `.state`, optional actions).
- `createStore(value)` → writable `Store`. `createStore(() => …)` (a function) → **derived** `ReadonlyStore` that auto-tracks every `.state`/`.get()` read inside it.
- `createAtom(value)` → `Atom` with `get/set/subscribe`; `createAtom(() => …)` → `ReadonlyAtom` (computed). `createAsyncAtom(promiseFn)` → readonly atom of `{status:'pending'|'done'|'error'}`.
- Side effects = `subscribe(fn)` returning `{ unsubscribe }`. There is no `Effect` class any more.
- `batch(fn)` coalesces notifications; derived values recompute lazily and only when a dependency changed (`compare` option on atoms; default `===`).
- React reads through `useSelector(source, selector?, { compare? })` built on `useSyncExternalStoreWithSelector`; re-render only when the selected value changes by `compare`.
- `useCreateStore` / `useCreateAtom` create component-scoped instances (stable across renders); `createStoreContext` passes a bundle of atoms/stores down a subtree.

## Core API
```ts
import { batch, createAtom, createStore, shallow } from '@tanstack/store'

export const cart = createStore({ items: [] as Array<{ id: string; qty: number }>, coupon: '' })

cart.setState((prev) => ({ ...prev, coupon: 'SAVE10' }))  // Store.setState takes an UPDATER only
cart.state            // current value (also cart.get())

const itemCount = createStore(() => cart.state.items.reduce((n, i) => n + i.qty, 0)) // ReadonlyStore
const withPrev = createStore<number>((prev) => cart.state.items.length + (prev ?? 0))

const { unsubscribe } = itemCount.subscribe((n) => console.log('count', n))

batch(() => {                     // subscribers fire once with the final state
  cart.setState((s) => ({ ...s, items: [] }))
  cart.setState((s) => ({ ...s, coupon: '' }))
})

const theme = createAtom<'light' | 'dark'>('light')
theme.set('dark')                 // Atom.set accepts a value OR an updater
theme.set((t) => (t === 'dark' ? 'light' : 'dark'))
```

Stores with actions (bound, destructurable):
```ts
export const counter = createStore({ count: 0 }, ({ setState, get }) => ({
  inc: () => setState((s) => ({ count: s.count + 1 })),
  reset: () => setState(() => ({ count: 0 })),
  double: () => get().count * 2,
}))
counter.actions.inc()
```

React:
```tsx
import { useAtom, useCreateStore, useSelector } from '@tanstack/react-store'

function CartBadge() {
  const n = useSelector(itemCount)                                   // whole value of a derived store
  const coupon = useSelector(cart, (s) => s.coupon)                  // slice
  const ids = useSelector(cart, (s) => s.items.map((i) => i.id), { compare: shallow }) // new array each time → shallow
  return <span>{n} {coupon} {ids.length}</span>
}

function ThemeToggle() {
  const [value, setTheme] = useAtom(theme)                           // [value, atom.set]
  return <button onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}>{value}</button>
}

function LocalCounter() {
  const store = useCreateStore({ count: 0 })                         // per-component instance
  const count = useSelector(store, (s) => s.count)
  return <button onClick={() => store.setState((s) => ({ count: s.count + 1 }))}>{count}</button>
}
```

## Patterns
1. **Module store + selector hooks** (most common): export the store and tiny `useX = () => useSelector(store, sel)` hooks; mutate through `store.actions` or exported functions so writes stay in one file.
2. **Derived view-model**: `createStore(() => compute(a.state, b.state))` across several stores; components select from the derived store only.
3. **Subtree-scoped state** (per-route, per-tenant, SSR-safe):
```tsx
import { createStoreContext, useCreateAtom, useCreateStore, useSelector } from '@tanstack/react-store'
import type { Atom, Store } from '@tanstack/react-store'

const { StoreProvider, useStoreContext } = createStoreContext<{
  countAtom: Atom<number>
  totals: Store<{ count: number }>
}>()

function Provider({ children }: { children: React.ReactNode }) {
  const countAtom = useCreateAtom(0)
  const totals = useCreateStore({ count: 0 })
  return <StoreProvider value={{ countAtom, totals }}>{children}</StoreProvider>
}
function Child() {
  const { countAtom, totals } = useStoreContext()   // throws outside the provider
  const count = useSelector(countAtom)
  return <>{count}/{useSelector(totals, (s) => s.count)}</>
}
```
4. **Async value**: `const user = createAsyncAtom(() => fetchUser())` then `useSelector(user)` and switch on `status`. For anything with caching/refetch/invalidation use TanStack Query instead.
5. **Side effect outside React** (persist to localStorage, analytics): `store.subscribe((s) => localStorage.setItem('cart', JSON.stringify(s)))`; hydrate by passing the parsed value to `createStore`.
6. **Reading TanStack Form/other library state**: `useSelector(form.store, (s) => s.values.x)` — same hook, any object with `get` + `subscribe`.

## Traps
1. **`new Store(...)` / `new Derived({ deps, fn })` / `derived.mount()` from memory** → 0.9 replaced them: `createStore(value)` and `createStore(() => …)`; deps are auto-tracked, no `mount()`. (`quick-start`; store CHANGELOG 0.9.0)
2. **`new Effect({ deps, fn })`** → removed in 0.9. Use `store.subscribe(fn)`; it returns `{ unsubscribe }` (an object, not a function). (`quick-start`)
3. **`useStore` from `@tanstack/react-store`** → deprecated alias of `useSelector` since 0.11; its 3rd arg was a bare compare fn, `useSelector` takes `{ compare }`. Don't confuse with the experimental `_useStore` tuple hook. (`framework/react/quick-start`)
4. **`store.setState(newValue)`** → `Store.setState` only accepts an updater `(prev) => next`; passing an object is a type error. `Atom.set` accepts both. (store source `store.ts`)
5. **Calling `setState` on a derived store** → `createStore(fn)` returns `ReadonlyStore` (since 0.9.1); write to its sources instead.
6. **Selector returning a fresh object/array without `compare`** → default compare is `===`, so every store change re-renders. Return primitives, or pass `{ compare: shallow }`. (`framework/react/reference/functions/useSelector`)
7. **`useSelector(store)` with no selector on a big object** → subscribes to the whole state; any field change re-renders.
8. **Creating a store inside a component body with `createStore`** → new instance each render, subscriptions churn. Use `useCreateStore` / `useCreateAtom` or module scope.
9. **Module-level stores under SSR** → shared across requests on the server. Create per-request instances (`useCreateStore` + `createStoreContext`) for request-specific data.
10. **`createStore(fn)` meant as an initial *value* that is a function** → any function argument is treated as a derived getter. Wrap: `createStore({ handler: fn })`.
11. **`subscribe` callback reading other atoms** → fixed in 0.11.2 (reads inside observers no longer become dependencies); on 0.11.0–0.11.1 such reads caused spurious notifications. Upgrade.

## Migration notes
| ≤0.8 | 0.9–0.11 (current) |
|---|---|
| `new Store(initial, { onUpdate, updateFn })` | `createStore(initial)` or `createStore(initial, actionsFactory)` |
| `new Derived({ deps: [a], fn: ({ currDepVals }) => … })` + `.mount()` | `createStore(() => a.state …)` (auto-tracked, readonly) |
| `new Effect({ deps, fn, eager })` + `.mount()` | `store.subscribe(fn)` → `{ unsubscribe }` |
| `store.subscribe(fn)` returning an unsubscribe fn | returns `{ unsubscribe }` |
| `useStore(store, sel, compareFn)` | `useSelector(store, sel, { compare })` (0.11) |
| — | `createAtom`, `createAsyncAtom`, `useAtom`, `useCreateAtom`, `useCreateStore`, `createStoreContext` (0.11) |
| hand-rolled deep compare | `shallow` exported from core |

## Go deeper
- `tanstack doc store quick-start` - createStore, derived, batch, subscribe
- `tanstack doc store installation` - adapter packages, framework versions
- `tanstack doc store framework/react/quick-start` - useSelector example
- `tanstack doc store framework/react/reference/functions/useSelector` - selector + compare options
- `tanstack doc store framework/react/reference/functions/useAtom` - tuple hook for atoms
- `tanstack doc store framework/react/reference/functions/useCreateStore` - component-scoped stores
- `tanstack doc store framework/react/reference/functions/createStoreContext` - subtree provider
- `tanstack doc store reference/functions/createAtom` - atom signature, compare option
- `tanstack doc store reference/functions/createAsyncAtom` - promise-backed atom
- `tanstack doc store reference/classes/Store` - Store class surface
- `tanstack doc store framework/angular/reference/functions/injectSelector` - Angular signal binding
