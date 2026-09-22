# Space

Space is the cheapest tool in the kit and the first thing an agent spends
carelessly, because no check fails when it is wrong and every screen has some.

## One scale, and everything on it

A 4px base with a geometric-ish ramp — 4, 8, 12, 16, 24, 32, 48, 64 — covers a
product. The number of steps is not the point; being *on* the scale is. A padding
of 7px, a gap of 13px and a margin of 18px are three decisions nobody made, and
they are exactly what `S-TOKEN-ARBITRARY` counts.

The reason arbitrary values feel wrong even when no individual one is noticeable:
alignment. Elements spaced on a shared scale line up across unrelated components
without anybody arranging it. Elements spaced by eye do not, and the result reads
as slightly broken in a way nobody can point at.

## Proximity carries meaning, so unequal gaps are a claim

If a label sits 8px above its field and 8px below the field above it, the label
belongs to neither. This is the most common spacing defect in forms and the
easiest to fix: the gap *within* a group must be visibly smaller than the gap
*between* groups. A 2:1 ratio is enough; 1.5:1 usually is not.

Every list, every form, every card grid makes this claim whether or not it is
deliberate. `M-JUDGE-ALIGNMENT` asks a person to confirm the grouping the spacing
implies is the grouping the content has, because no checker can know what belongs
together.

## Rhythm down the page

Sections separated by identical space read as a list of unrelated boxes. The
vertical rhythm should say something about structure: a large gap before a new
section, a medium one between blocks inside it, a small one between lines of the
same block. `S-CRAFT-RHYTHM` looks for the case where every gap is the same value,
which is the signature of spacing applied by a loop rather than by a decision.

The inverse failure is a page where every section has a different gap, which is
the arbitrary-value problem wearing a larger hat.

## Padding is about the content, not the container

A card's padding is set by what is inside it. A dense table wants 8–12px; a
marketing card with one sentence wants 24–32px. Applying one padding value to
every card in a product produces cramped data views and empty-looking prose.

The tell that padding was never decided: `p-6` on everything, including the things
that needed `p-3` and the things that needed `p-10`. `S-SLOP-UNIFORM` catches the
family of uniform-everything defects.

## The gutter, and the edges of the screen

16px minimum from the screen edge to text on a phone, or the first and last
characters sit under the curve of the display and the thumb holding it
(`S-TYPE-EDGE`). On devices with a notch or a home indicator, that floor is the
safe-area inset, not a fixed number — `S-RESP-SAFEAREA` checks that the inset
variables are actually used, and `S-IOS-SAFEAREA` and `S-AND-INSETS` do the
platform-native versions.

At 320px everything has to still work: no horizontal scroll, no clipped controls,
no two-column layout pretending 160px is a column. `R-REFLOW` measures it at the
widths that matter, and `S-RESP-FIXEDPX` catches the fixed pixel width that
guarantees the failure before anybody opens a browser.

## Whitespace is not emptiness

The most common request an agent receives about space is to remove it — "it feels
empty". Usually the problem is not the amount of space but that the space is
undifferentiated: everything has the same amount, so nothing groups and nothing
leads. Adding hierarchy to the spacing fixes the feeling that removing space would
only have hidden.

## Adjudicated by

`S-TOKEN-ARBITRARY` · `S-CRAFT-RHYTHM` · `S-SLOP-UNIFORM` · `S-TYPE-EDGE` ·
`S-RESP-SAFEAREA` · `S-RESP-FIXEDPX` · `S-IOS-SAFEAREA` · `S-AND-INSETS` ·
`R-REFLOW` · `M-JUDGE-ALIGNMENT`
