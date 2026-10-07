# TanStack Pacer

> Verified 2026-10-07 against `@tanstack/pacer@0.23.1` / `@tanstack/react-pacer@0.24.1` docs (TanStack CLI 0.71.1). Beta, pre-1.0: minors break. Re-check with `tanstack doc pacer <path>` when the installed version differs.

## Contents
When to use · Packages · Mental model · Core API · Patterns · Traps · Migration notes · Go deeper

## When to use / when not to
| Need | Utility |
|---|---|
| Only the final value matters (search box, validation, autosave) | Debouncer |
| Steady cadence while activity continues (scroll, resize, progress) | Throttler |
| Hard quota per window; excess **rejected** | Rate limiter |
| Every call must run, in order (FIFO/LIFO/priority, concurrency) | Queuer |
| Collect items, process together (analytics, bulk writes) | Batcher |

Use the **async** variant (`AsyncDebouncer`, `useAsyncDebouncer`, ...) when you need the result, error/success state, retries, or abort. If you pass an async fn to a sync utility, its Promise is ignored.

Don't use Pacer for request de-duplication, caching or refetch timing. TanStack Query already owns those (`staleTime`, dedupe, retries). Pacer belongs on the input side: debounce the *value* you put into a Query key, or rate-limit or queue *mutations*. Library authors who must count every kilobyte can use `@tanstack/pacer-lite` (no store, adapters, or devtools).

## Packages
| Package | Notes |
|---|---|
| `@tanstack/react-pacer` | Hooks + `PacerProvider`. **Re-exports all of `@tanstack/pacer`**, so you don't install core separately. Peer `react >=16.8` |
| `@tanstack/pacer` | Vanilla classes/functions (`Debouncer`, `debounce`, `asyncDebounce`, `Queuer`, ...) and option helpers |
| Other adapters | `@tanstack/{solid,angular,preact,vue,svelte,lit,alpine,ember,octane}-pacer` |
| `@tanstack/pacer-lite` | Non-reactive minimal versions for libraries |
| Devtools | `@tanstack/react-pacer-devtools` + `@tanstack/react-devtools` |

ESM-only, ES2022, Node >= 20 (since react-pacer 0.24 / pacer 0.23).
```bash
npm i @tanstack/react-pacer
npm i -D @tanstack/react-devtools @tanstack/react-pacer-devtools
```

## Mental model
- Each utility is a class (`Debouncer`, `Throttler`, `RateLimiter`, `Queuer`, `Batcher` + `Async*`) whose state lives in a TanStack Store (`instance.store.state`).
- React hooks come in three layers per utility. **Callback** (`useDebouncedCallback`) returns a plain fn. **State/value** (`useDebouncedState`, `useDebouncedValue`) wires into React state. **Instance** (`useDebouncer`) returns the instance with methods and selected state.
- The entry method is `maybeExecute(...args)` for debouncer, throttler and rate limiter, and `addItem(item)` for queuer and batcher.
- Hook state is **opt-in via a selector** (3rd argument). Without it, `instance.state` is `{}` and the component never re-renders on pacer changes.
- Hooks clean up on unmount: sync utilities cancel pending work, async ones cancel and abort. `onUnmount` *replaces* that default.
- `PacerProvider defaultOptions={{ debouncer: {...}, asyncQueuer: {...} }}` sets tree-wide defaults. Hook options override them.
- Async utilities run each execution through `AsyncRetryer` (`asyncRetryerOptions`).

## Core API
React hooks (all verified in `framework/react/reference/index`):

| Utility | Callback | State / value | Instance |
|---|---|---|---|
| Debounce | `useDebouncedCallback` | `useDebouncedState`, `useDebouncedValue` | `useDebouncer` |
| Throttle | `useThrottledCallback` | `useThrottledState`, `useThrottledValue` | `useThrottler` |
| Rate limit | `useRateLimitedCallback` | `useRateLimitedState`, `useRateLimitedValue` | `useRateLimiter` |
| Queue | (none) | `useQueuedState`, `useQueuedValue` | `useQueuer` |
| Batch | `useBatchedCallback` | (none) | `useBatcher` |
| Async | `useAsyncDebouncedCallback`, `useAsyncThrottledCallback`, `useAsyncRateLimitedCallback`, `useAsyncBatchedCallback` | `useAsyncQueuedState` | `useAsyncDebouncer`, `useAsyncThrottler`, `useAsyncRateLimiter`, `useAsyncQueuer`, `useAsyncBatcher` |

Also: `PacerProvider`, `useDefaultPacerOptions`, `usePacerContext`. Instance hooks expose `<instance.Subscribe selector={...}>{(s) => ...}</instance.Subscribe>` for reading state deeper in the tree.

