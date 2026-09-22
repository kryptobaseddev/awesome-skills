# distill — take away until only the work is left

Removal, done as engineering rather than as taste. The question is never "is this
simpler"; it is "does the same task still complete, in the same states, with the
same recoveries".

Derived from impeccable's `distill` (Apache-2.0) — see NOTICE.md.

## What distilling is not

LAW-19 (Occam) carries the warning in its own text: fewer visible elements,
fewer clicks and fewer lines are **not** automatic measures of quality. The
failure mode of this operation is deleting a recovery path, an empty state or a
keyboard behaviour and calling the result clean.

Three things are never removed in the name of simplicity:

- a recovery path (undo, cancel, back) — UX-003, TRUST-006;
- an accessibility behaviour — the whole A11Y family;
- essential guidance, a state, or a safety check — STATE-001 onward.

## The order that works

1. **Remove duplicated information** before removing anything else. The same fact
   stated three ways is the cheapest win and costs nothing.
2. **Remove decisions the user should not be making.** A default that is right
   nine times out of ten removes a decision without removing a capability.
3. **Remove competing emphasis.** UX-008: every prominent element should support
   the current task. This is usually where the real gain is, and it deletes no
   functionality at all.
4. **Only then remove elements.** And for each, say which task no longer needs it.

## Prove nothing broke

Removal is the operation most likely to break something silently, so the evidence
bar is higher here than anywhere else:

```bash
python3 scripts/ux_check.py . --json > after.json      # compare with before
bash scripts/ux_browser.sh http://localhost:5173 --baseline before.png
```

`R-BASELINE-DIFF` shows that pixels moved. It cannot show that a flow still
works, which is exactly what `M-PRESERVE-REGRESSION` asks you to establish by
running the flows rather than looking at the screens (GOV-004).

## Verify

| Detector | What it settles |
|---|---|
| `S-STATE-EMPTY`, `S-STATE-ERROR`, `S-STATE-LOADING` | The states you might have removed are still there. |
| `S-FOCUS-OUTLINE`, `S-A11Y-LABEL` | No accessibility behaviour went with the visual tidy-up. |
| `S-TRUST-DESTRUCT`, `S-STATE-CANCEL` | The recovery path survived. |
| `R-FOCUS-WALK` | The keyboard path still completes. |
| `M-PRESERVE-REGRESSION` | Somebody ran the flows, not the screenshots. |

Hand off to [polish.md](polish.md).
