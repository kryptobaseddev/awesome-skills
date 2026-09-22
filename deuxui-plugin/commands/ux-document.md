---
description: Capture the visual system the code already implies — as a machine-readable contract, not only as prose.
argument-hint: "[path to read, default the whole project]"
---

Target: $ARGUMENTS

Invoke the `deuxui` skill and follow `references/ops/document.md`.

Derive, do not describe. Run `scripts/derive_contract.py` over the real code
first, read the spread it prints beside each dominant value — that spread is how
you tell the scale from the drift — and only then write anything down.

Produce both artefacts and understand why there are two: `.deuxui/DESIGN.md` is
what a person reads, and `.deuxui/design.contract.yaml` is what the
`S-CONTRACT-*` detectors compare the code against. Prose cannot be conformed to,
so a DESIGN.md with no contract beside it leaves every contract check reporting
NOT_RUN.

Anything the code does not decide is left `UNKNOWN`. A guessed value becomes the
thing everything else is measured against, which is worse than a blank.
