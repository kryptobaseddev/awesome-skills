# TanStack Charts

> Verified 2026-10-07 against `@tanstack/charts@1.0.0` docs (TanStack CLI 0.71.1). Re-check with `tanstack doc charts <path>` when the installed major differs.

New library (1.0.0 published 2026-10-03). It is **not** the old `react-charts` package and LLM memory of either is unreliable — read the docs/types before writing code. The online docs track unreleased `main`; for the exact 1.0.0 surface use the tag `https://github.com/TanStack/charts/tree/v1.0.0/docs`.

## When to use / when not to
- Use for typed, declarative charts in TS apps: line/area/bar/dot/rect/cell/box/rule/text, facets, polar (pie/donut/radar), geo, hierarchy, networks — SVG by default, Canvas opt-in per mark, SSR-able.
- Grammar-of-graphics (Observable Plot-like): compose **marks** over shared **scales**; no "series" model, no monolithic `<LineChart>` component.
- Not a data layer: fetching, cleaning, filtering, memoization stay in your app. No dashboard widgets.

## Packages
| Package / entry | Role |
|---|---|
| `@tanstack/charts` | **the only package to install**: core, marks, transforms, all adapters as subpaths |
| `@tanstack/charts/react` | React `Chart` (React/React DOM 18 or 19) |
| `@tanstack/charts/react/tooltip` | `Chart`/`CanvasChart`/`RendererChart` that accept `renderTooltipBody` |
| `@tanstack/charts/react/canvas`, `/react/core` | Canvas chart; app-supplied renderer |
| `@tanstack/charts/{vue,solid,svelte,angular,preact,lit,alpine,octane,react-native}` | other adapters (React Native experimental, via `react-native-svg`) |
| `@tanstack/charts/scales/{linear,band,point,ordinal}` | compact scales (no `/scales` barrel) |
| `@tanstack/charts/tooltip`, `/canvas`, `/polar`, `/geo`, `/view`, `/legend`, `/selection`, `/interaction/{brush,zoom,cursor}`, `/transform/*` | opt-in capabilities |
| `@tanstack/react-charts@1.0.0` | compatibility re-export of `@tanstack/charts/react`; new apps should not use it |
| `d3-scale` (+ `@types/d3-scale`) | only when you need time/UTC/log/pow/sequential/... scales |

```bash
npm install @tanstack/charts            # + react react-dom for the React adapter
npm install d3-scale && npm install -D @types/d3-scale   # only if a chart needs scaleUtc etc.
```
Framework peers are optional at the package level; install only the ones for your adapter. Never install the `d3` umbrella package.

## Mental model
- `defineChart({ marks, scales, ... })` → a framework-independent **definition**. Adapters only mount it.
- **Marks** (`lineY`, `barY`, `dot`, `areaY`, `ruleY`, `text`, `cell`, ...) each take their *own* data + channel options. Array order = paint order.
- **Channels** map fields or accessors to visuals: `x`, `y`, `z` (series/group), `color` (scaled), `fill`/`stroke` (literal paint), `r`, `key`. Field names are type-checked against the row type.
- **Scales** live in a registry: `scales: { x: {...}, y: {...} }` — both reserved entries are required (`null` if unused). Pass a factory (`scaleLinear`) to infer the domain, `() => scaleBand().padding(0.2)` to configure, or an instance when the domain is app state. Never set a pixel range — Charts owns it.
- **Transforms** (`groupBy`, `binX`, `fold`, `normalize`, `rollingWindow`, `stackRowsY`, ...) are eager plain functions: rows in, typed rows out, with lineage (`source`).
- **Layout**: bars stack by default; `layout: group()` for side-by-side.
- **Views**: `composeViews` / `grid` / `layer` / `inset` from `@tanstack/charts/view` combine whole definitions; `facet`/`facetChart` for small multiples.
- **Definition identity is the update boundary**: a new definition object rebuilds the scene.

