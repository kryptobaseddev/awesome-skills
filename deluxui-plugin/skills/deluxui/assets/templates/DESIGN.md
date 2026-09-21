# Design system

What this interface is made of. The source of truth is the code; this file is the map
to it. **`DESIGN.md` wins on visual decisions, `PRODUCT.md` wins on strategic ones** —
and both lose to a safety or accessibility rule.

## Stack

Framework and version, styling approach, Tailwind major version if any, headless
primitive library if any, icon set, chart library, motion library.

## Tokens

Where they are defined (`@theme` block, `tailwind.config`, `:root`) and what the
semantic roles are — not every raw value, just the roles and where to find them:

```
canvas · surface · elevated-surface · text · muted-text · border · interactive
focus · success · warning · danger · selected · disabled
```

Note the colour space. Tailwind v4 defaults are OKLCH; mixing a hex override into an
OKLCH ramp produces a step that looks wrong and nobody can explain.

## Type

The roles in use — display, page title, section title, body, label, caption, numeric,
code — with the family and scale. Note if numerals are tabular anywhere they are
compared in a column.

## Spacing and radius

The scale and its base unit. Note any deliberate exceptions, so they read as decisions
rather than drift.

## Elevation

How depth is expressed: borders, shadow, or both. Pick one metaphor. An element with a
1px border *and* a wide soft shadow is two systems arguing.

## Themes

Which modes are supported, and how they are switched. Dark mode is not an inverted
light theme — it needs its own contrast and saturation decisions.

## Motion

Default durations and easing, what is allowed to animate, and how
`prefers-reduced-motion` is honoured. Include View Transitions if used; they animate
by default and people forget they are animation at all.

## Density

Comfortable or compact, and where each applies. A data table and a marketing page do
not want the same density, and forcing one on the other is how dashboards end up
showing four rows.

## Component inventory

| Component | Path | Status |
|---|---|---|
| Button | `src/components/ui/button.tsx` | canonical |
| … | | canonical / legacy / deprecated |

This is what `--inventory` searches and what the preserve ladder consults. Keeping it
current is what stops the fourth Button appearing.

## Do and do not

Project-specific rules a newcomer would otherwise get wrong.
