# React, Next.js, Tailwind, shadcn, Radix, Base UI

The stack most of this skill's checks were tuned against.

## Tailwind v3 vs v4 — check before you advise

```bash
python3 scripts/ux_check.py <project> --signals    # reports tailwind_major
```

The checks branch on this, and so should you.

| | v3 | v4 |
|---|---|---|
| Config | `tailwind.config.js` | CSS-first: `@import "tailwindcss"` + `@theme { }` |
| Palette | hex | **OKLCH** `--color-*` theme variables |
| `outline-none` | transparent 2px outline; stays visible in forced colors | **`outline-style: none`** — genuinely removes it |
| Old `outline-none` behaviour | — | renamed `outline-hidden` |
| Default ring width | 3px | **1px** — state the width explicitly |
| Container queries | plugin | built in: `@container`, `@sm:`, `@max-md:` |
| Spacing scale | fixed steps | dynamic from `--spacing`; `p-17` works |
| Renamed | — | `shadow-sm`→`shadow-xs`, `flex-shrink-*`→`shrink-*`, `overflow-ellipsis`→`text-ellipsis` |

Colours are never guessed. The checks read `node_modules/tailwindcss/theme.css` and
your `@theme` block; a class that cannot be resolved reports NOT_RUN rather than a
fabricated contrast verdict.

Focus, written for v4:

```html
<button class="outline-hidden focus-visible:ring-2 focus-visible:ring-offset-2">
```

## Primitives — compose, do not rebuild

| Library | Package |
|---|---|
| Radix UI | `@radix-ui/react-*` |
| Base UI | `@base-ui/react` — from the Radix, Floating UI and MUI teams; where shadcn is heading |
| Headless UI | `@headlessui/react` |
| Ark UI | `@ark-ui/react` |
| React Aria | `react-aria-components` |

If one of these is installed, `S-DS-REINVENT` flags a hand-written Dialog, Dropdown,
Tooltip, Select, Combobox, Tabs or Accordion. That is COMP-001, not a preference:
focus containment, typeahead, collision-aware positioning and the ARIA relationships
are genuinely hard, and these libraries have already got them right.

**shadcn/ui is your code.** It is copied into `components/ui/`, so its defects are
yours to fix — but check whether a component already exists there before adding one,
and change it in place rather than forking a variant next to it.

## React specifics

- `useOptimistic` and `onMutate` need a rollback path. Without one, a failed delete
  leaves the row visibly gone (STATE-004, STATE-005).
- `useActionState` / form actions still need an in-flight guard; a double submit is
  two requests.
- A Suspense boundary is a loading state only if its fallback reserves the right
  space. A boundary that collapses to nothing is measured as layout shift.
- Error boundaries catch render errors, not rejected fetches. Both need a path.
- `next/image` needs `alt`, and `width`/`height` or `fill` with a sized parent.
- Server Components: the pending state lives in the client boundary. Check it exists.

## Motion

Framer Motion / `motion` respects `useReducedMotion()` only if you call it. The
`motion-reduce:` variant covers CSS transitions, not JS-driven animation. `S-MOTION-REDUCE`
checks the file; `R-MOTION` emulates the preference and reports what still moves.
