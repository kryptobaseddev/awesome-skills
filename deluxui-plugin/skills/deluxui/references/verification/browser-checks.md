# The runtime tier: measuring instead of reading

```bash
bash scripts/ux_browser.sh <base-url> \
  --routes /,/settings --api '**/api/**' \
  --viewports 320,390,768,1024,1440 --out .deluxui/reports/runtime
```

Needs the `agent-browser` CLI and a running app. Without it the script writes a
report marking every runtime rule NOT_RUN with that reason and exits `3` — it does
not quietly skip them.

**Pass `--api`.** It is a glob against request URLs (`'**/api/**'`, `'**/rest/v1/**'`
for Supabase, `'**/graphql'`). Without it the three forced-state probes never run, and
those find more real defects than everything else here combined.

## The probes

| Detector | What it actually does | Rules |
|---|---|---|
| `R-REFLOW` | Sets each viewport, compares `scrollWidth` to the client width, names the elements extending past the edge | NUM-009, NUM-019, LAY-002 |
| `R-TARGET` | Measures every interactive element's real box; for anything under 24px, tests whether a 24px circle on it clashes with a neighbour (the SC 2.5.8 spacing exception). NUM-006/007 are iOS pt and Android dp and cannot be established from a browser — they stay manual | NUM-004 |
| `R-TARGET-COARSE` | The 44px coarse-pointer default — a PROJECT choice, not a standard | NUM-005 |
| `R-CONTRAST` | Walks every visible text node, composites through transparent ancestors to the real painted backdrop, applies the large-text rule by rendered size and weight | NUM-001, NUM-002, NUM-003 |
| `R-FOCUS-WALK` | Focuses each control and diffs its computed style before and after; counts backward jumps in reading order; finds positive tabindex | A11Y-002/003/004, NUM-011, LAY-003 |
| `R-ZOOM` | Applies 200% root font size, looks for clipped or displaced content | NUM-008 |
| `R-TEXTSPACING` | Injects the SC 1.4.12 overrides, looks for the same | NUM-010 |
| `R-MOTION` | Emulates `prefers-reduced-motion`, reloads, reports what still animates | LAY-010, A11Y-010 |
| `R-VITALS` | LCP, CLS, INP, FCP, TTFB | NUM-012 |
| `R-CONSOLE` | Uncaught page errors during a normal visit | STATE-001 |
| `R-STATE-ERROR` | **Aborts** matching requests, reloads, asks whether the page says what failed and offers a way on | STATE-001, STATE-006, UX-009 |
| `R-STATE-EMPTY` | Returns `[]`, asks whether the empty state exists and offers a first action | UX-001, COMP-017 |
| `R-STATE-OFFLINE` | Goes offline, asks the same | STATE-008, UX-001 |

## Reading the focus result

`R-FOCUS-WALK` is the one people distrust and should not. It focuses the element and
compares outline, box-shadow, background, colour and border before and after. If
nothing changed, nothing changed — that control is invisible when focused, no matter
what the stylesheet appears to say. It is the only reliable way to catch a focus ring
that is technically present and visually absent.

## Reading the vitals result

`R-VITALS` reports **NOT_RUN** whatever the numbers say. NUM-012 is a field metric at
the 75th percentile across real users, devices and networks; one run on a developer
machine cannot establish it in either direction. Use the numbers to find problems.
Never use them to claim a pass — that is the exact substitution GOV-006 prohibits.

## Reading the forced states

The three failures it reports most often:

- **`stuck_spinner`** — the request died and the spinner is still turning. The user
  waits forever for something that already failed.
- **`looks_blank`** — the region emptied with no explanation. Indistinguishable from
  "you have no data".
- **failure shown, no recovery** — it says something went wrong and offers no way on.

A `PASS` here means the interface said what happened *and* offered a next step. Both.

## Honestly not implemented

`R-AXE` (needs axe-core in the project), `R-STATE-SLOW`, `R-PIXEL-CONTRAST`,
`R-BASELINE-DIFF` (needs a baseline captured first) and `R-FORCED-COLORS` are declared
and report NOT_RUN with their specific reason. They are listed rather than omitted so
the gap is visible in the matrix instead of disappearing from it.
