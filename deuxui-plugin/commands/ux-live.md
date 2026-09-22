---
description: Change something and see what moved — regressed, stopped, fixed, still failing.
argument-hint: "[dev url]"
---

Invoke the `deuxui` skill, read `references/ops/live.md`, then:

```bash
bash scripts/ux_live.sh ${ARGUMENTS:-}
```

The first run records a baseline. Every run after it prints the delta.

Read `REGRESSED` and `STOPPED` before anything else. A `STOPPED` row means the
check examined nothing this time, so nothing was proved — deleting the evidence is
not a repair, and an edit that fixes two things while stopping one check has not
made the interface better yet.

Make one change between runs. A delta is only readable if the edit was.
