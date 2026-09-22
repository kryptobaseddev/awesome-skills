---
description: The system of record for design decisions — what the design is right now, how it got that way, and what each approval was actually approved against.
argument-hint: "[state|log|show ID|diff|snapshot]"
---

Invoke the `deluxui` skill and read `references/ops/ledger.md`.

```bash
python3 scripts/ux_ledger.py state
```

Every surface this skill writes was already a record of one event: an approval in
`.deluxui/decisions/`, a note in `.deluxui/requests/`, the order of work in
`phase.yaml`, the declaration in `design.contract.yaml`. What nothing held was the
**sequence** — and the sequence is what answers "why is the card radius 20 and not
14", because that is an event, not a file.

`state` keeps four claims apart and never merges them:

| Section | What it is |
|---|---|
| **DECLARED** | The visual commitments, field by field, blanks shown as blanks |
| **BUILT WITH** | Frameworks, primitive libraries, tokens, components — **measured from the repo** |
| **APPROVED** | The live approval per stage, and what it superseded |
| **OPEN** | Notes nobody closed, and fields a check is waiting on |

A contract declaring `depth.metaphor: shadow` over a component library whose every
primitive ships a border is a conflict neither one reveals alone.

```bash
python3 scripts/ux_ledger.py log -v          # every event, oldest first
python3 scripts/ux_ledger.py show DEC-003    # with the contract as it was THEN
python3 scripts/ux_ledger.py diff            # what changed in the declaration
python3 scripts/ux_ledger.py snapshot        # archive the contract by its own hash
```

A decision has always recorded a `contract_sha`, and a hash with no bytes behind it
is a fingerprint of a document nobody kept. The contract is now archived under that
hash automatically whenever one is derived, gated or approved, so `show` can print
what was declared at the time.

When it cannot, it says so and prints nothing. Showing *today's* contract beside an
old approval would make every past decision look as though it were made with
today's information — the worst thing a record can do. `A-CONTRACT-ARCHIVED`
(GOV-015) reports those gaps to the release gate, so an untraceable approval is a
result rather than a silence.

It does not close notes, and it does not invent dates. A note stays open until a
person closes it; an undated event sorts last under a heading that says why, rather
than being given a plausible date from a file's mtime.
