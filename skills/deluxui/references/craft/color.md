# Colour

## Roles, not swatches

A colour with no role is decoration. The contract declares nine:

```
canvas  surface  ink  muted  interactive  focus  success  warning  danger
```

Everything else in the product is derived from those or is an escape.
`S-CONTRACT-COLOR` measures the escapes, and `S-TOKEN-HEX` catches a raw hex
written where a token exists.

The reason roles beat swatches is substitution. "Brand blue" cannot tell you what
to do in dark mode, on a coloured surface, or when the value fails contrast
against the text sitting on it. "Interactive" can: it is the thing that must be
distinguishable from ink, must clear 3:1 against its background as a non-text
indicator, and must survive being placed on both canvas and surface.

## Generate the palette against the contrast it owes

Picking colours and then measuring them is backwards: you get a palette that is
nearly right and a set of small compromises nobody can see. Solve for the contrast
instead.

```bash
python3 scripts/palette.py --seed '#1f6feb' --contract
python3 scripts/palette.py --check              # audit a declared palette
```

It works in OKLCH, places each role at the lightness that *achieves* the ratio it
owes, and tapers chroma near the ends of the lightness range — without the taper a
ramp goes neon at the top and muddy at the bottom, which is the most visible
difference between a palette somebody built and one a loop emitted.

## The margins are invisible and the failures are not

Indigo-500 with white text is 4.47:1. It fails 4.5:1 and no human eye will ever
catch it. This is why contrast is the one craft decision that is never a judgement
call: `S-CONTRAST-PAIR` resolves what it can from source, `R-CONTRAST` measures the
computed result in the browser, and `R-PIXEL-CONTRAST` settles what neither can —
text over a gradient, a photograph, or a positioned sibling — by reading the
painted pixels.

Three ratios, and they are different criteria rather than a scale: 4.5:1 for body
text, 3:1 for large text (24px, or 18.66px bold) and for non-text indicators such
as a focus ring or an input border, and no requirement at all for decoration that
carries no information. Claiming the third for something that is actually the
second is the most common way a contrast failure gets argued away.

## Dark mode is composed, not inverted

Inversion produces glare: pure white text on a pure black ground at full
saturation, where the reader's iris is open and every bright pixel blooms. A real
dark theme reduces contrast *and* saturation — ink goes to a warm off-white, the
ground goes to a dark that is not black, and the accent is lightened so it still
clears 3:1 against the new ground.

The single most common dark-mode bug: a muted grey chosen against paper, carried
over unchanged, landing at about 2.5:1 on a dark card. The light theme passes,
the dark one fails, and nobody checks the dark one. Derive muted from the new ink
and ground rather than carrying a value across.

`S-CRAFT-PALETTE-WARM` looks at whether the neutrals have a tint at all — a ramp
of pure greys next to a warm accent reads as two unrelated systems — and
`S-CRAFT-GRAY-ON-COLOR` catches the related error of putting a neutral grey text
colour on a saturated ground, where it reads as dirt.

## Colour is never the only signal

About one in twelve men cannot distinguish the red/green pair that "error" and
"success" usually resolve to. A status that is only a colour is a status they
cannot read. `S-COLOR-ONLY` flags it; the fix is an icon, a word, or a shape
alongside — not a different pair of colours.

Related, and checked separately: forced-colors mode replaces the entire palette
with the user's own. A product whose meaning lives in its colours loses that
meaning, and `R-FORCED-COLORS` measures it by diffing two passes — something that
carried a distinction before and does not after.

## The ramp is a ladder, and a value between two rungs is an escape

`color.ramp_steps` in the contract is the set of lightness steps the palette
actually uses. A colour whose lightness sits between two of them reads as a tier the
system does not have — and, more practically, it cannot be re-tuned when the ramp
moves, so it drifts away from everything around it the first time the palette is
adjusted.

`S-CONTRACT-RAMP` measures lightness only, deliberately. Hue and chroma are where a
designer legitimately varies: a warning amber and a success green share a lightness
step and nothing else. Lightness is the axis a ramp fixes. Tolerance is 0.02 in
OKLCH L, which is roughly where two surfaces stop reading as the same tier.

Declare no ramp and the check reports NOT_RUN — there is no ladder for a colour to
be off. `scripts/palette.py` writes a ramp you can paste in.

## Adjudicated by

`S-CONTRACT-COLOR` · `S-CONTRACT-RAMP` · `S-CONTRAST-PAIR` · `S-TOKEN-HEX` · `S-COLOR-ONLY` ·
`S-CRAFT-PALETTE-WARM` · `S-CRAFT-GRAY-ON-COLOR` · `S-CRAFT-GRADIENT-TEXT` ·
`S-SLOP-PALETTE` · `R-CONTRAST` · `R-PIXEL-CONTRAST` · `R-FORCED-COLORS`

Tools: `scripts/palette.py`, `scripts/ux_forcedcolors.py`.
