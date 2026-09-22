# Preserve first

The most expensive thing an agent does to a mature product is redesign it while
fixing something small. It happens because generating a new component is easier than
reading the existing one, and because "improve this" reads like permission.

## The ladder

```
PRESERVE   Can the existing component do this as-is?
   |       no
MODIFY     Can I change it without changing what it is?
   |       no
COMPOSE    Can I build this from primitives that already exist?
   |       no
CREATE     Write something new -- and write down why.
```

```bash
python3 scripts/ux_check.py <project> --inventory "confirm dialog"
```

The output lists matching components and any headless primitive libraries installed.
If the project has Radix, Base UI, Headless UI, Ark or React Aria, a new dialog,
dropdown, tooltip or combobox is a COMP-001 violation, not a preference — those
libraries have solved focus containment, escape handling, typeahead and ARIA, and a
hand-rolled version will not.

## Identity lock

Before changing anything visual, write one sentence describing what is actually
there, using observable values:

> Surfaces are near-white `oklch(0.99 0 0)` with a single `--color-brand-500` accent;
> type is Inter at three sizes; layout is a fixed sidebar with a fluid content column;
> depth comes from 1px borders, not shadow; the copy is short, second person, no
> exclamation marks.

Rules for that sentence: use hex, OKLCH or token names, not moods. **"Modern" is not
a colour, "clean" is not a type system, "elegant" is not a layout.** Aesthetic-family
words — brutalist, editorial, minimal — are conclusions, not observations, and writing
one down turns it into a self-fulfilling brief.

Extract identity in this order: `DESIGN.md`, then CSS custom properties, then computed
styles on the element you are changing, then its siblings.

## Preserve or depart

**Default to preserve.** Departure requires one of exactly two things:

1. The user explicitly asked for something different.
2. `PRODUCT.md` records an anti-reference that names *this surface*. A general
   anti-reference does not count.

The reason is asymmetric cost. Being wrong about preserving produces a variant that
looks a bit conservative — one message to fix. Being wrong about departing rewrites
someone's product into a style they never asked for, discards decisions they made for
reasons you cannot see, and cannot be undone by asking nicely. **If you are unsure,
you are in preserve mode.**

## Varying without departing

When you owe someone options, vary along one axis and hold the identity fixed. The
axes: hierarchy, layout topology, typographic scale, colour strategy, density,
structural decomposition. Pick a different one per option. No new fonts, no new hues,
no new aesthetic signals.

Then squint: does each option still match the identity sentence? If one drifted, it
crossed into departure by accident. Rework it.

## Proving you preserved

```bash
# before the change
agent-browser open http://localhost:5173/settings && agent-browser screenshot base.png
# after
agent-browser diff screenshot --baseline
```

`R-BASELINE-DIFF` reports NOT_RUN unless you captured a baseline first. GOV-004 asks
you to preserve existing working behaviour; a diff is how you show you did, rather
than asserting it.

## Never edit generated files

Files that are gitignored, carry an `@generated` or `DO NOT EDIT` banner, or live in
`generated/` or `integrations/` are rewritten by the build. An edit there is silent
data loss on the next run. The checks skip them; you should too, and fix the
generator instead.
