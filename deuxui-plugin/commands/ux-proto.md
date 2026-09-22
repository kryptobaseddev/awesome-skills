---
description: Generate a working prototype from the design contract — real states, a real form, a real dialog, a real table — that a person can click, toggle and actually use.
argument-hint: "[title]"
---

Invoke the `deuxui` skill and read `references/ops/prototype.md`.

A wireframe settles structure. It cannot settle whether the thing works, because a
drawing cannot be used. This is the artefact for the second question.

```bash
python3 scripts/ux_proto.py --write .deuxui/proto/index.html --title "${1:-Prototype}"
python3 scripts/ux_check.py .deuxui/proto      # the generator must pass its own checks
```

Everything it emits comes from `.deuxui/design.contract.yaml` — the colour roles,
the type ladder, the spacing scale, the one declared depth metaphor — so it is
conformant by construction and the check above is a positive control rather than a
review of taste. If the contract names a typeface the project does not ship, the
page says so on its own face.

What is in it, and why each one is there:

- **the five states as a switch** — ready, loading, empty, error, offline. The part
  that never gets built and never gets looked at.
- a form with real labels, `:user-invalid` validation, an error summary linked to
  its fields, and a guarded submit
- a dialog that traps focus, a destructive action with confirm **and** an undo that
  puts the row back, and an activity list so the confirmation outlives the toast
- tabs with roving `tabindex` and arrow keys; a table with header scope, tabular
  figures, and zero shown differently from not-collected
- theme and density toggles, disabled controls that say why

Then adapt it to the actual screen, or lift components out of it. It is a
conforming reference, not the product.

Next: `/ux-review` — put it in front of a person.
