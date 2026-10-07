# TanStack Table

> Verified 2026-10-07 against `@tanstack/react-table@9.2.6` / `@tanstack/table-core@9.2.6` docs (TanStack CLI 0.71.1). Re-check with `tanstack doc table <path>` when the installed major differs.

**v9 is `latest` on npm** (`npm view @tanstack/react-table dist-tags` → `latest: 9.2.6`; 9.0.0 shipped 2026-08-04; last v8 is 8.21.3). A fresh `npm install @tanstack/react-table` gets v9, where `useReactTable` and `getCoreRowModel` **do not exist** in the main entry. Check `package.json` before writing code: `^8` → v8 API; `^9` → this file.

## Contents
- When to use / when not to · Packages · Mental model · Core API
- Patterns: server-side with Query · row selection · sizing/pinning/visibility · grouping/expanding · virtualized rows · fine-grained state
- Traps · Migration notes (v8 → v9) · Go deeper

## When to use / when not to
- Use for any data grid where you own markup/styles: sorting, filtering, pagination, selection, grouping, pinning, resizing, cell selection/spanning (new in v9).
- Headless: no markup, no virtualization, no fetching. Pair with TanStack Virtual for large DOMs and TanStack Query for server data.
- Don't use for a static 10-row list with no interaction — a plain `<table>` is simpler.

## Packages
| Package | Role |
|---|---|
| `@tanstack/react-table` | React adapter (peer `react >=18`); depends on `@tanstack/table-core` + `@tanstack/react-store` |
| `@tanstack/react-table/legacy` | deprecated v8-style shim (`useLegacyTable`, `getCoreRowModel`, ...) |
| `@tanstack/react-table-devtools` | devtools panel (peer `@tanstack/react-devtools >=0.10`) |
| `@tanstack/{preact,vue,solid,svelte,angular,lit,ember,alpine,octane}-table` | other adapters; Svelte adapter is Svelte 5 runes only (Svelte 3/4 → stay on v8); Angular ≥19 signals |

```bash
npm install @tanstack/react-table
npm install -D @tanstack/react-devtools @tanstack/react-table-devtools   # optional
```
Packages are **ESM-only** (no CJS/UMD), target ES2022.

## Mental model
- `tableFeatures({...})` is the single registry for **features, row model factories, and fn registries** (`sortFns`, `filterFns`, `aggregationFns`). Only what you register is bundled and typed.
- The core row model is automatic. Feature APIs (e.g. `column.getToggleSortingHandler`) exist on the type only when the feature is registered.
- State lives in **TanStack Store atoms**: one atom per slice (`table.atoms.sorting`), a flat `table.store`, and `table.state` (what your `useTable` selector picked; default = all registered state).
- You own a slice via (a) nothing — internal, (b) `state.x` + `onXChange` (v8-style), or (c) `atoms: { x: myAtom }` (v9-preferred). Atom beats `state` beats `initialState`.
- `manual*` options mean "the data I pass is already processed"; the table never fetches.
- Row/cell/column/header methods live on prototypes — call them on the instance, never destructure.
- `TFeatures` is the first generic on every type: `ColumnDef<typeof features, Person>`.

## Core API
```tsx
import {
  createColumnHelper, createSortedRowModel, createPaginatedRowModel,
  rowSortingFeature, rowPaginationFeature, sortFns, tableFeatures, useTable,
} from '@tanstack/react-table'

type Person = { id: string; firstName: string; age: number }

// module scope = stable reference
const features = tableFeatures({
  rowSortingFeature,
  rowPaginationFeature,
  sortedRowModel: createSortedRowModel(),       // slot must follow its feature
  paginatedRowModel: createPaginatedRowModel(),
  sortFns,                                      // or { alphanumeric: sortFn_alphanumeric }
})

const columnHelper = createColumnHelper<typeof features, Person>()
const columns = columnHelper.columns([
  columnHelper.accessor('firstName', { header: 'First', cell: (info) => info.getValue() }),
  columnHelper.accessor('age', { header: 'Age', sortFn: 'alphanumeric' }), // v8: sortingFn
])

export function People({ data }: { data: Person[] }) {
  const table = useTable({
    key: 'people',            // only needed for devtools
    features,
    columns,
    data,                     // must be referentially stable
    getRowId: (row) => row.id,
    initialState: { pagination: { pageIndex: 0, pageSize: 25 } },
  })
  return (
    <table>
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id}>
            {hg.headers.map((header) => (
              <th key={header.id} colSpan={header.colSpan}
                  onClick={header.column.getToggleSortingHandler()}>
                {header.isPlaceholder ? null : <table.FlexRender header={header} />}
                {{ asc: ' ▲', desc: ' ▼' }[header.column.getIsSorted() as string] ?? null}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getAllCells().map((cell) => (   // getVisibleCells() needs columnVisibilityFeature
              <td key={cell.id}><table.FlexRender cell={cell} /></td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```
