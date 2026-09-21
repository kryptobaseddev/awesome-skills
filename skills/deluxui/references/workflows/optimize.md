# optimize — perceived and measured performance

Two different things, deliberately kept apart. A spinner is not performance; it is an
apology for its absence.

```bash
bash scripts/ux_browser.sh <url> --routes <routes> --api '**/api/**'
```

`R-VITALS` reports LCP, CLS, INP, FCP and TTFB — and reports **NOT_RUN** regardless
of the numbers. That is deliberate: NUM-012 is a field metric at the 75th percentile
across real users and devices, and one run on a developer machine on a fast network
cannot establish it either way. Use the lab numbers to find problems, never to claim
a pass.

## Perceived performance

| Budget | Rule |
|---|---|
| ~100ms | Acknowledge the input. Something must visibly change. |
| ~1s | A persistent pending state, not just a cursor. |
| ~10s | Stage information and a way out. |

Acknowledgement is not completion. Showing success before the server confirms it is
STATE-002, and on a payment or a deletion it is STATE-005 — the user acts on a result
that may not exist.

Never delay a fast result so an animation can finish.

## Layout shift

The cheapest win here and the one most often skipped. Reserve space for anything that
arrives late: images with `width`/`height` or `aspect-ratio`, fonts with
`font-display: optional` or a metric-matched fallback, ad and embed slots, and
skeletons that match the real content's box rather than a generic grey bar.

`S-PERF-IMGDIM` finds images with no intrinsic size; `R-VITALS` reports the resulting
CLS.

## Cost the interface causes

- Continuously rendering 3D canvases. `frameloop="demand"` and a `dpr` cap — see
  `stacks/three-3d.md`.
- Animating anything other than `transform` and `opacity`.
- Large `backdrop-filter` surfaces, which are expensive on low-end devices and are
  usually decorative anyway.
- Loading the whole icon set for six icons.

## What this mode is not

Bundle analysis and build configuration are a different job. Stay on what the user
experiences: responsiveness, stability and honest status. If the fix is genuinely a
build concern, say so and hand it over.