## Core API (React)
```tsx
import { useMemo } from 'react'
import { barY, defineChart, group } from '@tanstack/charts'
import { scaleBand } from '@tanstack/charts/scales/band'
import { scaleLinear } from '@tanstack/charts/scales/linear'
import { tooltip } from '@tanstack/charts/tooltip'
import { Chart } from '@tanstack/charts/react'

type Row = { quarter: string; product: string; revenue: number }

export function RevenueChart({ rows, grouped }: { rows: Row[]; grouped: boolean }) {
  const definition = useMemo(
    () =>
      defineChart({
        marks: [
          barY(rows, {
            x: 'quarter',
            y: 'revenue',
            color: 'product',                 // stacks by default
            ...(grouped ? { layout: group() } : {}),
          }),
        ],
        scales: {
          x: { scale: () => scaleBand().padding(0.18) },
          y: { scale: scaleLinear, nice: true, grid: true, axis: { label: 'Revenue' } },
        },
        tooltip,                              // optional built-in tooltip
      }),
    [rows, grouped],
  )

  return (
    <Chart
      definition={definition}
      height={320}                            // width follows the container
      ariaLabel="Revenue by quarter"          // required
      onSelect={(point) => point && console.log(point.datum.product, point.yValue)}
    />
  )
}
```
`Chart` props: `definition`, `ariaLabel` (required), `ariaDescription`, `height` (default 320), `width`, `aspectRatio`, `initialWidth` (default 640, used for SSR), `className`, `style`, `tabIndex`, `onFocusChange`, `onFocusGroupChange`, `onSelect`, `onRender`, `idPrefix`, `renderSvg`, `measureText`.
Vanilla: `const host = mountChart(el, { definition, height, ariaLabel })` → `host.update({...})` → `host.destroy()`. Server/static: `createChartScene(def, { width, height })`, `renderChartSvg` (`@tanstack/charts/svg`).
Other adapters consume the same definition; import `Chart` from `@tanstack/charts/<framework>`.

## Patterns
```ts
// Time series: upgrade only the x scale to D3
import { scaleUtc } from 'd3-scale'
defineChart({
  marks: [lineY(rows, { x: 'date', y: 'value', z: 'region' })],   // z = one line per region
  scales: { x: { scale: scaleUtc, nice: true }, y: { scale: scaleLinear, nice: true } },
})

// Layering: line is visual only, dots own focus/tooltips
import { decorative } from '@tanstack/charts/mark/decorative'
const marks = [decorative(lineY(rows, { x: 'date', y: 'value' })), dot(rows, { x: 'date', y: 'value' })]

// Aggregate in app code, then plot
import { groupBy } from '@tanstack/charts/transform/group'
const byRegion = groupBy(orders, { by: 'region', outputs: { revenue: { value: 'amount', reduce: 'sum' } } })

// Stable category colors across charts
import { scaleOrdinal } from '@tanstack/charts/scales/ordinal'
defineChart({ marks, scales, color: { scale: scaleOrdinal(['A', 'B'], ['#2563eb', '#f97316']) } })

// Canvas for one dense mark only
import { canvasChartRenderer } from '@tanstack/charts/canvas'
areaY(dense, { x: 'date', y1: 'low', y2: 'high', renderer: canvasChartRenderer })

// Custom React tooltip body: switch the import
import { Chart } from '@tanstack/charts/react/tooltip'
<Chart definition={def} ariaLabel="..." renderTooltipBody={({ defaultBody, pinned, dismiss }) => (
  <>{defaultBody}{pinned ? <button onClick={dismiss}>Close</button> : null}</>
)} />
```