- Read state: `table.state.pagination` (render), `table.atoms.sorting.get()` (handlers, no subscription), `table.store.state` (full snapshot).
- Write state: `table.setSorting(...)`, `table.setPageIndex(0)`, `column.toggleVisibility()`, `row.toggleSelected()`; reset with `table.resetSorting()` / `resetPagination(true)` (blank default).
- `flexRender(def, ctx)` still works; `<table.FlexRender cell={cell} />` / `<FlexRender header={h} />` are the v9 form.
- Everything-included shortcut: `features: stockFeatures` (type `StockFeatures`) — v8-like, bigger bundle.
- Other adapters: same `tableFeatures`/feature names; entry point is `useTable` (Vue, Preact), `createTable` (Solid, Svelte), `injectTable` (Angular); app-hook variants `useAppTable` / `createAppTable` / `injectAppTable`.

## Patterns

### 1. Server-side (manual) pagination + sorting + filtering with TanStack Query
```tsx
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { PaginationState, SortingState } from '@tanstack/react-table'

const serverFeatures = tableFeatures({
  rowPaginationFeature, rowSortingFeature, columnFilteringFeature, globalFilteringFeature,
  // NO sorted/filtered/paginated row models: the server does the work
})

function ServerTable() {
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 10 })

  const q = useQuery({
    queryKey: ['people', { sorting, globalFilter, pagination }], // every server-owned slice
    queryFn: () => fetchPeople({ sorting, globalFilter, pagination }),
    placeholderData: keepPreviousData,
  })

  const table = useTable({
    features: serverFeatures,
    columns,
    data: q.data?.rows ?? EMPTY,          // EMPTY = module-scope [] (stable)
    rowCount: q.data?.rowCount,           // or pageCount; -1 = unknown (cursor APIs)
    getRowId: (row) => String(row.id),    // stable across pages
    state: { sorting, globalFilter, pagination },
    onSortingChange: (u) => { setSorting(u); setPagination((p) => ({ ...p, pageIndex: 0 })) },
    onGlobalFilterChange: (u) => { setGlobalFilter(u); setPagination((p) => ({ ...p, pageIndex: 0 })) },
    onPaginationChange: setPagination,
    manualPagination: true, manualSorting: true, manualFiltering: true,
  })
  // table.nextPage(), table.getCanNextPage(), table.getPageCount() all work from rowCount
}
```
Cursor APIs: `useInfiniteQuery`, pick `data.pages[pagination.pageIndex]`, pass `pageCount: -1` (guide/client-side-vs-server-side).

### 2. Row selection
```tsx
const selFeatures = tableFeatures({ rowSelectionFeature })
const selectColumn = {
  id: 'select',
  header: ({ table }) => (
    <input type="checkbox"
      checked={table.getIsAllRowsSelected()}
      ref={(el) => { if (el) el.indeterminate = table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected() }}
      onChange={table.getToggleAllRowsSelectedHandler()} />
  ),
  cell: ({ row }) => (
    <input type="checkbox" checked={row.getIsSelected()} disabled={!row.getCanSelect()}
      onChange={row.getToggleSelectedHandler()} />   // Shift-click range selection ON by default in v9
  ),
}
// options: getRowId (selection is keyed by row id!), enableRowSelection: (row) => row.original.age > 18,
// enableMultiRowSelection: false, enableSubRowSelection: false, enableRowRangeSelection: false
// read: table.getSelectedRowModel().rows  (only rows present in `data` under manualPagination)
```

