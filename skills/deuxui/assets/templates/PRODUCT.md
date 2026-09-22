# Product

Who this is for and what they are trying to finish. **No colours, no fonts, no
spacing** — those live in `DESIGN.md`. Keeping them apart is what stops one file
trying to be both a brief and a style guide.

Anything you do not know yet is `UNKNOWN`. That is a real answer and a useful one;
inventing an audience is not.

## Users

Who uses this, what they already know, and what they are doing while they use it
(at a desk, on a phone in a warehouse, under time pressure).

## Jobs to be done

The two or three things people come here to finish. Phrased as outcomes, not features.

## Primary tasks

The handful of flows that carry the value. These get the most testing.

## Rare high-impact tasks

Cancel, refund, delete, export, recover, dispute, transfer ownership. Infrequent and
catastrophic when broken — LAW-20 exists because these are the first things dropped
from a test plan and the first things that end up in a support queue.

## Irreversible or external actions

Every action that spends money, sends something to a third party, publishes, revokes
access, or destroys data. Each one needs a clear consequence before commit and a
recovery path after. Drives `--feature payments_or_legal` and
`--feature destructive_actions`.

## Constraints

Brand commitments, regulatory requirements, a component you must not touch, a
platform convention you must follow.

## Anti-references

Specific things this should not become, and **which surface** each one is about. A
general anti-reference does not authorise departing from the existing design on a
particular screen — see `references/preserve.md`.

## Support matrix

Devices, browsers, operating systems, input modes, locales, time zones, network
conditions. What you list here is what gets tested; what you leave out is untested,
not passing.

## Assumptions and open questions

Reversible defaults you chose, and what would change if you were wrong.
