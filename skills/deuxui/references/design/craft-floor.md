# The craft floor

The mechanics that separate a page someone built from a page something assembled.
Everything here is measured — each line names the detector that decides it, so none of
it is advice you have to take on trust.

A floor is not a ceiling. All of it green means the mechanics are not in the way. It
says nothing about whether the design is any good, and a detector that implied otherwise
would be lying.

Derived from the impeccable skill's craft floor (Apache-2.0,
github.com/pbakaus/impeccable). Numbers live in `references/rules/thresholds.yaml` under
`type_craft`, `depth`, `motion_craft` and `zindex`, and every one is overridable by a
project that genuinely chose a different bar.

## Type

| Rule | Number | Detector |
|---|---|---|
| Display type stops before it shouts | clamp() max ≤ **6rem** | `S-CRAFT-HERO-SCALE` |
| Adjacent roles carry different jobs | ≥ **1.25×** between steps | `S-CRAFT-TYPE-FLAT` |
| Tracking has a floor | ≥ **-0.04em** | `S-TYPE-TRACKING` |
| The system has a voice, not a committee | ≤ **3** families | `S-CRAFT-FAMILIES` |
| Reading measure | **45–75ch** | `S-TYPE-MEASURE`, `R-MEASURE` |
| Body text is readable | ≥ **12px**, 1rem ordinary floor | `S-TYPE-TINY` |
| Headings break on purpose | `text-wrap: balance` | `S-CRAFT-BALANCE` |

Scale substituting for hierarchy is the tell. If the h1 needs 9rem to feel primary, then
nothing else on the page is doing that work — weight, space and colour are all idle.

## Depth

One metaphor. Border *or* shadow, and the contract names which (`depth.metaphor`).

- Shadows carry an offset and a blur, because light comes from somewhere. A zero-offset
  coloured ring comes from nowhere and reads as a sticker — `S-CRAFT-HALO`.
- A zero-blur offset block shadow is the neobrutalist signature. Worn by a world that did
  not choose it, it is a costume — `S-CRAFT-HARD-SHADOW`.
- A 1px border under a wide soft shadow is two systems arguing — `S-CRAFT-DEPTH`.
- Card radii sit around **12–16px**; pills are for small controls — `S-CRAFT-CARD-RADIUS`.

## Motion

One authored moment, not one identical entrance per section.

- Exponential ease-out. `ease-in-out` on an entrance reads as lag; a negative bezier
  control point is bounce, which is a template's idea of personality — `S-CRAFT-EASING`.
- **Never gate content visibility on a reveal.** Transitions do not run on inactive tabs
  or in headless renderers, so the section ships blank and nobody sees it in development.
  Animate up from an already-visible default — `S-CRAFT-HIDDEN-AT-REST`.
- Reduced motion is not optional — `S-MOTION-REDUCE`, `R-MOTION`.

## Browser surfaces

The parts nobody drew still carry the design. Text selection, the caret, scrollbars, the
focus ring, underline offset, and tabular numerals in compared columns all ship with
browser defaults that belong to no design system. Theming them from the palette is the
cheapest signal a page was built rather than assembled, and it is the thing models skip
most reliably — `S-CRAFT-SURFACES`.

## Colour

- Contrast is not negotiable: body and placeholder ≥ 4.5:1, large text ≥ 3:1, controls
  and focus indicators ≥ 3:1 — `S-CONTRAST-PAIR`, `R-CONTRAST`.
- Grey on a chromatic surface reads washed out however good the ratio, because the
  surface has hue and the text has none. Tint from the surface — `S-CRAFT-GRAY-ON-COLOR`.
- Gradient text fails contrast across part of its own run by construction, and is the most
  recognisable generated-UI signature there is — `S-CRAFT-GRADIENT-TEXT`.
- Dark mode is composed, not inverted. A real dark theme reduces contrast *and*
  saturation; inversion produces glare.

## Scaffolds to refuse

Defaults, not bans — the brief's own words can earn any of them. Reaching for one when
the axis was free means you were not deciding.

- Same-size cards of icon + heading + text as the page structure. Nested cards are always
  wrong — `S-SLOP-CARDNEST`.
- An icon in a tinted rounded square, repeated down a feature list — `S-CRAFT-ICON-TILE`.
- Zero-padded section numbers where the sequence carries no information —
  `S-CRAFT-SECTION-NUMBERS`.
- An eyebrow or kicker above a heading. The heading carries its own weight —
  `S-SLOP-EYEBROW`.
- Repeating-gradient stripes with no material under them — `S-CRAFT-STRIPES`.
- `z-index: 9999`. Above 100 it is a bidding war, not a scale — `S-CRAFT-ZINDEX`.
- Emoji standing in for an icon system — `S-SLOP-EMOJI`.

## Optical alignment

The skill used this word for a long time without defining it, which made "optical
misalignment" an unfalsifiable diagnosis. Here is what it means and what to do.

**Optical alignment is when geometric centring looks wrong.** The eye centres on perceived
mass, not on the bounding box, so a shape whose mass is not evenly distributed reads as
off-centre when it is mathematically perfect. The common cases:

- A triangular play icon in a circular button. Its mass sits left of its box centre, so it
  needs ~1–2px of right shift to look centred.
- Round letterforms and shapes (O, C, 0, a circular badge) overshoot a flat baseline
  slightly on purpose; matching their bounding box to a square's makes them look small.
- Text next to an icon: align to the cap height, not the bounding box.
- A quotation mark or bullet hung outside the text column looks aligned when the *glyph
  body* lines up, not its box.

**No detector decides this.** It is one of the things only a person looking can call, and
it is recorded as a manual result if it matters. Do not report it as checked — say you
looked, and say what you saw.
