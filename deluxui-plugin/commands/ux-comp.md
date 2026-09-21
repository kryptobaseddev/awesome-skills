---
description: Render three comps from the declared contract, generate rasters where a model is reachable, and measure what comes back against the contract it claims to express.
argument-hint: "[surface name]"
---

Invoke the `deluxui` skill and read `references/ops/visualize.md`.

A comp round settles a structural question with a picture instead of a paragraph.
Three things have to be true for it to be worth doing, and the tooling enforces
all three.

**The world is already committed.** Read `.deluxui/design.contract.yaml` first. If
required fields are still `UNKNOWN`, this round cannot settle them — the comps
will be drawn with placeholders and the sheet says so on its face. Declare them,
or accept that the approval does not cover them.

```bash
python3 scripts/ux_image.py brief --write .deluxui/comps/$1.brief.yaml --surface "$1"
# edit the regions: `share` is the vertical proportion, `medium` is flat or plate
python3 scripts/ux_image.py render .deluxui/comps/$1.brief.yaml
```

`render` needs no model, no key and no network. It draws each option from the
contract, so the comps are conformant by construction and cannot be the thing
that drifts. The caption block under each sheet carries the structural claim —
region, medium, share, what it holds — because a comp approved for its atmosphere
has not approved the part the build has to honour.

**Where a model is reachable, ask it too, and then check it.**

```bash
python3 scripts/ux_image.py providers          # what can generate here, and why not
python3 scripts/ux_image.py generate .deluxui/comps/$1.brief.yaml
python3 scripts/ux_image.py verify .deluxui/comps/$1-A.png
```

The prompt is built from the contract — the palette by role with its hex values,
the families, the ladder, the radii, the depth metaphor, the visitor — not from an
adjective. `verify` then measures what came back: every declared role has to be
present in the image at real coverage, and a colour that is close in distance but
opposite in tint is reported as a different world rather than a near miss. With no
provider, generation reports NOT_RUN and the rendered sheets stand. It never
silently produces nothing.

**Then stop.** Do not begin code until a person has chosen:

```bash
python3 scripts/ux_question.py ask .deluxui/comps/$1.comps.yaml
```

Read `references/craft/composition.md` before drawing the regions, and
`references/craft/imagery.md` before deciding any of them is a plate.
