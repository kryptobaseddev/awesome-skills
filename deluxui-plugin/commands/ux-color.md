---
description: Build or audit a colour system in OKLCH, with every pair contrast-checked before it is written down.
argument-hint: "[brand hex or hue]"
---

Invoke the `deluxui` skill and read `references/ops/colorize.md`.

If `.deluxui/design.contract.yaml` declares `color.roles`, audit what is there
first — a declared palette failing its own contrast requirement means every
conforming screen inherits the failure, and fixing components is the wrong repair:

```bash
python3 scripts/palette.py --check .deluxui/design.contract.yaml
```

To build one ($ARGUMENTS is a brand colour or a hue):

```bash
python3 scripts/palette.py --seed '$ARGUMENTS' --mode operate
python3 scripts/palette.py --seed '$ARGUMENTS' --mode operate --contract
python3 scripts/palette.py --seed '$ARGUMENTS' --mode operate --dark --contract
```

Pick the mode from what the visitor came to do, not from the brand. Then say
plainly what the tool did not decide: whether the hue belongs to this product,
what the accent is spent on, and how any of it behaves over an image.
