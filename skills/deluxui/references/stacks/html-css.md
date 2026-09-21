# Plain HTML and modern CSS

No framework means no framework getting in the way. The platform now does most of
what component libraries were invented for.

## Use the platform

| Need | Platform answer |
|---|---|
| Modal | `<dialog>` + `showModal()` — top layer, `::backdrop`, Escape, focus containment |
| Non-modal overlay | `popover` attribute + `popovertarget` |
| Anchored positioning | `anchor-name` / `position-anchor` |
| Disclosure | `<details>` / `<summary>` |
| Background inert while modal is open | `inert` attribute |
| Validation after interaction | `:user-invalid` / `:user-valid` — **not** `:invalid` |
| Auto-growing textarea | `field-sizing: content` |
| Animating to `height: auto` | `interpolate-size: allow-keywords` |
| Entry animation | `@starting-style` + `transition-behavior: allow-discrete` |

`:invalid` matches before the user has typed anything, so a required empty field
renders as an error on first paint. That is FORM-005, and `:user-invalid` is the fix.

## Modern CSS worth reaching for

- `light-dark()` with `color-scheme` — one declaration instead of two theme blocks.
- `oklch()` for perceptually even ramps; `color-mix()` for derived tints that stay in
  the same space.
- Relative colour syntax: `oklch(from var(--brand) calc(l - 0.1) c h)`.
- `@container` before `@media`. A component keyed to its container survives reuse; one
  keyed to the viewport does not.
- `:has()` for parent-conditional styling — it removes most wrapper-class hacks.
- `text-wrap: balance` for headings, `pretty` for body copy.
- `scrollbar-gutter: stable` to stop layout jumping when a scrollbar appears.
- `@layer` to make cascade order explicit instead of accidental.
- `subgrid` when nested items must align to a parent's tracks.
- `content-visibility: auto` for long off-screen lists.

## Still on you

The platform gives you mechanics, not judgement. You still owe: a visible
`:focus-visible` style on every interactive element, a reduced-motion query around
anything that moves (including View Transitions, which animate by default), a
`lang` attribute, landmarks and headings in a sensible order, a skip link, and states
for empty, loading, error and offline.

`dvh` over `vh`. `svh` when you need the smallest stable height.
