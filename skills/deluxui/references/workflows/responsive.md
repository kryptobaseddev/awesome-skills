# responsive — layout, reflow and phone ergonomics

Mostly a runtime mode. Source can tell you a width is fixed; only a browser can tell
you what actually overflows.

```bash
bash scripts/ux_browser.sh <url> --routes <routes> \
     --viewports 320,390,768,1024,1440 --out .deluxui/reports/runtime
```

`R-REFLOW` reports the narrowest viewport where the page scrolls sideways and names
the elements sticking out. `R-ZOOM` applies 200% text and `R-TEXTSPACING` applies the
SC 1.4.12 overrides, then look for content that got clipped or pushed off screen —
both are about surviving a user's own settings, not your breakpoints.

Screenshots land in the output directory. Look at them. A layout can satisfy every
measurement and still be unusable.

## What usually breaks

| Symptom | Cause |
|---|---|
| Sideways scroll at 320px | A fixed pixel width, a long unbroken string, or a table with no scroll region |
| Footer under the URL bar on a phone | `100vh` / `h-screen`. Use `dvh`, or `svh` for the smallest stable height |
| A bottom bar under the home indicator | No `env(safe-area-inset-bottom)` |
| Text clipped at 200% | A fixed height on a text container |
| Fine on desktop, unusable on phone | Density chosen for one viewport; hit areas under 44px |
| The keyboard covers the field being typed into | A sticky footer plus no scroll-into-view on focus |

## Modern tools, in preference order

**Container queries** before media queries. A component that responds to its own
container works in a sidebar, a modal and a full-width page without knowing which it
is in; a component keyed to viewport width breaks the moment it is reused. Tailwind
v4 ships `@container` and the `@sm:`/`@max-md:` variants.

Then: intrinsic sizing (`min()`, `max()`, `clamp()`), `text-wrap: balance` for
headings and `pretty` for body, and `subgrid` when nested items must align to a
parent track.

## Narrow viewports are not touch-only

A 320px viewport might be a desktop window at 400% zoom. Keep keyboard access and
visible focus at every width (LAY-009). Conversely a wide viewport may well be a
touchscreen — do not make hover the only route to anything, at any size.
