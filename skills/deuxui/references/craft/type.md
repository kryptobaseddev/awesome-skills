# Type

Type is the interface. Almost everything a product says, it says in words, and
every decision below is made whether or not anybody makes it.

## The ladder, and why adjacent steps have to differ

A type scale is a set of roles — display, title, subtitle, body, caption, label —
each with a job. Two steps that differ by less than about 1.25× cannot carry
different jobs: at 15px and 16px a reader sees an inconsistency rather than a
hierarchy, and every use of the smaller one is a decision nobody can defend.

This is the single most common defect in generated interfaces, and it has a shape:
sizes accumulate one at a time, each reasonable in isolation, until a codebase has
fourteen values between 12 and 24 pixels and no scale at all. `S-CRAFT-TYPE-FLAT`
measures the gaps; `S-CONTRACT-TYPE-SCALE` measures departures from the declared
ladder once one exists.

Generate one rather than accumulating it:

```bash
python3 scripts/typescale.py --contract        # a ladder that clears 1.25x by construction
python3 scripts/typescale.py --check           # audit the one you have
```

Steps below about 12px are dropped and reported rather than rounded: a rung nobody
can read is not a rung.

**How many steps.** Five to seven roles covers a product. More than nine and the
roles stop being distinguishable, which is the same failure as too-close steps
arriving by a different route.

## Measure, leading, and the relationship between them

Reading measure — the line length — wants 45 to 75 characters. Past about 75 the
return sweep starts failing and people re-read lines without noticing they are
doing it. `R-MEASURE` measures the rendered result in the browser, because a
`max-width` in pixels is a guess about a character width that depends on the face.

Leading follows from measure, not from a global setting. A long measure needs more
leading to keep the return sweep findable; a short one needs less or the lines
stop reading as a block. `typescale.py` computes it per step. Body text under 1.4
crowds descenders into the next line and fails the text-spacing criterion the
moment anybody overrides it — `S-TYPE-LEADING` catches it, and exempts display
sizes, where tight leading is correct.

Display type inverts every rule here. At 48px, 1.1 leading is right, negative
tracking is right, and the measure wants to be short enough to break where you
choose — which is what `text-wrap: balance` is for. `S-CRAFT-BALANCE` flags a file
full of headings with none.

## Tracking

Tracking is a function of size. Large type needs it tightened, small type needs it
opened, and a single global letter-spacing is wrong at both ends.
`S-TYPE-TRACKING` and `S-TYPE-TRACKING-WIDE` flag the two directions. The one
place wide tracking earns its keep is short uppercase labels, where it repairs
some of what uppercase destroys.

Which is the other thing: uppercase removes word-shape, one of the cues fluent
readers rely on. Fine for a two-word label, punishing for a sentence.
`S-TYPE-ALLCAPS` fires on uppercase at body sizes.

## Families

Three families is the ceiling, and two is usually right: a display face and a text
face, with a mono where the product shows code, identifiers or aligned figures.
`S-CRAFT-FAMILIES` counts them.

A second family earns its weight by being legible as a *different voice*. Two
neo-grotesques — Inter and Manrope, say — read as one family rendered
inconsistently, and you have paid a font load for nothing. Take the contrast, or
drop to one family and carry the hierarchy on weight and size, which is cheaper
and usually better:

```bash
python3 scripts/fontindex.py --pair "Fraunces" "Inter"
```

**And check that the face exists.** The quietest failure in this whole domain: the
contract names a face, the scale and leading are tuned for it, the CSS asks for
it, and nothing in the repository provides it. The browser falls back silently and
every judgement downstream is about a typeface nobody chose.
`S-CONTRACT-FONT-AVAIL` catches it; `fontindex.py` explains it.

## The floor

Body text at 16px on the web. Not because 16 is sacred, but because it is the
browser default and the size every reader's zoom preference is calibrated
against — a 14px body means everyone who has adjusted their browser gets something
smaller than they asked for. `S-TYPE-TINY` flags text under the floor and
`S-TYPE-CRAMPED` flags the combination of small size and tight leading, which is
worse than either.

Text has to survive 200% zoom (`R-ZOOM`) and a text-spacing override
(`R-TEXTSPACING`) without clipping. Both are WCAG criteria and both are failed by
the same thing: a fixed-height container around text.

## Justification, and edges

Justified text on the web produces rivers, because browsers do not hyphenate
well enough to avoid them. `S-TYPE-JUSTIFY` flags it. And a text container with no
horizontal gutter puts the first and last characters under the phone's screen
curve and the holding thumb — `S-TYPE-EDGE`, 16px minimum.

## Adjudicated by

`S-CRAFT-TYPE-FLAT` · `S-CONTRACT-TYPE-SCALE` · `S-CONTRACT-FAMILY` ·
`S-CONTRACT-FONT-AVAIL` · `S-CRAFT-FAMILIES` · `S-CRAFT-HERO-SCALE` ·
`S-CRAFT-BALANCE` · `S-TYPE-LEADING` · `S-TYPE-MEASURE` · `S-TYPE-TRACKING` ·
`S-TYPE-TRACKING-WIDE` · `S-TYPE-ALLCAPS` · `S-TYPE-TINY` · `S-TYPE-CRAMPED` ·
`S-TYPE-JUSTIFY` · `S-TYPE-EDGE` · `R-MEASURE` · `R-ZOOM` · `R-TEXTSPACING`

Tools: `scripts/typescale.py`, `scripts/fontindex.py`.
