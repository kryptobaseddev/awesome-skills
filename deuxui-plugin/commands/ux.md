---
description: Route a UX request to the right deuxui operation, from measured signals rather than wording.
argument-hint: "[what you want, in your own words]"
---

The user said: $ARGUMENTS

Invoke the `deuxui` skill, then read `references/ops/routing.md` and follow it.

Do not run an operation yet. First gather the signals it asks for:

```bash
python3 scripts/doctor.py .
python3 scripts/ux_check.py . --signals
```

Then recommend the two or three highest-value next operations, each with one line
of reason drawn from those signals, and wait for the user to pick. The
recommendation is a suggestion they confirm — this tool changes files and records
verdicts, and both deserve a yes.

If they said "redesign", slow down: establish visual authority before assuming a
new visual language is allowed (CTX-005).