### 3. Column sizing / resizing / pinning / visibility
```tsx
const gridFeatures = tableFeatures({
  columnSizingFeature, columnResizingFeature,   // resizing is its own feature now
  columnPinningFeature, columnVisibilityFeature,
})
const table = useTable({
  features: gridFeatures, columns, data,
  columnResizeMode: 'onChange',
  initialState: {
    columnPinning: { start: ['name'], end: ['actions'] },  // v8: left/right
    columnVisibility: { internalId: false },
  },
})
// sticky pinned cell style
const pinStyle = (column: Column<typeof gridFeatures, Person>): CSSProperties => {
  const pinned = column.getIsPinned()                     // 'start' | 'end' | false
  return {
    position: pinned ? 'sticky' : 'relative',
    insetInlineStart: pinned === 'start' ? `${column.getStart('start')}px` : undefined,
    insetInlineEnd: pinned === 'end' ? `${column.getAfter('end')}px` : undefined,
    width: column.getSize(),
    zIndex: pinned ? 1 : 0,
  }
}
// resize handle: <div onMouseDown={header.getResizeHandler()} onTouchStart={header.getResizeHandler()} />
// visibility toggle: <input type="checkbox" checked={column.getIsVisible()} disabled={!column.getCanHide()}
//                     onChange={column.getToggleVisibilityHandler()} />
// split regions: table.getStartHeaderGroups()/getCenterHeaderGroups()/getEndHeaderGroups(),
//                row.getStartVisibleCells()/getCenterVisibleCells()/getEndVisibleCells()
```

### 4. Grouping + aggregation + expanding
```tsx
const groupFeatures = tableFeatures({
  columnGroupingFeature, rowAggregationFeature, rowExpandingFeature,  // aggregation is separate in v9
  groupedRowModel: createGroupedRowModel(),
  expandedRowModel: createExpandedRowModel(),
  aggregationFns: { sum: aggregationFn_sum },
})
// column: { accessorKey: 'visits', aggregationFn: 'sum', aggregatedCell: ({ getValue }) => getValue() }
// table.setGrouping(['status']); groupedColumnMode: 'reorder' | 'remove' | false
// cell: cell.getIsGrouped() → expander button onClick={row.getToggleExpandedHandler()} + row.subRows.length
//       cell.getIsAggregated() → aggregated value; cell.getIsPlaceholder() → render null
// tree data: getSubRows: (row) => row.children ; getRowCanExpand for custom detail panels
```
Custom aggregation: `constructAggregationFn({ aggregate: ({ rows, getValue }) => ... })`; depth via column `maxAggregationDepth` (default `0` = direct children, `Infinity` = leaves).

### 5. Virtualized rows (Table + Virtual)
```tsx
const rows = table.getRowModel().rows
const rowVirtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => containerRef.current,   // container needs fixed height + overflow:auto
  estimateSize: () => 33,
  overscan: 5,
})
<tbody style={{ display: 'grid', height: rowVirtualizer.getTotalSize(), position: 'relative' }}>
  {rowVirtualizer.getVirtualItems().map((vr) => {
    const row = rows[vr.index]
    return (
      <tr key={row.id} data-index={vr.index} ref={(node) => rowVirtualizer.measureElement(node)}
          style={{ display: 'flex', position: 'absolute', width: '100%', transform: `translateY(${vr.start}px)` }}>
        {row.getVisibleCells().map((cell) => (   // needs columnVisibilityFeature + columnSizingFeature registered
          <td key={cell.id} style={{ display: 'flex', width: cell.column.getSize() }}>
            <table.FlexRender cell={cell} />
          </td>
        ))}
      </tr>
    )
  })}
</tbody>
```
Use `table { display: grid }`, sticky `thead { display: grid; position: sticky; top: 0 }`, `tr { display: flex }` — native table layout breaks with absolutely positioned rows. Columns: virtualize `table.getVisibleLeafColumns()` with `horizontal: true` and left/right spacer cells. After a server-side sort replaces data, `rowVirtualizer.scrollToIndex(0)`.

### 6. Fine-grained re-renders
```tsx
const table = useTable({ features, columns, data }, () => null)   // parent never re-renders on state
<table.Subscribe selector={(s) => s.pagination}>
  {(p) => <span>Page {p.pageIndex + 1}</span>}
</table.Subscribe>
// one slice: const sorting = useSelector(table.atoms.sorting)   // from @tanstack/react-store
// own a slice: const sortingAtom = useCreateAtom<SortingState>([]); useTable({ ..., atoms: { sorting: sortingAtom } })
```
Reusable setup: `createTableHook({ features, tableComponents, cellComponents, headerComponents })` → `useAppTable`, `createAppColumnHelper`, `table.AppTable/AppHeader/AppCell`, `useTableContext/useCellContext/useHeaderContext`. Partial shared options: `tableOptions({...})`.

