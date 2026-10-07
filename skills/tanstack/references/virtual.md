# TanStack Virtual

> Verified 2026-10-07 against `@tanstack/react-virtual@3.14.13` / `@tanstack/virtual-core@3.17.11` docs (TanStack CLI 0.71.1). Re-check with `tanstack doc virtual <path>` when the installed major differs.

Adapter and core version numbers differ (react 3.14.x depends on core 3.17.x) — that is normal. Several options below (`anchorTo`, `followOnAppend`, `scrollToEnd`, `takeSnapshot`, `directDomUpdates`, `useCachedMeasurements`, `laneAssignmentMode`) are recent 3.x additions; confirmed present in the 3.14.13 / 3.17.11 type definitions. On an older 3.x, check `node_modules/@tanstack/virtual-core/dist/esm/index.d.ts` before using them.

## Contents
- When to use · Packages · Mental model · Core API
- Patterns: dynamic heights · window scroll · horizontal/grid/masonry · infinite scroll with Query · chat/end-anchored · scroll restoration
- Traps · Migration notes · Go deeper

## When to use / when not to
- Use when a scroll container would otherwise mount thousands of rows/columns/cells (lists, tables, grids, chat logs, masonry).
- Headless: you render the markup and apply the positions it computes.
- Don't use for < a few hundred simple rows — plain rendering is simpler and keeps find-in-page/accessibility intact.
- Virtualization is not pagination: all `count` items must be addressable on the client (or loaded progressively).

## Packages
| Package | Entry points |
|---|---|
| `@tanstack/react-virtual` | `useVirtualizer`, `useWindowVirtualizer` (peers `react`/`react-dom` 16.8–19); re-exports all of `virtual-core` |
| `@tanstack/virtual-core` | `Virtualizer` class, `defaultRangeExtractor`, `elementScroll`, `windowScroll`, `observeElementRect`, ... |
| `@tanstack/vue-virtual` | `useVirtualizer`, `useWindowVirtualizer` |
| `@tanstack/solid-virtual`, `@tanstack/svelte-virtual`, `@tanstack/lit-virtual` | `createVirtualizer`, `createWindowVirtualizer` (Lit also `VirtualizerController`) |
| `@tanstack/angular-virtual` | `injectVirtualizer`, `injectWindowVirtualizer` |
| `@tanstack/marko-virtual` | Marko tags |

```bash
npm install @tanstack/react-virtual
```
No devtools package.

## Mental model
- Three things you provide: `count`, `getScrollElement` (the element with `overflow: auto` and a bounded size), `estimateSize(index)`.
- The virtualizer returns `getVirtualItems()` → `{ key, index, start, end, size, lane }` and `getTotalSize()`.
- Your markup: scroll element → one inner element sized to `getTotalSize()` with `position: relative` → only the virtual items, absolutely positioned at `start` (via `translateY`/`translateX` or `top`).
- Dynamic sizes: render with the estimate, then `ref={virtualizer.measureElement}` + `data-index` lets a ResizeObserver correct sizes.
- Axis: vertical by default; `horizontal: true` for columns; two virtualizers on the same scroll element = grid; `lanes` = masonry.
- The React instance is created once (`useState`) and mutated; the hook re-renders the component via a reducer on scroll (with `flushSync` by default).

## Core API
```tsx
import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

function List({ items }: { items: Array<{ id: string; label: string }> }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35,
    overscan: 5,                                  // default 1
    getItemKey: (index) => items[index].id,       // default: index
  })

  return (
    <div ref={parentRef} style={{ height: 400, overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}>
        {virtualizer.getVirtualItems().map((v) => (
          <div
            key={v.key}
            style={{
              position: 'absolute', top: 0, left: 0, width: '100%',
              height: v.size,
              transform: `translateY(${v.start}px)`,
            }}
          >
            {items[v.index].label}
          </div>
        ))}
      </div>
    </div>
  )
}
```
Instance methods: `scrollToIndex(i, { align: 'start'|'center'|'end'|'auto', behavior: 'auto'|'smooth' })`, `scrollToOffset(px, opts)`, `scrollBy(delta)`, `scrollToEnd()`, `isAtEnd(threshold?)`, `getDistanceFromEnd()`, `measure()` (drop cached sizes), `resizeItem(i, size)`, `takeSnapshot()`. Properties: `isScrolling`, `scrollDirection`, `scrollOffset`, `scrollRect`, `options`.

Other options: `enabled`, `horizontal`, `paddingStart/End`, `scrollPaddingStart/End`, `scrollMargin`, `gap`, `lanes`, `initialOffset`, `initialRect` (SSR), `rangeExtractor` (sticky items), `onChange(instance, sync)`, `isRtl`, `useScrollendEvent`, `isScrollingResetDelay` (150 ms).
React-only: `useFlushSync` (default `true`), `directDomUpdates` (default `false`), `directDomUpdatesMode: 'transform' | 'position'`.

