# Depth

## One metaphor

An element with a 1px border *under* a wide soft shadow is two systems arguing.
Pick one — borders or shadows — and let the other appear only where it does a job
the first cannot.

This is a genuine either/or rather than a preference. A border-based system says
"these are panes on one plane"; a shadow-based system says "these are objects at
different heights". A product that uses both says neither, and every component
after the first has to decide again. The contract declares
`depth.metaphor: border | shadow`, and `S-CONTRACT-DEPTH-METAPHOR` and
`S-CRAFT-DEPTH` measure what the code does against it.

## Elevation is a short list, and the list means something

Three to five levels, each tied to a *behaviour*, not to a size:

| Level | What lives there |
|---|---|
| 0 | The canvas. Nothing floats. |
| 1 | Resting surfaces: cards, panels, table headers. |
| 2 | Raised on interaction: a hovered card, a dragged item. |
| 3 | Overlays anchored to something: dropdowns, popovers, tooltips. |
| 4 | Overlays that take the screen: dialogs, sheets. |

A shadow not on the list is a one-off, and one-offs are how a depth system turns
into a collection of similar blurs. `S-CONTRACT-ELEVATION` counts them.

The other half of the same rule is stacking order. `z-index: 9999` is not a level;
it is an argument the author expected to lose. A product needs perhaps four named
z values, and anything above them is a bug waiting for a second `9999`.
`S-CRAFT-ZINDEX` flags the arms race.

## Shadows that look like shadows

A shadow is light occluded by an object. Three properties follow from that and
each one is commonly wrong:

- **Direction.** Light comes from one place. A shadow offset down-right on one
  component and centred on another says the sun moved.
- **Softness scales with distance.** A dialog 24px above the page has a large,
  diffuse, low-opacity shadow. A card 2px up has a small tight one. A `shadow-2xl`
  on a resting card claims it is floating eight inches off the screen.
- **Colour.** A pure-black shadow at 20% over a warm surface reads as grey mud.
  Shadows should carry the ground's hue, darkened — which is what
  `color-mix(in oklab, var(--ink) 12%, transparent)` gets you cheaply.

`S-CRAFT-HARD-SHADOW` flags the zero-blur offset shadow (an outline pretending to
be depth), and `S-CRAFT-HALO` flags the symmetric all-round glow, which is not a
shadow at all — it is a halo, and it reads as generated because nothing in the
physical world produces one.

## Nesting

A card inside a card inside a card is three borders and no hierarchy. Two levels
is the practical limit; at three the reader has stopped perceiving containment and
started perceiving noise. `S-SLOP-CARDNEST` measures the depth.

The usual cause is that each component was built to be self-contained, so each one
brings its own surface. The fix is that the *outer* container owns the surface and
the inner ones are transparent — which also makes them reusable in more places.

## Blur and translucency

Backdrop blur is expensive, and on a busy background it makes text unreadable in a
way that depends on the content behind it — so a contrast check on one screenshot
proves nothing about the next. `S-SLOP-BLUR` measures density of use, and
`R-PIXEL-CONTRAST` is the only honest way to settle contrast over one.

Where translucency is right — an iOS sheet over a photograph, a sticky header over
scrolled content — the platform materials do it properly and cheaply
(`S-IOS-MATERIALS`). Hand-rolled `rgba` plus `backdrop-filter` usually does not.

## Adjudicated by

`S-CONTRACT-DEPTH-METAPHOR` · `S-CONTRACT-ELEVATION` · `S-CRAFT-DEPTH` ·
`S-CRAFT-HARD-SHADOW` · `S-CRAFT-HALO` · `S-CRAFT-ZINDEX` · `S-SLOP-CARDNEST` ·
`S-SLOP-BLUR` · `S-IOS-MATERIALS` · `S-AND-ELEVATION` · `R-PIXEL-CONTRAST`
