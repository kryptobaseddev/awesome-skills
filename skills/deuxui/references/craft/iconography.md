# Iconography

## An icon without a name is a control nobody can use

An icon-only button has no accessible name unless one is supplied, which means a
screen-reader user hears "button" and a voice-control user cannot say its name to
press it. `S-A11Y-ICONBTN` is one of the highest-frequency findings in real
codebases, and the fix is one attribute.

Beyond accessibility: recognition of an unlabelled icon is far worse than teams
assume outside a handful of universals. The hamburger, the magnifier, the X, the
gear and the arrow are learned. Almost nothing else is — and the ones that feel
obvious to the person who chose them are the most dangerous, because no user test
was run.

A label under the icon costs a few pixels and removes the guess entirely. Where
there is genuinely no room, a tooltip is a supplement to the accessible name,
never a substitute — and never the only place critical information appears, since
it does not exist on touch. `S-COMP-TOOLTIP-CRITICAL`.

## One set, one weight, one metaphor

Mixing icon libraries is visible even to people who cannot say why: stroke widths
differ, optical sizes differ, corner treatments differ, and the grid the glyphs
were drawn on differs. One set, one weight, one size scale.

The same applies inside a set. A product that uses outline icons in the nav and
filled icons in the toolbar is claiming a distinction; if no distinction is
intended, it is noise. Filled-vs-outline is a legitimate way to show selected
state — provided it is used for that and only that.

## Optical size is not font size

Icons are drawn on a grid and their strokes are tuned for a size. A 16px icon
scaled to 24px has strokes that are too thin for its size; a 24px icon scaled down
is muddy. Modern sets ship optical sizes — use them rather than a transform.

Alignment: an icon's visual centre is rarely its bounding-box centre, and a
circular glyph next to square text needs a hair more inset to look aligned. See
[detail.md](detail.md).

## Platform sets exist and are better

SF Symbols on Apple platforms and Material Symbols on Android are drawn to match
the system font's weight and optical size, adapt to Dynamic Type, and carry
accessibility names already. A hand-drawn substitute is worse in every one of
those dimensions. `S-IOS-SFSYMBOLS` flags the substitution.

## The icon tile

A rounded square with a gradient fill and a white glyph inside, repeated down a
feature list, is one of the most reliable tells of a generated page — it is a
template shape applied to unrelated content. `S-CRAFT-ICON-TILE` counts them. The
same content usually reads better as a plain glyph in the text colour, sized with
the heading beside it.

## Colour and state

An icon carrying a status must not carry it in colour alone (`S-COLOR-ONLY`), and
an icon that is meaningful must keep its meaning in forced-colors mode, where
`currentColor` survives and a hard-coded `fill` does not — one of the things
`R-FORCED-COLORS` measures by diffing a normal pass against a forced one.

## Adjudicated by

`S-A11Y-ICONBTN` · `S-COMP-TOOLTIP-CRITICAL` · `S-COLOR-ONLY` ·
`S-CRAFT-ICON-TILE` · `S-IOS-SFSYMBOLS` · `S-AND-MATERIAL` · `R-FORCED-COLORS` ·
`M-SCREENREADER`
