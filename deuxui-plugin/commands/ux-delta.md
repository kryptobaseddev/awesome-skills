---
description: Run the tiers and print the delta against the previous run — which detectors were fixed, which regressed, which are still failing. Answers "did that edit help".
argument-hint: "[base-url] [--routes /,/settings] [--reset]"
---

Invoke the `deuxui` skill and read `references/ops/delta.md`.

```bash
bash scripts/ux_delta.sh http://localhost:5173 --routes /,/settings   # baseline
# ... make one change ...
bash scripts/ux_delta.sh http://localhost:5173 --routes /,/settings   # the delta
```

Without a delta the loop is: edit, re-read a 235-row matrix, guess. The first run
records a snapshot and says so; every run after it prints what was fixed, what
regressed and what is unchanged.

This was `/ux-live` until the live loop existed. It answers a different question —
not "which of these do you prefer" but "did that edit help" — because a preference
needs a person and a delta does not. For the first question use `/ux-live`.