## Traps
1. **Writing old `react-charts` code.** `import { Chart } from 'react-charts'` with `options={{ data, primaryAxis, secondaryAxes }}` and `getValue` axes is the unrelated v3-beta `react-charts` package (last published 2023). TanStack Charts uses `defineChart` + marks + `scales`. (overview)
2. **Installing `@tanstack/react-charts` for a new app.** It is a compatibility package; import from `@tanstack/charts/react` (and `@tanstack/charts/scales/*`, not `@tanstack/charts-scales/*`). (guides/migrating)
3. **Root `x`/`y` scale options.** Pre-Alpha definitions put `x: {...}` at the definition root; now they must be under `scales.x` / `scales.y`, and both are required (`null` when unused). A missing scale is an error, not a fallback. (guides/migrating, installation)
4. **Importing `scaleUtc`/`scaleLog` from Charts.** Compact scales are only linear/band/point/ordinal. Time and nonlinear scales come from `d3-scale`, which your app must depend on directly (transitive deps are not an import contract). (concepts/scales-and-d3)
5. **Band scale for dates.** `scaleBand` treats dates as categories (Friday and Monday adjacent). Use `scaleUtc`/`scaleTime` when elapsed time matters. (concepts/scales-and-d3)
6. **Mutating data in place / inline definitions.** Updates happen only when the definition identity changes. Mutating `rows` does nothing; building `defineChart` inline every render rebuilds the scene every render. Module-scope definitions for static charts, `useMemo` over the captured values otherwise. (framework/react/adapter, guides/dynamic-data-and-animation)
7. **Bars stacking unexpectedly.** Multiple bars per category stack by default; side-by-side needs `layout: group()`. (concepts/data-and-channels)
8. **`fill` vs `color`.** `color` goes through the color scale/legend; `fill`/`stroke` bypass it. Use `color` (or `z`) for series semantics. (concepts/data-and-channels)
9. **Casting to silence types.** Field channels are type-filtered (numeric length accepts numeric fields only). Fix the row type or use an accessor instead of `as any`; don't add component generics. (concepts/data-and-channels, framework/react/quick-start)
10. **Accessor signature changed.** `(datum, index, data) => v` → `(datum, { index, data }) => v`; the same "context object" change applies to facet builders, focus, legend, selection callbacks. (guides/migrating)
11. **`renderTooltipBody` on the base `Chart`.** Only the `@tanstack/charts/react/tooltip` entry accepts it. (framework/react/quick-start)
12. **Polar/geo from the root.** `polar`, `radialArc`, `pie`, `geoShape` live at `@tanstack/charts/polar` / `@tanstack/charts/geo`. (installation)
13. **Hidden container / SSR width.** Before measurement the scene uses `initialWidth` (640); set it for deterministic server output. (framework/react/adapter)

## Migration notes
| Previous | Current |
|---|---|
| `react-charts` (`<Chart options={{ data, primaryAxis, secondaryAxes }} />`) | `@tanstack/charts` grammar — rewrite, no 1:1 mapping |
| `@tanstack/react-charts` | `@tanstack/charts/react` |
| `@tanstack/react-charts/<capability>` | `@tanstack/charts/react/<capability>` |
| `@tanstack/charts-scales/<family>` | `@tanstack/charts/scales/<family>` |
| `@tanstack/<framework>-charts` | `@tanstack/charts/<framework>` |
| root `x` / `y` options | `scales.x` / `scales.y` (+ `axis`, `axis.ticks`, `axis.tickLabels`) |
| `(datum, index, data)` accessors | `(datum, { index, data })` |
| facet `chart(data, key)` | `chart(data, { key })` |
| 0.x Alpha (minor = may break) | 1.0+: semver compatibility contract |

## Go deeper
- `tanstack doc charts overview` — concepts, ownership
- `tanstack doc charts installation` — subpaths, peers, D3 boundary
- `tanstack doc charts framework/react/quick-start` — React chart
- `tanstack doc charts framework/react/reference/chart` — every `Chart` prop
- `tanstack doc charts framework/react/adapter` — lifecycle, SSR, sizing
- `tanstack doc charts concepts/data-and-channels` — channels, z, color
- `tanstack doc charts concepts/marks-and-layering` — mark catalog
- `tanstack doc charts concepts/scales-and-d3` — compact vs D3 scales
- `tanstack doc charts reference/transforms` — groupBy, bin, fold
- `tanstack doc charts guides/migrating` — import + API moves
- `tanstack doc charts guides/ai-authoring` — agent authoring sequence
