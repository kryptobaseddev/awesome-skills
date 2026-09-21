# typeset — make type carry information, hierarchy and voice

A ladder of numbers is not a type system. The system is which job each rung does,
and whether the reader can tell two rungs apart.

Derived from impeccable's `typeset` (Apache-2.0); the ladder is generated and
checked here rather than chosen by eye — see NOTICE.md.

## Before you touch anything

If `type.families` is declared in the contract, those families are authoritative.
Replacing them creates a new identity, which is [new-work.md](new-work.md), not
this. Preserve them and improve their use (CTX-005).

```bash
python3 scripts/typescale.py --check .deluxui/design.contract.yaml
python3 scripts/ux_check.py . --detector S-CRAFT-TYPE-FLAT \
        --detector S-CRAFT-FAMILIES --detector S-TYPE-MEASURE \
        --detector S-TYPE-LEADING --detector S-CONTRACT-TYPE-SCALE --json
```

## Two assessments, kept apart

Run the mechanical scan and your own reading **separately**, and do not let the
scan anchor the reading. Answer each of these with a file, a selector or a
computed value:

- **Authority.** Which faces and weights are established? Is every family doing a
  job only it can do? Three is the ceiling (`S-CRAFT-FAMILIES`) and most systems
  need two.
- **Hierarchy.** Can heading, body, label, metadata and data be told apart at a
  glance, without reading the words?
- **Reading.** Is body copy in the 45–75ch band (NUM-016)? Is leading tuned to
  the measure and the face, or to a habit?
- **Stress.** Long headings, localisation expansion, 200% zoom, a narrow
  container, a missing weight, the fallback face.
- **Delivery.** Only used assets loaded, metric-compatible fallbacks, no
  invisible text and no disruptive reflow (PERF-002).

A clean scan is a floor, not proof of good typography.

## Build the ladder

```bash
python3 scripts/typescale.py --mode operate --body 16 --measure 45,75
python3 scripts/typescale.py --mode operate --contract   # commit it
python3 scripts/typescale.py --mode operate --css        # the properties
```

Every step clears the 1.25x minimum by construction, so two roles can always
carry two jobs. Leading falls as the measure narrows; tracking tightens at
display sizes and opens at caption sizes. A rung that would land under the 12px
floor is dropped and said so, because a role nobody can read is not a role.

Then apply the parts a generator cannot:

- Light text on a dark surface needs compensating on all three axes — a little
  more leading, a touch more tracking, one step more weight if the face needs it.
- Use paragraph spacing **or** first-line indent. Both double-marks the boundary.
- Numeric, tabular and code features where the content benefits.
- Preserve zoom, user font settings, Dynamic Type (IOS-005) and the Android font
  scale (AND-007). Type that ignores the reading size the user chose fails the
  reader who most needed it.

## The face has to exist

The quietest failure in this whole operation: the contract names a face, the scale
and the leading are tuned for it, the CSS asks for it, and nothing in the
repository provides it. The browser falls back silently, and every type decision
downstream was made about a typeface this product does not render.

```bash
python3 scripts/fontindex.py .            # what the project provides, and what it only names
python3 scripts/fontindex.py . --check    # exit 2 when a declared family is missing
python3 scripts/fontindex.py --pair "Fraunces" "Inter"
```

It looks for all five ways a face legitimately arrives — an `@font-face` rule, an
`@fontsource` package (imported or in the manifest), `next/font`, a font file in
the tree, and a Google Fonts request — and matches across spellings, so `Söhne` in
the contract resolves to `sohne-web-buch.woff2` on disk.

One thing it refuses to do: treat the faces installed on the build host as
evidence that a visitor has them. A build host's font list describes the build
host. `S-CONTRACT-FONT-AVAIL` is the detector; `VIS-010` is the rule.

## Verify

| Detector | What it settles |
|---|---|
| `S-CONTRACT-TYPE-SCALE` | Sizes in the code are on the declared ladder (VIS-002, NUM-015). |
| `S-CRAFT-TYPE-FLAT` | Adjacent roles differ enough to carry different jobs. |
| `S-CRAFT-FAMILIES` | At most three families. |
| `S-CRAFT-HERO-SCALE` | Display type under the 6rem ceiling. |
| `S-TYPE-TINY`, `S-TYPE-LEADING`, `S-TYPE-MEASURE` | Floor, leading, measure. |
| `S-TYPE-ALLCAPS`, `S-TYPE-JUSTIFY`, `S-TYPE-TRACKING-WIDE` | Habits that cost reading. |
| `R-MEASURE`, `R-ZOOM` | The rendered measure, and the layout at 200%. |

Hand off to [polish.md](polish.md).