Signatures (React):
```ts
useDebouncer(fn, options, selector?)                 // -> ReactDebouncer (maybeExecute, cancel, flush, reset, setOptions, state)
useDebouncedValue(value, options, selector?)         // -> [debouncedValue, debouncer]
useDebouncedState(initial, options, selector?)       // -> [value, setValue, debouncer]
useQueuedState(fn, options, selector?)               // -> [items, addItem, queuer]
useAsyncQueuedState(fn, options, selector?)          // -> [pendingItems, queuer]
```
Vanilla:
```ts
import { Debouncer, debounce, debouncerOptions } from '@tanstack/pacer'
const d = new Debouncer(fn, { wait: 500, key: 'search' }) // d.maybeExecute(x); d.cancel(); d.flush()
const debounced = debounce(fn, { wait: 500 })              // plain fn
const shared = debouncerOptions({ wait: 1000, trailing: true }) // typed reusable options
```
Other adapters: Solid uses `create*` names (`createDebouncedValue`) and Angular uses `inject*`. As of 0.24.1, Vue, Svelte, Lit, Alpine, Ember and Angular dropped callback-only helpers. Call the instance's `maybeExecute` or `addItem` there.

## Patterns
**1. Debounced search feeding TanStack Query**
```tsx
import { useDebouncedValue } from '@tanstack/react-pacer'
import { useQuery } from '@tanstack/react-query'

function Search() {
  const [q, setQ] = useState('')
  const [debouncedQ] = useDebouncedValue(q, { wait: 300 })
  const results = useQuery({ queryKey: ['search', debouncedQ], queryFn: () => search(debouncedQ), enabled: debouncedQ.length > 1 })
  return <input value={q} onChange={(e) => setQ(e.target.value)} />
}
```
**2. Autosave with pending indicator + "save now"**
```tsx
const saver = useDebouncer(saveDraft, { wait: 1000 }, (s) => ({ isPending: s.isPending }))
// onChange: saver.maybeExecute(draft)
<button disabled={!saver.state.isPending} onClick={() => saver.flush()}>Save now</button>
```
**3. Async debounced fetch with abort**
```ts
const search = useAsyncDebouncer(
  async (query: string) => {
    const res = await fetch(`/api/search?q=${query}`, { signal: search.getAbortSignal() ?? undefined })
    return res.json()
  },
  { wait: 300, onError: reportError, asyncRetryerOptions: { maxAttempts: 3, backoff: 'exponential', baseWait: 500 } },
  (s) => ({ isExecuting: s.isExecuting, lastResult: s.lastResult }),
)
```
**4. Client-side quota**
```tsx
const limiter = useRateLimiter(sendEvent, { limit: 5, window: 60_000, windowType: 'sliding', onReject: () => toast('Slow down') },
  (s) => ({ rejectionCount: s.rejectionCount }))
limiter.maybeExecute(payload)       // returns false when rejected; rejected calls never run later
limiter.getRemainingInWindow(); limiter.getMsUntilNextWindow()
```
**5. Upload queue with concurrency**
```tsx
const [pending, queue] = useAsyncQueuedState(uploadFile, { concurrency: 2 }, (s) => ({ items: s.items, activeItems: s.activeItems }))
queue.addItem(file) // false + onReject when maxSize reached
```
Ordering: `addItemsTo: 'back'` with `getItemsFrom: 'front'` gives FIFO (the default). Use `getItemsFrom: 'back'` for LIFO, and `getPriority: (item) => n` puts higher numbers first. `started: false` collects items before you call `start()`. `stop()` pauses and keeps items.

**6. Analytics batching**
```tsx
const batcher = useBatcher(sendEvents, { maxSize: 20, wait: 1000 }, (s) => ({ size: s.size }))
batcher.addItem({ type: 'click' })   // also: flush(), cancel(), clear(), getShouldExecute: (items) => boolean
```

