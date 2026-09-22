# Craft — what to decide, and what decides whether you got it right

Twelve domains. Each one is a body of decisions an interface makes whether or not
anybody makes them deliberately, and each file ends by naming the detectors that
adjudicate its claims.

That ending is not a formality. Craft writing usually terminates in an
exhortation — *be intentional*, *respect the grid* — and an exhortation cannot be
wrong, which means it cannot be checked, which means it changes nothing. Every
claim here either resolves to a number in `../rules/thresholds.yaml`, to a field
in `.deuxui/design.contract.yaml` that the project declared, or to a question in
the manual tier that a person answers and signs. Where a claim resolves to none of
those, it is marked as taste and you are free to disagree with it.

| Domain | Read it when | File |
|---|---|---|
| Type | Anything with words in it, which is everything | [type.md](type.md) |
| Colour | Choosing or auditing a palette; dark mode | [color.md](color.md) |
| Space | It feels cramped, or arbitrary, or like a list of unrelated boxes | [space.md](space.md) |
| Depth | Cards, modals, dropdowns, anything stacked | [depth.md](depth.md) |
| Composition | A new screen; "the layout feels off" | [composition.md](composition.md) |
| Density | Tables, dashboards, admin tools, anything an expert uses daily | [density.md](density.md) |
| Motion | Transitions, loading, anything that moves | [motion.md](motion.md) |
| Imagery | Photographs, illustration, plates, video | [imagery.md](imagery.md) |
| Iconography | Icons, symbols, anything without a label | [iconography.md](iconography.md) |
| Voice | Every string in the product | [voice.md](voice.md) |
| States | Empty, loading, error, offline — the majority of the work | [states.md](states.md) |
| Detail | The last five per cent, after everything else is right | [detail.md](detail.md) |

## Three things that are true across all twelve

**A system is judged by its escapes, not by its shape.** A probe over four real
codebases found the same number of type steps in every one of them — eleven to
seventeen — while arbitrary one-off values per file separated the disciplined
codebases from the sprawling ones by roughly ten times. How many steps you have is
your business. How many values are *not* on the list is the signal, and it is what
`S-TOKEN-ARBITRARY`, `S-CONTRACT-TYPE-SCALE` and `S-CONTRACT-COLOR` measure.

**Craft is checked against a declaration, never against a taste.** "Is this
beautiful?" has no decision procedure. "Does this match what was declared?" has
one, and it never requires anybody to adjudicate the declaration itself. That is
the whole trick: it removes taste from the verdict instead of pretending to
resolve it. With no `.deuxui/design.contract.yaml`, the conformance checks report
NOT_RUN — an undeclared system cannot be conformed to.

**The second-order reflex fails too.** Knowing that gradients and glassmorphism
read as generated does not mean the flat monochrome alternative is a decision. It
is the same reflex one step later. The question is what this product is for and
who is looking at it, and the answer is in `PRODUCT.md` and
[../design/visitor-modes.md](../design/visitor-modes.md), not in a trend.

## Where this sits

- [../design/craft-floor.md](../design/craft-floor.md) — every craft number in one
  table, with the detector that decides it. This directory is the reasoning; that
  is the reference.
- [../anti-slop.md](../anti-slop.md) — the catalogue of tells, and why each one
  reads as machine-made.
- [../ops/index.md](../ops/index.md) — the operations. A craft file tells you what
  good looks like; an operation is the move that gets you there.
