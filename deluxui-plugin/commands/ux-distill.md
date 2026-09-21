---
description: Remove until only the work is left — without removing a recovery path.
argument-hint: "<the screen or flow>"
---

Target: $ARGUMENTS

Invoke the `deluxui` skill and follow `references/ops/distill.md`.

LAW-19 carries its own warning: fewer elements, fewer clicks and fewer lines are
not automatic measures of quality. Three things are never removed in the name of
simplicity — a recovery path, an accessibility behaviour, or a state.

Work in the order that pays: duplicated information, then decisions the user
should not be making, then competing emphasis, and only then elements. For each
element removed, say which task no longer needs it.

Removal is the operation most likely to break something silently, so baseline
first and compare:

```bash
bash scripts/ux_live.sh                  # before
# ... remove ...
bash scripts/ux_live.sh                  # after: zero regressed, zero stopped
```
