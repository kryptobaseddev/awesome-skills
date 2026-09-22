# phase — the order the work happens in, as a gate

deuxui has always claimed that the visual contract is declared **before** the code
it governs, because a contract written afterwards is a description of whatever got
emitted: it will always show conformance and it is worth nothing.

Until this operation existed, that claim was a comment. Nothing checked it, which
is the same shape as a PASS on a check that never ran.

impeccable's `build-phase` is the ancestor; what deuxui adds is that the order is
measured from the repository rather than tracked — see NOTICE.md.

```
discover -> declare -> wireframe -> prototype -> build -> verify -> release
```

## Use it

```bash
python3 scripts/ux_phase.py init           # detects greenfield or brownfield
python3 scripts/ux_phase.py status         # where you are, and what the next phase needs
python3 scripts/ux_phase.py advance        # checks the requirements, records the evidence
python3 scripts/ux_phase.py check          # the three process detectors as a verdict
```

## What each phase needs to be entered

| Phase | Machine-checked entry requirement |
|---|---|
| `declare` | `PRODUCT.md` and `DESIGN.md` exist, are written, and carry no more than two placeholders |
| `wireframe` | The contract declares every required field — no `UNKNOWN` left |
| `prototype` | At least two wireframes rendered, and somebody chose a structure |
| `build` | A working prototype exists **and** a named person used it and accepted it. A wireframe choice is not enough: a drawing cannot be used, so it cannot establish that the thing works |
| `verify` | UI files changed after the contract snapshot |
| `release` | The merged report says `READY` |

## The snapshot is what makes the order evidence

Entering `wireframe` records the contract's hash, the git head, and the hash of every UI
file in the tree. Entering `verify` compares against it.

- Files changed since the snapshot → the declaration preceded the code, and that
  is now a measurement rather than an assertion. `A-PHASE-ORDER` PASS.
- Nothing changed since → either nothing was built against the contract, or the
  contract was written to describe code that already existed. `A-PHASE-ORDER`
  FAIL, and every `S-CONTRACT-*` PASS in the report would have been circular.

A brownfield project says so (`ux_phase.py init --brownfield`) and gets the honest
version: the contract was derived from what was there on a recorded date, and
conformance is a claim about what changed afterwards. With nothing changed yet, it
reports NOT_RUN — there is no new work whose order could be wrong, which is not the
same as the order being right.

## The refusal happens while the file is open

```bash
python3 scripts/ux_phase.py gate write src/components/Detail.tsx
```

Before `build`, that exits non-zero and names the missing requirement plus the one
command that satisfies it. The plugin wires it to `PreToolUse`, so the refusal
arrives at the moment of the edit rather than at review time — which is the only
moment when not having built it yet is cheap.

Writing the screen before the direction is approved is the failure being
prevented: the code becomes the decision, and the approval that follows is a
formality about something already built.

## The override is deliberate

```bash
python3 scripts/ux_phase.py override build --who "NAME" --reason "..."
```

A gate with no way past it gets bypassed by deleting the state file, and then
there is no record at all. An override needs a person's name — not the agent's —
and a reason of real length, and it lands in `phase.yaml` with the list of
requirements that were unmet at the time. The report carries it.

## Opt-in

With no `.deuxui/phase.yaml`, nothing is refused and the process detectors report
NOT_RUN rather than passing. An unrecorded order of work establishes nothing
either way, which is exactly what NOT_RUN means everywhere else in this tool.

## Verified by

`A-PHASE-ORDER` (`GOV-010`) · `A-COMP-APPROVED` (`GOV-011`) ·
`A-DECISION-VETTED` (`GOV-012`)
