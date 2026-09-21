# extract — pull repeated patterns into the system

Consolidation. The failure modes are equal and opposite: leaving the same button
implemented nine ways, and abstracting a component used twice.

Derived from impeccable's `extract` (Apache-2.0) — see NOTICE.md.

## Find the design system before adding to it

```bash
python3 scripts/ux_check.py . --inventory "button card input modal"
```

That reports the matching components, the total inventory size, and which
primitive libraries are already installed. If there is no design system, **do not
create one yet** — ask where it should live and what the conventions are. A second
design system beside the first is worse than none.

## The threshold is three, with the same intent

Extract what is used three or more times **for the same reason**. Two uses is a
coincidence. Three uses with different intents is three components that happen to
look alike, and merging them creates a props API that grows a boolean per call
site. Premature abstraction costs more than duplication.

What is worth looking for, with the detector that finds it:

| Opportunity | Detector |
|---|---|
| Hardcoded colour where a token exists | `S-TOKEN-HEX` |
| Off-scale spacing and sizing | `S-TOKEN-ARBITRARY` |
| A hand-built control that already exists natively | `S-A11Y-DIVCLICK`, `S-MODAL-NATIVE` |
| Repeated size-plus-weight-plus-leading combinations | `S-CRAFT-TYPE-FLAT`, `S-CONTRACT-TYPE-SCALE` |
| Repeated easing and duration | `S-CRAFT-EASING`, `S-CONTRACT-MOTION` |
| A component reinvented that the inventory already has | `S-DS-REINVENT` |

## Extract with the contract in hand

A token extracted to a value nobody declared is a new value in the system. Put it
in `.deluxui/design.contract.yaml` in the same edit, or the next scan reports it
as an escape — correctly.

Every extracted component owes the things the inline version was quietly getting
from the browser, or quietly failing to: a name, a role, a keyboard pattern, a
focus ring, a disabled state that is not just greyed text, and the full state set
(default, hover, focus, active, disabled, loading, error). Shipping half of these
is how a design system becomes the source of the accessibility defects instead of
the fix for them.

## Migrate, and prove nothing broke

```bash
bash scripts/ux_live.sh http://localhost:5173     # before
# ... migrate call sites ...
bash scripts/ux_live.sh http://localhost:5173     # after
```

Zero regressed is the bar, and a `STOPPED` row counts against it. Extraction
touches many files at once, which makes it the operation most likely to break
something in a place nobody is looking.

Then: [polish.md](polish.md).
