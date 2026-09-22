# ledger — the system of record for design decisions

Every surface this skill writes was already a record of one event. `decisions/`
held an approval, `requests/` held a note, `phase.yaml` held the order the work
happened in, and `design.contract.yaml` held the declaration. What nothing held
was the **sequence** — and the sequence is what somebody arriving in month six
actually needs, because "why is the card radius 20 and not 14" is answered by an
event, not by a file.

```bash
python3 scripts/ux_ledger.py state      # what the design is, right now
python3 scripts/ux_ledger.py log        # how it got that way, oldest first
python3 scripts/ux_ledger.py show DEC-003
python3 scripts/ux_ledger.py diff
python3 scripts/ux_ledger.py snapshot
```

## The declaration is content-addressed

A decision has always recorded a `contract_sha`. A hash with no bytes behind it is
a fingerprint of a document nobody kept, so `snapshot` archives the contract under
that hash in `.deuxui/contract/`, with a lineage index recording which fields
changed against the previous version.

Three things now archive automatically, which is the point — an archive that
depends on somebody remembering has holes exactly at the interesting edits:

| When | Who calls it |
|---|---|
| The contract is derived from an existing codebase | `derive_contract.py --write` |
| The work enters `wireframe`, which is when the snapshot is taken | `ux_phase.py advance` |
| A person records an approval | `ux_review.py` |

The identity is the hash of the **declared subset**, not of the file. Two
consequences worth knowing: a comment-only edit does not create a new version,
because a comment is not a commitment; and filling in an `UNKNOWN` does, because a
commitment appeared. The hash also excludes the contract's own path, so the same
declaration hashes the same on two machines.

## An unresolvable reference is a gap, never a guess

This is the property the whole file is shaped around. If a decision names a
contract nobody archived, `show` says so and prints nothing:

```
DECLARED AT THE TIME
  contract 80f887b4 is named here but is not in .deuxui/contract/. The bytes were
  never archived, so this approval cannot be resolved. Showing today's contract
  instead would misrepresent what was approved.
```

Printing the current contract beside an old approval is the single most misleading
thing a ledger could do: it makes every past decision look as though it were made
with today's information. `state` counts these, and **`A-CONTRACT-ARCHIVED`
(GOV-015)** reports them to the gate, so an untraceable approval is a result rather
than a silence.

## `state` answers four different questions, and keeps them apart

| Section | What it is | Where it comes from |
|---|---|---|
| **DECLARED** | The visual commitments, field by field, with blanks shown as blanks | `design.contract.yaml` |
| **DECLARED IN PROSE** | Audience, jobs and risk; the visual system as built | `PRODUCT.md`, `DESIGN.md` |
| **BUILT WITH** | Frameworks, primitive libraries, tokens, component count | **measured from the repository** |
| **APPROVED** | The live approval per stage, and what it superseded | `decisions/` |
| **OPEN** | Notes nobody has closed, and fields a check is waiting on | `requests/` + the contract |

The two prose declarations are reported by how much is actually written, not by
whether the file exists: they fail by being stubs, and a heading with nothing under
it passes an existence check while settling nothing. Both are archived beside each
contract version, so `show DEC-003` can say what the brief said at the time too --
and says plainly when it cannot.

DECLARED, DECLARED IN PROSE and BUILT WITH are different claims and are never
merged. A contract
declaring `depth.metaphor: shadow` over a component library whose every primitive
ships a border is a conflict nobody would find by reading either one alone.

A field left undeclared reads as `NOT DECLARED — a check is waiting on this, and
reports NOT_RUN`. It is not filled in from a default to make the page look
finished, for the same reason a check that did not run does not report PASS.

## Approvals are latest-per-stage, and supersession is stated

A wireframe approval and a prototype approval answer different questions, so they
are never interchangeable; an earlier approval of the *same* stage has been
superseded by definition. `state` names the live one and lists the superseded ones,
because a record showing three wireframe approvals without saying which is current
is how a build ends up honouring the wrong one.

## Two records in one project

A project can end up with two state directories: someone runs an older version, a
checkout is shared, a directory gets copied by hand. Only one is read, so everything
in the other is silently ignored — including any approval a decision points at.

This tool will not choose between them. Merging them produces a history that never
happened, and picking one silently discards the other. But refusing without giving
you anything to decide with is not much better, so:

```bash
python3 scripts/ux_ledger.py migrate --compare               # the evidence, changes nothing
python3 scripts/ux_ledger.py migrate --adopt .other --apply  # your decision, reversibly
```

`--compare` prints what actually distinguishes them. File counts and dates are the
weak evidence — you can read those with `ls`. The strong evidence is what only a real
history has: archived contract versions whose filenames are content hashes, decisions
that resolve against them, a phase history. A directory with three archived contracts
and four decisions is somebody's design record. A directory with a config file and
nothing else is a scaffold that happens to be newer.

The report names the most complete record and the most recently written one
**separately**, because they disagree exactly when it matters: a fresh `init` writes
recent files over nothing.

`--adopt` **moves** the record you are not keeping to
`.deuxui-archived-<timestamp>-<name>/` and writes a `SET-ASIDE.md` into it saying what
it was and how to put it back. Nothing is deleted and nothing inside is rewritten, so
every `contract_sha` in either still resolves and a wrong answer is one rename from
being undone.

That marker is also what stops the archive being detected as a *new* rival on the next
run — a live record is identified by its contents, so an archive has to be able to say
it is set aside. Without it, resolving one conflict manufactured a permanent one.

## What it does not do

It does not close notes. A note stays open until a person closes it, and nothing
here clears one because a later decision was recorded — a work item that vanished
on a technicality is a work item quietly discarded.

It does not place undated events. An event with no timestamp sorts last under a
heading that says why, rather than being given a plausible date from a file's
mtime, which would put a copied file in the wrong decade.

## Verify

```bash
python3 scripts/ux_ledger.py check         # A-CONTRACT-ARCHIVED on its own
python3 scripts/ux_report.py --merge       # it arrives in the process tier
```
