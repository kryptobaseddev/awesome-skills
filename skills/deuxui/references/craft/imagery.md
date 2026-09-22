# Imagery

## Flat or plate — the decision that changes what gets built

A region of a design is one of three things, and which one is a fact about the
pixels rather than a preference:

| Medium | What it is | How it ships |
|---|---|---|
| `flat` | Few colours, hard edges, semantic content | CSS and markup |
| `plate` | Many colours, high edge density — a photograph, a figure, a texture | A raster |
| `mixed` | A plate beside or behind flat content | Both, composited |

```bash
python3 scripts/comp_spec.py reference.png       # palette, regions, and the medium of each
```

Getting this wrong in the flat→plate direction wastes effort: a forty-vertex
`clip-path` reproducing a torn paper edge is a week of work and a maintenance
burden for something a 12KB PNG does better. Getting it wrong the other way is
worse: shipping a screenshot of a table is text that cannot be selected,
translated, searched, resized or read aloud.

And a plate quietly rebuilt as a gradient is not an optimisation — it is a
deletion of the design somebody approved. If the plate cannot be produced, that is
a scope decision for the person who approved it, not a silent flattening
afterwards.

## Never rasterise interface text

Text in an image cannot be read by a screen reader, cannot be selected, cannot be
translated, does not reflow, does not scale with the reading size, and fails
`A11Y-007` the moment anybody checks. This applies to headings in hero images,
labels on diagrams, and the numbers on a chart.

The exception is a photograph that happens to contain text — a shop sign in a
street scene — which is content, not interface. The test is whether a user needs
the text to use the product.

## Every image has a job, and most of them do not have one

A stock photograph of people at a laptop is a placeholder that shipped. It tells
the reader nothing, costs 200KB, and is the single loudest signal that nobody
looked at the page. If an image is not carrying information — this is the product,
this is the person, this is the place, this is the data — the page is better
without it.

`S-SLOP-COPY` catches the textual version of the same failure (lorem, "Your
Company"), and `M-CONTENT-REVIEW` asks a person to confirm the imagery is the
product's own.

## The mechanics that are always wrong first

- **Intrinsic size.** An `<img>` with no `width`/`height` or `aspect-ratio`
  reflows the page when it loads, and that is measured directly as CLS.
  `S-PERF-IMGDIM`, `R-VITALS`.
- **Alt text.** Decorative images take `alt=""`; informative ones describe the
  information, not the picture. "Chart" is not alt text; "Revenue by quarter,
  rising from £1.2M to £3.4M" is. `S-A11Y-ALT`.
- **Format and size.** A 4000px hero served to a 390px phone is four seconds of
  someone's data plan. `srcset`, modern formats, and a real budget.
- **Text over an image** has no fixed contrast, because the contrast depends on
  the pixels behind each glyph. A dark scrim rescues it; measuring it is the only
  way to know. `R-PIXEL-CONTRAST` reads the painted result.
- **Video needs captions** (`S-MEDIA-CAPTIONS`) and must not autoplay with sound;
  text over video has the same contrast problem as text over a photograph, worse
  because it moves. `S-VIDEO-LEGIBILITY`.

## Provenance travels inside the file

A generated image with no record of where it came from is an asset nobody can
account for six weeks later — not for authorship reasons but for practical ones:
nobody can regenerate it, vary it, or tell whether it still matches the contract.

```bash
python3 scripts/comp_spec.py plate.png --provenance "generated: <exact prompt>"
python3 scripts/comp_spec.py plate.png --read-provenance
```

`ux_image.py generate` writes this automatically — provider, model, option, brief
hash, contract hash and the full prompt — into a PNG `tEXt` chunk, so it survives
being moved and cannot be separated from the file. `A-COMP-CONFORM` reports its
absence.

## Adjudicated by

`S-A11Y-ALT` · `S-PERF-IMGDIM` · `S-MEDIA-CAPTIONS` · `S-VIDEO-LEGIBILITY` ·
`S-SLOP-COPY` · `R-PIXEL-CONTRAST` · `R-VITALS` · `A-COMP-CONFORM` ·
`M-CONTENT-REVIEW`

Tools: `scripts/comp_spec.py`, `scripts/ux_image.py`.