## Traps
1. **No re-render without a selector.** `useDebouncer(fn, opts).state.isPending` is `undefined` because `state` is `{}`. Pass `(s) => ({ isPending: s.isPending })` as the 3rd arg. This changed in 0.15: selectors are required for reactivity. (`framework/react/adapter`)
2. **Removed getter methods.** `debouncer.getExecutionCount()`, `getIsPending()`, `getOptions()`, `getWait()` no longer exist. Read `instance.state.*` (selected) in render, or `instance.store.state.*` in callbacks. (changelog 0.15)
3. **Renamed async state fields.** `executeCount` became `executionCount` and `settledCount` became `settleCount` on AsyncBatcher/AsyncQueuer (pacer 0.23). Old selectors silently read `undefined`. (changelog)
4. **`cancel()` no longer aborts.** Since 0.16, `cancel()` drops a *pending* trailing call and `abort()` stops *active* async work. Abort only reaches a fetch if you pass `getAbortSignal()` to it. `reset()` neither clears timers nor stops work: call `cancel(); abort(); reset()`. (`framework/react/guides/async-debouncing`)
5. **Replaced async calls resolve early.** When call B replaces pending call A, A's Promise resolves immediately with the current `lastResult` (often `undefined`), not with B's result. Await the latest call. If you need one result per call, use an async queuer. (`framework/react/guides/async-debouncing`)
6. **Errors swallowed after adding `onError`.** Without `onError`, `throwOnError` defaults to true and the Promise rejects. With `onError`, it defaults to false and the Promise resolves with `lastResult`. (`framework/react/guides/async-debouncing`)
7. **Debouncer has no `maxWait`.** Continuous input can postpone execution forever. Use a throttler when the work must run at a bounded interval. (`framework/react/guides/debouncing`)
8. **Batcher `wait` defaults to `Infinity`.** Without `maxSize` or `wait`, a batch only runs on `flush()`. Continuous traffic keeps restarting `wait`, so set `maxSize` too. Batchers have no `start`/`stop`/`isRunning` (removed 0.15). (`framework/react/guides/batching`)
9. **Rate limiter rejects, it doesn't defer.** Rejected calls are gone. If work must happen eventually, use a queuer, or queue from `onReject`. (`framework/react/guides/rate-limiting`)
10. **Queue starts by default.** Items process immediately unless you pass `started: false`. `maxSize` limits *pending* items, not active ones. `addItem(undefined)` is rejected. (`framework/react/guides/async-queuing`)
11. **Devtools show nothing.** A utility only registers when it has a `key` option (auto-uuid removed in 0.16.1). (`devtools`)
12. **`setOptions({ wait })` doesn't reschedule.** The new wait applies on the next call. Disabling via `setOptions({ enabled: false })` cancels pending work. (`framework/react/guides/debouncing`)
13. **Custom `onUnmount` replaces cleanup.** When you provide it, you must cancel/abort yourself. Flushing in it runs callbacks during teardown. (`framework/react/guides/debouncing`)
14. **CommonJS `require` fails** as of react-pacer 0.24 / pacer 0.23. The packages are ESM-only. (`installation`)

## Migration notes
| Old | Current |
|---|---|
| `useQueuerState` | `useQueuedState` (returns `[items, addItem, queuer]`) |
| `get*Item` (queuer) | `peek*Item` |
| `getExecutionCount()`, `getIsPending()`, `getOptions()`, `getWait()` | `state.executionCount` etc. via selector; `store.state` in callbacks |
| `new AsyncQueuer({ ... })` + add functions | `new AsyncQueuer(fn, options)`; add **items**, `fn` processes each |
| `getNextItem` / `onGetNextItem` | `execute()` |
| Implicit reactive `state` | selector arg required (react/solid 0.15) |
| `cancel()` aborting in-flight async work | `cancel()` = pending only; `abort()` = active |
| `executeCount`, `settledCount` (async batcher/queuer) | `executionCount`, `settleCount` |
| `Batcher.start()/stop()/isRunning` | removed |
| async `flush()` returning void | returns a Promise |
| `onError(error)` | `onError(error, args, instance)` (also args on `onSuccess`/`onSettled`/`onExecute`) |
| `ReturnType<TFn>` double-wrapped promise types | `Awaited<ReturnType<TFn>>` (0.23) |
| Angular `inject*Callback` | instance factory + call `maybeExecute` / `addItem` (0.24.1) |
| CJS builds | ESM-only, Node 20+ |

## Go deeper
- `tanstack doc pacer guides/which-pacer-utility-should-i-choose`: pick the right utility
- `tanstack doc pacer framework/react/adapter`: provider, selectors, Subscribe
- `tanstack doc pacer framework/react/reference/index`: full React hook list
- `tanstack doc pacer framework/react/guides/debouncing`: leading/trailing, flush/cancel
- `tanstack doc pacer framework/react/guides/async-debouncing`: promises, abort, retries
- `tanstack doc pacer framework/react/guides/throttling`: throttle timing and state
- `tanstack doc pacer framework/react/guides/rate-limiting`: fixed vs sliding windows
- `tanstack doc pacer framework/react/guides/queuing`: FIFO/LIFO/priority, start/stop
- `tanstack doc pacer framework/react/guides/async-queuing`: concurrency, capacity
- `tanstack doc pacer framework/react/guides/batching`: size/time/custom triggers
- `tanstack doc pacer framework/react/guides/async-retrying`: backoff, timeouts
- `tanstack doc pacer devtools`: devtools setup, `key` requirement
- `tanstack doc pacer installation`: packages, ESM requirement
