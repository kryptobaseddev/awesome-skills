---
description: Composition, rhythm and where the eye lands — priority stated first, arrangement as the consequence.
argument-hint: "<the screen>"
---

Target: $ARGUMENTS

Invoke the `deuxui` skill and follow `references/ops/layout.md`.

State the content priority in words, in order, before arranging anything. That is
LAY-001, and `M-JUDGE-CONTENT-PRIORITY` is the question you have to answer: at the
narrowest supported width, are the primary task and its essential context both
still reachable?

Spacing comes off the declared scale, never from an arbitrary utility value
(`S-TOKEN-ARBITRARY`, `S-CRAFT-RHYTHM`). Then prove it rather than eyeballing it:
`R-REFLOW` settles whether the composition survives 320px, and
`R-STICKY-OBSTRUCTION` catches a pinned bar that covers the thing it sits over.

Do not reach for a fixed pixel width or `100vh` on the way
(`S-RESP-FIXEDPX`, `S-RESP-VH`), and do not let a table be the only way to read a
value on a phone (`S-RESP-TABLE`).