## Patterns

### 1. Dynamic (measured) sizes
```tsx
const virtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 120,          // estimate the LARGEST plausible size
})
// ...
{virtualizer.getVirtualItems().map((v) => (
  <div
    key={v.key}
    data-index={v.index}                       // required: maps the node to its index
    ref={virtualizer.measureElement}           // ResizeObserver-backed measurement
    style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${v.start}px)` }}
  >
    {rows[v.index].body}
  </div>                                       // NO fixed height here
))}
```
Smooth `scrollToIndex` with dynamic sizes: docs recommend "block translation" — wrap rendered items in one element translated by `items[0].start` instead of positioning each item (api/virtualizer → scrollToIndex). Hidden lists (`display: none` tabs): set `useCachedMeasurements: true` before hiding so the 0-size ResizeObserver callbacks don't wipe measurements.

### 2. Window scrolling
```tsx
const listRef = useRef<HTMLDivElement>(null)
const offsetRef = useRef(0)
useLayoutEffect(() => { offsetRef.current = listRef.current?.offsetTop ?? 0 }, [])

const virtualizer = useWindowVirtualizer({
  count: 10000,
  estimateSize: () => 35,
  overscan: 5,
  scrollMargin: offsetRef.current,     // distance from page top to the list
})
// item style: transform: `translateY(${v.start - virtualizer.options.scrollMargin}px)`
```

### 3. Horizontal, grid, masonry
```tsx
const columnVirtualizer = useVirtualizer({
  horizontal: true, count: cols.length,
  getScrollElement: () => parentRef.current,
  estimateSize: (i) => cols[i].width,
})
// grid: a row virtualizer + column virtualizer on the SAME scroll element;
// inner div { height: rows.getTotalSize(), width: cols.getTotalSize(), position: 'relative' }
// cell: transform: `translateX(${col.start}px) translateY(${row.start}px)`, width: col.size, height: row.size

const masonry = useVirtualizer({ count, getScrollElement, estimateSize: (i) => heights[i], lanes: 4 })
// item: left: `${v.lane * 25}%`, width: '25%', transform: `translateY(${v.start}px)`
// laneAssignmentMode: 'measured' to assign lanes from measured (not estimated) sizes
```
Tables: rows absolute + `translateY`; columns use left/right spacer cells (`virtualColumns[0].start`, `getTotalSize() - last.end`). See table.md → Virtualized rows.

### 4. Infinite scroll with `useInfiniteQuery`
```tsx
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: ['projects'],
  queryFn: ({ pageParam }) => fetchServerPage(10, pageParam),
  initialPageParam: 0,
  getNextPageParam: (last) => last.nextOffset,
})
const allRows = data ? data.pages.flatMap((p) => p.rows) : []

const virtualizer = useVirtualizer({
  count: hasNextPage ? allRows.length + 1 : allRows.length,   // +1 = loader row
  getScrollElement: () => parentRef.current,
  estimateSize: () => 100,
  overscan: 5,
})

const virtualItems = virtualizer.getVirtualItems()
useEffect(() => {
  const last = virtualItems[virtualItems.length - 1]
  if (!last) return
  if (last.index >= allRows.length - 1 && hasNextPage && !isFetchingNextPage) fetchNextPage()
}, [hasNextPage, fetchNextPage, allRows.length, isFetchingNextPage, virtualItems])
// render: v.index > allRows.length - 1 ? 'Loading more...' : allRows[v.index]
```

### 5. Chat / logs / AI streams (end-anchored)
```tsx
const virtualizer = useVirtualizer({
  count: messages.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 72,
  getItemKey: (i) => messages[i]!.id,   // REQUIRED for prepend stability
  anchorTo: 'end',                      // keep visible item stable when history is prepended
  followOnAppend: true,                 // follow new output only if already at the end
  scrollEndThreshold: 80,
  overscan: 6,
})
useLayoutEffect(() => { virtualizer.scrollToEnd() }, [virtualizer])
// prepend history: setMessages((cur) => [...older, ...cur]) — no manual scrollTop math,
// no column-reverse; measureElement keeps a growing streamed last message pinned.
// "Jump to latest" button: show when !virtualizer.isAtEnd(); onClick={() => virtualizer.scrollToEnd({ behavior: 'smooth' })}
```

### 6. Restore scroll after navigation
```tsx
// on unmount
sessionStorage.setItem('list', JSON.stringify({ snapshot: virtualizer.takeSnapshot(), offset: virtualizer.scrollOffset }))
// on mount
const saved = JSON.parse(sessionStorage.getItem('list') ?? 'null')
useVirtualizer({ count, estimateSize, getScrollElement,
  initialMeasurementsCache: saved?.snapshot, initialOffset: saved?.offset })
