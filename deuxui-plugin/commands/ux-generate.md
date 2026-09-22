---
description: Scaffold a screen, component or flow from the declared contract, so it conforms by construction instead of by later correction.
argument-hint: "<what to scaffold>"
---

Target: $ARGUMENTS

Invoke the `deuxui` skill and follow `references/ops/generate.md`.

The preserve ladder runs first — `PRESERVE > MODIFY > COMPOSE > CREATE`. Ask the
inventory before writing a line:

```bash
python3 scripts/ux_check.py <project> --inventory "<what you were about to build>"
```

Generate from the contract, not from a remembered template: every size off the
declared ladder, every colour a declared role, every gap on the declared scale.
That is what makes running the checks over the output meaningful — it is a
positive control on the generator rather than a review of it.

Emit every state in the same pass, because the ones added later are the ones never
added: empty, loading, error, offline, permission-denied, and the destructive
action's confirmation and undo. And no clickable `div` (`S-A11Y-DIVCLICK`) — if the
project has Radix, Base UI, Headless UI, Ark or React Aria installed, compose
theirs rather than hand-writing focus containment you will get wrong.
