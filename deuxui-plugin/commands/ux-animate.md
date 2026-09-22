---
description: Motion that makes a relationship legible — and stops when the operating system asks it to.
argument-hint: "<the interaction or transition>"
---

Target: $ARGUMENTS

Invoke the `deuxui` skill and follow `references/ops/animate.md`.

Write the `prefers-reduced-motion` branch in the same edit as the animation, never
after. An animation with no reduced-motion path is not a polish gap; it is an
accessibility failure with a health consequence (A11Y-010, LAY-010), and
`S-MOTION-REDUCE` will say so.

Every duration comes off the contract's declared motion band
(`S-CONTRACT-MOTION`), and the easing comes off the declared curves
(`S-CRAFT-EASING`). Motion that only decorates costs attention; if you cannot say
which relationship the movement explains, do not add it.

Check it in the browser: `R-MOTION` measures what actually ran, and
`S-CRAFT-HIDDEN-AT-REST` catches content that is invisible until something moves.
