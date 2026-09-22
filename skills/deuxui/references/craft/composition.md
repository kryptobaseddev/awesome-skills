# Composition

## One dominant move

A screen has one thing it is for. Composition is the arrangement that makes that
thing findable before anything else, and the most common failure is not ugliness —
it is two elements competing at the same scale, which reads as shouting and leaves
the reader to arbitrate.

Commitment is depth, not coverage: one region takes the weight, the rest hold
still so it can be read. A hero, a dense sidebar and a full-width promotional band
on the same screen are three heroes.

`M-JUDGE-COMPETITION` asks a person whether anything competes with the primary
action, because no checker can know which action is primary. `PRODUCT.md` should
say.

## Regions before pixels

Before any layout decision, name the regions the screen has, in order, with their
proportions and what each one holds. That list is the structural claim — and it is
the thing a comp exists to settle:

```bash
python3 scripts/ux_image.py brief --write .deuxui/comps/detail.brief.yaml --surface "listing detail"
python3 scripts/ux_image.py render .deuxui/comps/detail.brief.yaml
```

Each region declares a **medium**: `flat` (it ships as code) or `plate` (it ships
as a raster). That distinction decides what gets built, and getting it wrong in
either direction is expensive — see [imagery.md](imagery.md).

## The grid earns its keep at the edges

A twelve-column grid is not a moral commitment; it is a way of making unrelated
components line up. What matters is that the *container* width, the gutter and the
column count are declared, so a component built in one place fits in another.
`grid.container_max_px` in the contract is the value; a component that sets its own
max-width is the escape.

Reading content is the exception and wants a measure in characters rather than
columns — 45–75ch — which is usually narrower than the grid suggests. A prose page
using the full twelve columns is a page nobody finishes.

## Alignment is the cheapest quality signal

Optical alignment beats mathematical alignment, and the cases are few enough to
list: a circular icon next to square text needs a hair more inset; a right-aligned
number column aligns on the decimal, not the glyph box; a button's label is
centred on its cap-height, not its line box, so an all-caps label sits low unless
adjusted.

`S-UX-CONTROL-ALIGNMENT` catches controls of different heights sitting in a row —
a 36px input beside a 40px button is the most common instance, and it is visible
to everyone and named by nobody.

## Visual weight, and where the eye goes

Weight comes from size, contrast, colour, isolation and motion, roughly in that
order. Isolation is the underused one: an element with space around it reads as
important without being bigger or louder, which is why dense screens are hard —
there is no space left to spend on emphasis, so everything must get its weight
from contrast instead. See [density.md](density.md).

The corollary: emphasis is relative. Making everything bold makes nothing bold,
and a page where every card has a shadow has a flat page with extra rendering
cost.

## Responsive is a different composition, not the same one scaled

At 320px, a three-column grid is not three narrow columns — it is a stack, and the
order of that stack is a decision. Which region leads on a phone is frequently not
the one that leads on a desktop: the hero image that anchors a wide layout is often
the thing to demote when the fold is 600px tall.

`R-REFLOW` measures overflow and clipping at 320/390/768/1024/1440.
`M-JUDGE-CONTENT-PRIORITY` asks whether the stacking order matches what the
visitor came to do, because the checker can see that it reflows and not whether it
reflows into the right order.

## Adjudicated by

`S-UX-CONTROL-ALIGNMENT` · `S-CRAFT-BALANCE` · `S-CRAFT-RHYTHM` ·
`S-RESP-FIXEDPX` · `S-RESP-OVERFLOW` · `R-REFLOW` · `R-MEASURE` ·
`M-JUDGE-COMPETITION` · `M-JUDGE-CONTENT-PRIORITY` · `M-JUDGE-ALIGNMENT` ·
`A-COMP-APPROVED`

Tools: `scripts/ux_image.py`.
