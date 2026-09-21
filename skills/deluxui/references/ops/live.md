# live — change something, see what moved

The iteration loop. Without a delta the loop is: edit, re-read a 228-row matrix,
guess. `ux_live.sh` answers the only question that matters between edits.

impeccable's `live` renders parameterised variants in a browser for a human to
steer. deluxui's answers a different question with the same loop — not "which of
these do you prefer" but "did that edit help" — because a preference needs a
person and a delta does not. See NOTICE.md.

## Run it

```bash
bash scripts/ux_live.sh http://localhost:5173 --routes /,/settings   # baseline
# ... make one change ...
bash scripts/ux_live.sh http://localhost:5173 --routes /,/settings   # the delta
```

The first run records a snapshot and says so. Every run after it prints:

| Row | Meaning |
|---|---|
| `REGRESSED` | was PASS, now FAIL. Listed first, always. |
| `STOPPED` | was PASS or FAIL, now NOT_RUN or NOT_APPLICABLE. The check examined nothing, so nothing was proved. |
| `fixed` | was FAIL, now PASS. |
| `still` | failing before and after. |

`STOPPED` is the row that makes a green delta trustworthy. An earlier version of
this script did not have it, and deleting the only Kotlin file in a project
reported fifteen Android rules as fixed. Deleting the evidence is not a repair,
and a delta that cannot tell the difference is worse than no delta.

## One change at a time

The delta is only readable if the edit was. Two changes in one step produce a
mixed result with nothing to attribute it to. This is slower to type and faster
to finish.

## What live iteration is for

- Closing a specific list: take the FAIL rows from one detector family and work
  down them, confirming each one moved.
- Regression safety on a refactor: baseline, refactor, delta. Zero regressed is
  the bar, and `STOPPED` rows count against it.
- Threshold experiments: change `.deluxui/ux.config.yaml`, re-run, see which
  rules moved. A STANDARD-class value will refuse to move, loudly — that refusal
  is the point.

## What it is not for

It is not a verdict. `ux_live.sh` compares two runs; `ux_report.py --merge`
produces the gate. A delta of "12 fixed, 0 regressed" on a project with 90
NOT_RUN rules is progress inside an unverified product.

Setup: [live-setup.md](live-setup.md). Verdict: [polish.md](polish.md).
