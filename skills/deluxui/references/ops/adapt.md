# adapt — move a web design to a different context

A different viewport class, input mode, density, locale or surface. The trap is
the same one as in [adapt-native.md](adapt-native.md): treating adaptation as
scaling.

Derived from impeccable's `adapt` (Apache-2.0) — see NOTICE.md.

## Assess first

What was this designed for, and what did it assume? Mouse and hover? A wide
viewport? English? A fast connection? One theme? Each assumption is a rule in this
tool, and the adaptation is the work of removing it.

## Desktop to touch

Hover is the assumption that breaks hardest, because on touch there is no hover
state at all — a control whose affordance only appears on hover has no affordance.

- `S-HOVER-ONLY` finds interactive content revealed on hover with no
  `focus-within` path (VIS-005, COMP-011).
- Targets go from 24px to 44px (NUM-004 to NUM-005), and `R-TARGET-COARSE`
  measures them with a coarse pointer emulated rather than assumed.
- Anything that needs a drag needs a non-drag alternative (SC 2.5.7).
- A tooltip carrying information the user needs is information the user does not
  get. Move it into the interface.

## Wide to narrow

320px is the floor (NUM-009), and the measurement is `R-REFLOW` at 320, 390, 768,
1024 and 1440 rather than a guess at a breakpoint.

Restructure rather than compress: a table becomes a list of records (LAY-006), a
sidebar becomes a sheet, a multi-column form becomes one column. Compressing a
table until the columns are 40px wide is a table nobody can read, and
`overflow-x: hidden` over the top of it is the same defect with the evidence
removed.

## One locale to many

- German compounds are roughly 30% longer and do not wrap where English does.
  This is where hand-tuned layouts come apart, and `M-JUDGE-ALIGNMENT` asks you
  to look at the longest real label.
- RTL is not a mirror: icons with direction reverse, logical properties replace
  `left` and `right`, and numbers do not flip.
- Dates, numbers and currencies get formatted, not concatenated —
  `S-CONTENT-FORMAT` (CONTENT-005, CONTENT-006).
- Hardcoded strings where an i18n system exists is `S-CONTENT-I18N` (CONTENT-004).

## Light to dark

Composed, not inverted. `palette.py --dark` places each role against the dark
canvas rather than flipping lightness, because inversion raises saturation exactly
where it should fall and produces glare. Then declare `color.dark_mode: composed`
and check both appearances — `R-CONTRAST` measures whichever one the browser is
in, so run it twice.

## Verify

```bash
bash scripts/ux_browser.sh http://localhost:5173 --viewports 320,390,768,1024,1440
python3 scripts/ux_report.py --merge
```

The rows that matter here: `R-REFLOW`, `R-TARGET-COARSE`, `R-ZOOM`,
`R-ORIENTATION`, `R-TEXTSPACING`, `R-CONTRAST`. All six are runtime, because none
of them can be established by reading source.