```

## Traps
1. **No bounded scroll element.** `getScrollElement` returns a div without a fixed/max height and `overflow: auto` → the div grows to `getTotalSize()`, everything is "visible", every row mounts. Give the container a height (or use `useWindowVirtualizer`). (introduction)
2. **Inner element not sized.** Forgetting `height: getTotalSize()` + `position: relative` on the inner div → scrollbar is wrong and absolutely-positioned items collapse. (introduction)
3. **`key={v.index}` with dynamic data.** Index keys reuse DOM nodes for different records and confuse measurement after inserts/sorts. Use `key={v.key}` and set `getItemKey` to a stable id; for chat prepends this is mandatory. (api/virtual-item, chat)
4. **`measureElement` without `data-index`.** The virtualizer can't map the node to an item → sizes never correct. Always pair `ref={virtualizer.measureElement}` with `data-index={v.index}`, and don't also set a fixed `height`. (api/virtualizer → measureElement)
5. **Underestimating `estimateSize` with measured items.** Small estimates cause jumps as items grow above the viewport. Estimate the largest plausible size. (api/virtualizer → estimateSize)
6. **Window virtualizer offset.** With content above the list, positions are off by that height. Set `scrollMargin` and subtract `virtualizer.options.scrollMargin` in the transform. (api/virtualizer → scrollMargin)
7. **React 19 `flushSync` warning.** "flushSync was called from inside a lifecycle method" while scrolling → set `useFlushSync: false`. (framework/react/react-virtual)
8. **`directDomUpdates` contract.** When `true`: inner container must take `ref={virtualizer.containerRef}` and must NOT set height; items must be `position: absolute; top: 0; left: 0` and must NOT set `transform`/`top` (the virtualizer writes them). Set once at mount — toggling leaves stale inline styles. (framework/react/react-virtual)
9. **Native `<table>` layout + absolute rows.** Dynamic-height virtual rows break native table layout; use `display: grid` on table/thead, `display: flex` on `tr`, and explicit cell widths. Firefox measures table border heights differently — the official examples skip dynamic row measurement there. (table: framework/react/guide/virtualization)
10. **Stale virtualizer in memoized children / React Compiler.** The React instance is a single mutable object (created with `useState`, mutated on scroll), so passing `virtualizer` as a prop to a `React.memo`/compiler-memoized child won't re-render it. Read `getVirtualItems()` in the component that called the hook, or pass the derived items down. (derived from `@tanstack/react-virtual` 3.14.13 source; the Virtual docs do not cover React Compiler — unverified as a documented rule)
11. **Unmemoized `getItemKey`.** Changing function identity every render can invalidate measurement caches; memoize it with `useCallback`. (api/virtualizer → getItemKey)
12. **Mixing `resizeItem` and `measureElement` on the same index** → unpredictable sizes. Use one per index. (api/virtualizer → resizeItem)
13. **Expecting overscan > 1 by default.** Default `overscan` is `1`; fast scrolling shows blanks. Use 5-10 for most lists. (api/virtualizer → overscan)

## Migration notes (react-virtual v2 → @tanstack/react-virtual v3)
The v2 package is `react-virtual` (last release 2.10.4, Jan 2022). LLMs still emit its API.

| v2 (`react-virtual`) | v3 (`@tanstack/react-virtual`) |
|---|---|
| `import { useVirtual } from 'react-virtual'` | `import { useVirtualizer } from '@tanstack/react-virtual'` |
| `size: n` | `count: n` |
| `parentRef: ref` | `getScrollElement: () => ref.current` |
| `estimateSize` optional | `estimateSize` required |
| `keyExtractor` | `getItemKey` |
| `rowVirtualizer.virtualItems` | `virtualizer.getVirtualItems()` |
| `rowVirtualizer.totalSize` | `virtualizer.getTotalSize()` |
| `item.measureRef` on each item | `ref={virtualizer.measureElement}` + `data-index` |
| window scrolling via custom `useObserver`/`onScrollElement` | `useWindowVirtualizer` |
| — | `lanes`, `gap`, `scrollMargin`, `anchorTo`, `followOnAppend`, `scrollToEnd`, `takeSnapshot`, `directDomUpdates` |

## Go deeper
- `tanstack doc virtual introduction` — minimal list example
- `tanstack doc virtual api/virtualizer` — every option and method
- `tanstack doc virtual api/virtual-item` — VirtualItem fields
- `tanstack doc virtual framework/react/react-virtual` — useFlushSync, directDomUpdates
- `tanstack doc virtual chat` — end-anchored chat/streams
- `tanstack doc virtual pretext` — text-height estimates via Pretext
- `tanstack doc table framework/react/guide/virtualization` — Table + Virtual