## Traps
1. **Writing v8 code against v9.** `useReactTable`, `getCoreRowModel()`, `getSortedRowModel()` as table options → not exported from the main entry in 9.x (only from `/legacy`). Fix: `useTable` + `features: tableFeatures({...})` with `sortedRowModel: createSortedRowModel()` slots. (framework/react/guide/migrating)
2. **Feature APIs "missing".** `column.getToggleSortingHandler is not a function` / TS error on `table.atoms.rowSelection` → the feature wasn't registered. Registering only `sortedRowModel` without `rowSortingFeature` is a type error: slot must come after its feature. (framework/react/guide/table-state)
3. **String fn names don't resolve.** `sortFn: 'alphanumeric'` or `filterFn: 'includesString'` (and `'auto'`) only resolve functions present in the `sortFns`/`filterFns` registry slot. Register them (`{ alphanumeric: sortFn_alphanumeric }`) or pass the function directly. (migrating)
4. **Destructuring instance methods.** `const { getValue } = row` → `this` lost, throws. v9 methods are on prototypes; also `{...row}` / `JSON.stringify(row)` drop methods. Call `row.getValue('x')`. (migrating)
5. **`table.getState()` / `onStateChange` gone.** Use `table.state`, `table.store.state`, `table.atoms.<slice>.get()`; observe everything with `table.store.subscribe(fn)`. (migrating, table-state)
6. **Column pinning renamed with no aliases.** `left/right` → `start/end` everywhere: state, `column.pin('start')`, `getIsPinned() === 'start'`, `getLeftVisibleCells` → `getStartVisibleCells`, `getLeftTotalSize` → `getStartTotalSize`. `enablePinning` → `enableColumnPinning` / `enableRowPinning`. Use `insetInlineStart/End` CSS. (migrating)
7. **Resizing needs two features.** `columnSizingFeature` gives `getSize`; drag resizing additionally needs `columnResizingFeature`. State `columnSizingInfo` → `columnResizing`, `onColumnSizingInfoChange` → `onColumnResizingChange`. (migrating)
8. **Manual mode does not reset the page.** With manual server-side processing and no filtered/sorted row models, sort/filter changes do not run `autoResetPageIndex`; `manualPagination` disables it outright. Reset `pageIndex` in your `on*Change` handlers. (guide/client-side-vs-server-side)
9. **Server page + client sort = wrong.** Client-side sorting/filtering after server pagination only processes the loaded page. When the server paginates, it must also sort/filter/group. (client-side-vs-server-side)
10. **Unstable `data`/`columns`.** `data={q.data?.rows ?? []}` inline creates a new array every render → row model rebuilds and auto-resets. Use a module-scope empty array, `useMemo`, or React Compiler. (react-compiler)
11. **React Compiler + stable row objects.** v9 keeps `row`/`column`/`cell` references stable, so a compiled child `<SelectionCell row={row} />` can be skipped and show stale `row.getIsSelected()`. Subscribe inside the child: `<Subscribe source={row.table.atoms.rowSelection} selector={(s) => s[row.id]}>`. (framework/react/guide/react-compiler)
12. **Selector hides state.** Passing `() => null` or a narrow selector to `useTable` means JSX reading other slices won't update — wrap those reads in `table.Subscribe`. (migrating)
13. **Select-all indeterminate stuck on.** v9 `getIsSomeRowsSelected()` is true whenever ≥1 row is selected (v8: some-but-not-all). Use `getIsSomeRowsSelected() && !getIsAllRowsSelected()`. Shift range selection is now default on `getToggleSelectedHandler()` (`enableRowRangeSelection: false` to opt out). (migrating)
14. **Selection keyed by index.** Default row id is the index; with server pages/sorting the selection points at different records. Always set `getRowId`. (row-selection)
15. **Aggregation without the feature.** `aggregationFn`/`aggregatedCell` need `rowAggregationFeature` (separate from `columnGroupingFeature` in v9). Custom aggregators use `constructAggregationFn`; `column.getAggregationValue({ rows, maxDepth })` takes an object. (migrating, grouping)
16. **Generics.** `ColumnDef<Person>` / `createColumnHelper<Person>()` → missing `TFeatures`. Use `ColumnDef<typeof features, Person>`. Meta augmentation now `ColumnMeta<TFeatures, TData, TValue>`, or per-table `columnMeta: metaHelper<...>()` slot. `RowData` must be a record or array. (migrating)
17. **Devtools silently skip a table.** Registration requires the `key` option; without it devtools log `Missing table key` and ignore it. (devtools)
18. **Same slice owned twice.** Putting `pagination` in both `initialState` and `state`/`atoms` → controlled wins, initial ignored. `table.reset()` does not clear external atoms. (pagination, table-state)
19. **`row.getVisibleCells()` / `table.getVisibleLeafColumns()` without `columnVisibilityFeature`.** In v9 they belong to the visibility feature, so with only sorting/pagination registered they are type errors. Use `row.getAllCells()` / `table.getAllLeafColumns()`, or register `columnVisibilityFeature`. Header groups (`table.getHeaderGroups()`) are core. (verified against table-core 9.2.6 types)

