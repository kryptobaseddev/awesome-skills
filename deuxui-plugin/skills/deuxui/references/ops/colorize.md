# colorize — introduce colour as hierarchy, meaning and atmosphere

Colour that carries a role. A swatch with no role is decoration, and decoration
is not a colour system.

Derived from impeccable's `colorize` (Apache-2.0), with the palette decision made
by a tool instead of by feel — see NOTICE.md.

## Before you touch anything

Read `.deuxui/design.contract.yaml`. If `color.roles` is declared, this is a
**refinement inside a committed system**, and CTX-005 applies: a new visual
language introduced to make the result look different is a defect, not a
redesign. If the contract is absent, derive or declare one first —
`scripts/derive_contract.py --write` for existing code, `deuxui design` for new.

Then read what is actually there:

```bash
python3 scripts/ux_check.py . --detector S-TOKEN-HEX --detector S-SLOP-PALETTE \
                               --detector S-CONTRACT-COLOR --json
python3 scripts/palette.py --check .deuxui/design.contract.yaml
```

The first tells you where colour escapes the system. The second tells you whether
the declared system is even internally sound — a declared palette failing its own
contrast requirement means every conforming screen inherits the failure, and
fixing components is the wrong repair.

## Visitor mode decides how much colour may own

| Mode | Colour's job |
|---|---|
| persuade, experience | May carry the voice and own whole regions. |
| operate, read | Encodes action, selection, status and wayfinding. Rarity is what gives the accent its force. |
| native | The platform owns the structure; colour expresses through tint (IOS-010) or the Material roles (AND-008). |

## Build roles, not swatches

```bash
python3 scripts/palette.py --seed '#1f6feb' --mode operate            # look at it
python3 scripts/palette.py --seed '#1f6feb' --mode operate --contract # commit it
python3 scripts/palette.py --seed '#1f6feb' --mode operate --dark --contract
```

Nine roles: canvas, surface, ink, muted, interactive, focus, success, warning,
danger. Each is placed against the contrast it owes and the achieved ratio is
printed, so the palette arrives already measured rather than measured later.

Three things the tool cannot decide, and you must:

- **Whether the hue belongs to this product.** Hue comes from meaning, not from a
  default category association.
- **What the accent is spent on.** The primary action should be the easiest thing
  to find. An accent spent on decoration has nothing left to spend on the action.
- **What happens over an image or a gradient.** Alpha makes contrast
  context-dependent; prefer an explicit colour over a stack of translucent
  overlays. `R-CONTRAST` reports text over an image as unjudged rather than
  guessing, which is a gap you close by looking.

Dark mode is composed, never inverted. Run `--dark` and choose its surfaces; an
inversion produces glare because it raises saturation exactly where it should
fall.

## Write it down

Paste the `color:` block into `.deuxui/design.contract.yaml`, including
`ramp_steps`. The ramp is what makes an escape measurable: a value in the code
that is not on that list is a departure, and departures are the signal that
discriminates. Record deliberate ones under `departures:` with a reason a reader
can weigh.

## Verify

```bash
python3 scripts/ux_check.py .        # then read these rows
```

| Detector | What it settles |
|---|---|
| `S-CONTRACT-COLOR` | Every colour in the code is a declared role or a recorded departure (VIS-001). |
| `S-TOKEN-HEX` | No literal value where a token exists. |
| `S-CRAFT-GRAY-ON-COLOR` | No washed-out neutral secondary text on a coloured surface. |
| `S-CRAFT-PALETTE-WARM` | The neutrals are tinted deliberately or not at all. |
| `S-COLOR-ONLY` | Nothing is communicated by colour alone (VIS-004, A11Y-009). |
| `R-CONTRAST` | The rendered pairs, on the real backdrop, at runtime. |

A clean static scan is a floor. Run the runtime tier: CSS-derived colour cannot
see what an overlay or an image put behind the text.

Hand off to [polish.md](polish.md).
