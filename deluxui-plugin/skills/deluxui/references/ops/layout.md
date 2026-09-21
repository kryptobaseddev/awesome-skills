# layout — composition, rhythm and where the eye lands

Layout is priority made visible. State the priority first, in words, and the
arrangement becomes a consequence rather than a preference.

Derived from impeccable's `layout` (Apache-2.0) — see NOTICE.md.

## State the priority before arranging anything

LAY-001 is the rule and `M-JUDGE-CONTENT-PRIORITY` is the question:

> State the content priority for one screen in order, before looking at the
> layout. Then check the narrowest supported width: are the primary task and its
> essential context both still reachable?

Write that order down. A layout argued from a list is checkable; a layout argued
from balance is not.

## The moves, in the order that pays

1. **Space carries grouping.** Proximity does more work than a border and costs
   nothing (LAW-14 / uniform connectedness). Reach for a divider only when
   proximity genuinely cannot say it.
2. **One grid, declared.** `grid.columns`, `gutter_px` and `container_max_px` go
   in the contract. A second implicit grid is how alignment drifts.
3. **Rhythm, not uniformity.** A page where every section is the same height and
   density has no shape. `S-CRAFT-RHYTHM` measures the monotony; varying the
   pace is what makes one section read as the peak.
4. **Alignment survives real content.** The long label and the large text size
   at the same time — that is `M-JUDGE-ALIGNMENT`, and it is where hand-tuned
   layouts come apart.
5. **Density is a task decision.** An oversized consumer layout on a data-heavy
   screen wastes the operator's day (VIS-009). Load a representative number of
   real records, not three.

## Responsive is not a separate job

Do it here, not later. 320px is the floor (NUM-009), `dvh`/`svh` rather than
`100vh` (LAY-005), no `overflow-x: hidden` masking a real overflow, and a table
that has a narrow fallback (LAY-006). On native, AND-001 makes this explicit: a
phone bottom bar shipped unchanged to a tablet is the same failure with a
platform name.

## Verify

| Detector | What it settles |
|---|---|
| `S-CRAFT-RHYTHM` | Section pacing varies rather than repeating. |
| `S-RESP-FIXEDPX`, `S-RESP-VH`, `S-RESP-TABLE` | Fixed widths, viewport units, tables. |
| `S-TOKEN-ARBITRARY` | Spacing is on the declared scale (NUM-017). |
| `R-REFLOW` | Real overflow and clipping at 320, 390, 768, 1024, 1440. |
| `R-STICKY-OBSTRUCTION` | Fixed chrome that covers a focused control (NUM-011). |
| `M-JUDGE-CONTENT-PRIORITY`, `M-JUDGE-ALIGNMENT`, `M-JUDGE-DENSITY` | The three judgements no scan settles. |

Hand off to [polish.md](polish.md).
