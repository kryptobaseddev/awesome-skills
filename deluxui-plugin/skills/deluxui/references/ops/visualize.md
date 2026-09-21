# visualize — render the direction before building it

Three high-fidelity comps of a surface, so a structural decision is made against
something visible rather than described.

Derived from impeccable's `visualize` and `generate-image` (Apache-2.0), with the
comp bound to the contract in both directions: generated from it, then measured
back against it — see NOTICE.md.

## Three ways to get a comp, and they are not alternatives

**1. Render it from the contract.** Needs no model, no key and no network, so it
is always available — and because every fill is a declared role, every size a
declared rung and every radius a declared value, the sheet is conformant by
construction and cannot be the thing that drifts.

```bash
python3 scripts/ux_image.py brief --write .deluxui/comps/detail.brief.yaml --surface "listing detail"
# edit the regions, then:
python3 scripts/ux_image.py render .deluxui/comps/detail.brief.yaml
```

Each sheet carries a caption block under the surface: the option's title, what it
decides, and the region table — name, medium, share, what it holds. A comp shown
without its structural claim gets approved for its atmosphere, and the atmosphere
is not the part the build has to honour.

Where the contract has blanks, the sheet says so on its face, in red, and names
them. Those regions are placeholders, not proposals, and approving the comp does
not decide them.

**2. Generate a raster, where a model is reachable.**

```bash
python3 scripts/ux_image.py providers      # what can generate here, and what is missing
python3 scripts/ux_image.py prompt .deluxui/comps/detail.brief.yaml --option A
python3 scripts/ux_image.py generate .deluxui/comps/detail.brief.yaml
```

Four providers, tried in order and each reporting its own absence: a harness's own
image tool via `DELUXUI_IMAGE_CMD` (a command template with `{prompt_file}`,
`{out}`, `{w}`, `{h}`), the `image-nanobanana` skill if installed beside this one,
the Gemini API directly, and OpenAI. With none of them reachable, generation
reports NOT_RUN and the rendered sheets stand — it never silently produces nothing.

The prompt is built **from the contract**: the palette by role with its values, the
families, the ladder, the radii, the single depth metaphor, what the visitor came
to do, and the regions with their shares and mediums. Not from an adjective. The
result carries its provider, model, prompt, brief hash and contract hash inside the
PNG.

**3. Read a reference image**, which is the half of a comp round a model was never
required for:

```bash
python3 scripts/comp_spec.py shot.png              # palette, regions, mediums
python3 scripts/comp_spec.py shot.png --contract   # the colour block, sampled
```

Point it at a screenshot of the existing product — `agent-browser screenshot
--full` writes exactly the form it reads — and it reports the palette by coverage,
the canvas and ink with the measured ratio between them, where the horizontal
rhythm changes, and **which bands are photographic rather than flat**.

That last column is the one that changes what gets built. A band with many colours
and many edges is a `plate`: a figure, a product, machinery, a named texture. It
ships as a raster. Writing CSS for it — or a forty-vertex `clip-path` for a torn
edge — is not an optimisation, it is a quiet deletion of the design somebody
approved, and dropping an image-native region is a scope decision the user makes
at the approval point rather than a silent flattening after it.

## Measure what came back

This is the half a generator alone never does. A model returns a beautiful image
in a palette nobody declared, somebody approves it, and from then on the build is
judged against a comp that was never the system.

```bash
python3 scripts/ux_image.py verify .deluxui/comps/listing-detail-A.png
```

Every declared colour role has to be present in the image at real coverage. The
tolerance is computed per colour rather than fixed, because the palette read is
quantised and a flat tolerance loose enough to absorb the quantiser was also loose
enough to let a cool grey pass as warm paper. And direction is checked separately
from distance: a colour that is close in magnitude but the opposite way round the
hue wheel is reported as a different world rather than a near miss. A warm paper
ground and a cool grey one are not interchangeable, and a comp approved in one
will be built in the other.

Provenance travels in the file, not in a sidecar that gets separated from it the
first time somebody moves something:

```bash
python3 scripts/comp_spec.py plate.png --provenance "generated: <exact prompt>"
python3 scripts/comp_spec.py plate.png --read-provenance
```

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

## Then serve the choice

```bash
python3 scripts/ux_question.py ask .deluxui/comps/listing-detail.comps.yaml
```

See [decide.md](decide.md). Until somebody has chosen, the phase gate refuses UI
edits — see [phase.md](phase.md).

## Verify

Once built, the comp's promises become the contract's:

```bash
python3 scripts/ux_check.py .        # the S-CONTRACT-* rows
```

If the built screen conforms and the comp did not, the comp was the thing that
drifted. Record it under `departures:` or bring it back.
