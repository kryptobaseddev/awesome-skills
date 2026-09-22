---
description: Pull repeated patterns into the design system — three uses with the same intent, not two.
argument-hint: "<what to look at>"
---

Target: $ARGUMENTS

Invoke the `deuxui` skill and follow `references/ops/extract.md`.

Find the system before adding to it:

```bash
python3 scripts/ux_check.py . --inventory "button card input modal"
```

If there is no design system, do not create one — ask where it should live first.
A second design system beside the first is worse than none.

Extract at three uses with the same intent. Every extracted component owes a
name, a role, a keyboard pattern, a focus ring and the full state set; shipping
half of those makes the design system the source of the accessibility defects
instead of the fix for them.

Migration touches many files, so baseline with `ux_live.sh` and require zero
regressed and zero stopped.