## Migration notes (v8 → v9)
| v8 | v9 |
|---|---|
| `useReactTable(opts)` | `useTable(opts, selector?)` |
| all features implicit | `features: tableFeatures({...})` (or `stockFeatures`) |
| `getCoreRowModel: getCoreRowModel()` | removed (automatic) |
| `getSortedRowModel: getSortedRowModel()` | `sortedRowModel: createSortedRowModel()` in `tableFeatures` |
| `getFilteredRowModel` / `getPaginationRowModel` / `getExpandedRowModel` / `getGroupedRowModel` | `filteredRowModel: createFilteredRowModel()` / `paginatedRowModel: createPaginatedRowModel()` / `expandedRowModel: createExpandedRowModel()` / `groupedRowModel: createGroupedRowModel()` |
| `getFacetedRowModel` / `MinMaxValues` / `UniqueValues` | `facetedRowModel` / `facetedMinMaxValues` / `facetedUniqueValues` slots (`create*`) |
| `sortingFns`, `sortingFn`, `SortingFn`, `column.getSortingFn()` | `sortFns`, `sortFn`, `SortFn`, `column.getSortFn()` |
| `declare module` `FilterFns`/`FilterMeta` | `filterFns: { fuzzy }` + `filterMeta: metaHelper<...>()` slots |
| `table.getState()` | `table.state` / `table.store.state` / `table.atoms.x.get()` |
| `onStateChange` | removed; `table.store.subscribe` |
| `columnPinning.left/right`, `pin('left')` | `columnPinning.start/end`, `pin('start')` |
| `getLeft*/getRight*` pinning APIs | `getStart*/getEnd*` |
| `enablePinning` | `enableColumnPinning` + `enableRowPinning` |
| `columnSizingInfo`, `setColumnSizingInfo`, `onColumnSizingInfoChange` | `columnResizing`, `setColumnResizing`, `onColumnResizingChange` (+ `columnResizingFeature`) |
| aggregation inside grouping | `rowAggregationFeature`; `column.getAggregationFn()` → `getAggregationFns()` |
| `(columnId, leafRows, childRows) => ...` aggregator | `constructAggregationFn({ aggregate, merge? })` |
| `createColumnHelper<TData>()` | `createColumnHelper<TFeatures, TData>()`; `columnHelper.columns([...])` |
| `Table<TData>`, `Row<TData>`, `ColumnDef<TData>` | `Table<TFeatures, TData>`, `Row<TFeatures, TData>`, `ColumnDef<TFeatures, TData, TValue>` |
| `row._getAllCellsByColumnId()` | `row.getAllCellsByColumnId()`; other `_` APIs removed |
| CJS/UMD builds | ESM only |
| incremental path | `useLegacyTable` from `@tanstack/react-table/legacy` (deprecated, all features) |

## Go deeper
- `tanstack doc table framework/react/guide/migrating` — full v8→v9 guide
- `tanstack doc table framework/react/quick-start` — first v9 table
- `tanstack doc table framework/react/guide/table-state` — atoms, store, controlled state
- `tanstack doc table guide/client-side-vs-server-side` — manual mode, Query, cursors
- `tanstack doc table framework/react/guide/pagination` — pagination options
- `tanstack doc table framework/react/guide/row-selection` — selection, range, sub-rows
- `tanstack doc table framework/react/guide/column-pinning` — start/end pinning APIs
- `tanstack doc table framework/react/guide/grouping` — grouping + expanding
- `tanstack doc table framework/react/guide/virtualization` — Table + Virtual patterns
- `tanstack doc table framework/react/guide/react-compiler` — Subscribe in nested components
- `tanstack doc table framework/react/guide/composable-tables` — createTableHook
- `tanstack doc table framework/react/guide/use-legacy-table` — v8 shim
- `tanstack doc table devtools` — devtools setup
