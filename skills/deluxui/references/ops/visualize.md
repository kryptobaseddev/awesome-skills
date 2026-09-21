# visualize — render the direction before building it

Three high-fidelity comps of a surface, so a structural decision is made against
something visible rather than described.

Derived from impeccable's `visualize` (Apache-2.0), reduced to what deluxui can
honestly claim — see NOTICE.md.

## What deluxui does and does not provide

deluxui ships **no image generation**. Where the harness has an image tool, use
it; where it does not, this operation degrades to a described comp — a written
composition per option, region by region — and **says so**. A described comp is
weaker than a rendered one, and pretending otherwise is the failure mode.

What deluxui does provide is the half of impeccable's comp round that needs no
model at all — reading a reference:

```bash
python3 scripts/comp_spec.py shot.png              # palette, regions, mediums
python3 scripts/comp_spec.py shot.png --contract    # the colour block, sampled
python3 scripts/comp_spec.py shot.png --json
```

Point it at a screenshot of the existing product — `agent-browser screenshot
--full` writes exactly the form it reads — and it reports the palette by coverage,
the canvas and ink with the measured ratio between them, where the horizontal
rhythm changes, and **which bands are photographic rather than flat**.

That last column is the one that changes what gets built. A band with many
colours and many edges is a `plate`: a figure, a product, machinery, a named
texture. It ships as a raster. Writing CSS for it — or a forty-vertex `clip-path`
for a torn edge — is not an optimisation, it is a quiet deletion of the design
somebody approved, and dropping an image-native region is a scope decision the
user makes at the approval point rather than a silent flattening after it.

Provenance travels in the file, not in a sidecar that gets separated from it the
first time somebody moves something:

```bash
python3 scripts/comp_spec.py plate.png --provenance "generated: <exact prompt>"
python3 scripts/comp_spec.py plate.png --read-provenance
```

And the comp's palette, type and motion still come from the contract, so a comp
that drifts from the committed world is measurable rather than a matter of
impression.

## Comp at the surface's own viewport

A phone screen comped landscape misstates the composition before anything is
built against it. Portrait at device size for a native or mobile-first surface,
desktop landscape otherwise.

## Three, and what to vary

One comp invites a rubber stamp. Three surface the decision. Vary the
**structural** uncertainty a picture can actually resolve — topology, sequence,
density, hierarchy, focal composition, interaction framing — not the palette three
times. The world is already committed (see [new-work.md](new-work.md)); this round
does not reopen it.

- A comp is a designed **surface**, not a picture of the subject. Lead with the
  regions this design has, named in order with their scale relationships. A prompt
  that leads with atmosphere returns a poster.
- The inverse also fails: a surface with none of its subject in it. The subject
  appears as the content the regions hold.
- The visitor's job must be readable from the image alone, with no caption. If the
  mode cannot be read back, it is art direction without a surface.
- Commitment is depth, not coverage. One dominant move, with the remaining regions
  holding still so it can be read. Two things competing at the same scale is
  shouting.

## One approval point

Show all three together. Ask what carries forward, what feels false to the world,
and whether to approve, combine, revise or reject. Then stop and wait.

Do not begin code until the direction is approved or the choice is explicitly
delegated. If it is delegated, choose from the brief and the contract, state the
evidence, and disclose the delegation in the first reply rather than the last.

## The comp is a north star, not a spec

Keeping the palette and mood while redrawing the topology is a second art
direction, not an implementation. And never rasterise core UI text or controls:
text in an image cannot be read by a screen reader, cannot be selected, cannot be
translated, does not scale with the reading size, and fails `A11Y-007` the moment
anyone checks.

## Verify

Once built, the comp's promises become the contract's:

```bash
python3 scripts/ux_check.py .        # the S-CONTRACT-* rows
```

If the built screen conforms and the comp did not, the comp was the thing that
drifted. Record it under `departures:` or bring it back.
