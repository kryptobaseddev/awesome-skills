# delta — change something, see what moved

The iteration loop. Without a delta the loop is: edit, re-read a 235-row matrix,
guess. `ux_delta.sh` answers the only question that matters between edits.

This was called `live` until the live loop itself existed. It answers a different
question — not "which of these do you prefer" but "did that edit help" — because a
preference needs a person and a delta does not. For the first question, see
[live.md](live.md). See NOTICE.md.

## Run it

```bash
bash scripts/ux_delta.sh http://localhost:5173 --routes /,/settings   # baseline
# ... make one change ...
bash scripts/ux_delta.sh http://localhost:5173 --routes /,/settings   # the delta
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
- Threshold experiments: change `.deuxui/ux.config.yaml`, re-run, see which
  rules moved. A STANDARD-class value will refuse to move, loudly — that refusal
  is the point.

## What it is not for

It is not a verdict. `ux_delta.sh` compares two runs; `ux_report.py --merge`
produces the gate. A delta of "12 fixed, 0 regressed" on a project with 90
NOT_RUN rules is progress inside an unverified product.

Setup: [live-setup.md](live-setup.md). Verdict: [polish.md](polish.md).

## Point at it, and have the pointing land as a record

The most valuable input in this work is a person looking at the real thing and
saying "that". It is also the input that evaporates fastest: it arrives as "the
spacing on the card feels off", the agent guesses which card, and the correction
is lost by the next message.

```bash
agent-browser open http://localhost:5173
python3 scripts/ux_select.py watch
```

An overlay goes into the page the browser already has open — no server, no
framework adapter, no build step. Hovering outlines an element; clicking captures
it and asks what is wrong with it, in the vocabulary the operations already use:
`bolder`, `quieter`, `distill`, `clarify`, `layout`, `space`, `colorize`,
`typeset`, `polish`, or `broken` for a defect rather than a preference.

Each answer becomes `.deuxui/requests/REQ-NNN.yaml` carrying the selector, the
element's text, its computed type, colour, spacing, radius and shadow, its box,
and the viewport it was seen at. So the request names an operation and an element
rather than a feeling, and the agent has enough to find it in the source without
guessing.

What this deliberately does **not** do is patch the DOM with a generated variant.
The change belongs in the source, where the dev server's own hot reload shows it
and the delta loop above measures it. A variant that exists only in the page has
to be committed back afterwards, and that round trip is where an edit gets lost —
which is also why nothing here needs a per-framework adapter.

Nobody pointing at anything is NOT_RUN, not agreement: an unreviewed screen is not
a reviewed one.

```bash
python3 scripts/ux_select.py list
```
