# operate — depth for product surfaces, and notes for reading surfaces

When design serves the product: application UIs, dashboards, settings, data
tables, tools, anything behind a login where the user is in a task.

Derived from impeccable's `operate` (Apache-2.0) — see NOTICE.md.

## The product slop test

Familiarity is a feature here. The test is whether a category-fluent user can
trust the interface immediately, or has to pause at every subtly-off component.

Product UI's failure mode is not flatness — it is strangeness without purpose:
over-decorated buttons, mismatched form controls, gratuitous motion, display faces
where labels belong, invented affordances for standard tasks. The bar is earned
familiarity. The tool should disappear into the task.

## Type

One family is usually right. A product UI does not need a display pairing: a
well-tuned sans carries headings, buttons, labels, body and data. Use the calm
ratio — `typescale.py --mode operate` gives 1.25, and there are more type
elements here than on a brand surface, so exaggerated contrast is noise.

Fixed rem steps, not fluid. Users view at consistent DPI, and a `clamp()` heading
that shrinks inside a sidebar looks worse rather than responsive. Prose still
wants 45–75ch; data and compact UI can run denser, and a table at 120ch is fine.

## Colour

Restrained is the floor. One surface can earn a committed treatment — a dashboard
where one category colour carries a report, a welcome screen — but the accent is
spent on primary actions, current selection and state, never on decoration.

What product UI needs and brand surfaces do not is a **state vocabulary**:
default, hover, focus, active, disabled, selected, loading, error, warning,
success, info. Standardise all eleven. Shipping half of them is the most common
defect in this category, and `S-VIS-STATE-COVERAGE` looks for it.

A second neutral layer for sidebars, toolbars and panels, slightly cooler or
warmer than the content surface, does more for legibility than any accent.

## Layout and components

Responsive behaviour is **structural** — collapse the sidebar, make the table
responsive, change the column count — not fluid typography.

- Skeletons for loading, not a spinner in the middle of content.
- Empty states that teach the interface, not "nothing here" (UX-001).
- Consistent affordances: the same button shape, the same form-control vocabulary,
  the same icon style. `M-JUDGE-CONSISTENCY` asks you to open the same action in
  two places and confirm it behaves the same way.
- Overlays escape their container. An absolutely positioned dropdown inside an
  `overflow: hidden` ancestor is clipped; use `<dialog>`, the popover API,
  `position: fixed` or a portal.
- Density is a task decision (VIS-009). Load a representative number of real
  records and count what fits — `M-JUDGE-DENSITY` is that question.

## Motion

150–250ms on most transitions, well inside the 120–240ms band for
micro-interactions (NUM-018). Motion conveys state: change, feedback, loading,
reveal. Nothing else.

No orchestrated page-load sequence. A product loads into a task and nobody wants
to watch it arrive — `S-CRAFT-MOTION` counts entrance moments and one is the
ceiling.

## Read surfaces

Documentation, guides, long-form. Take the typography and consistency rules above
and raise the priority of two things: prose measure (NUM-016, and `R-MEASURE`
measures the rendered result) and navigation — where am I in this document, and
how do I get to the next part. Component density matters far less.

## Verify

```bash
python3 scripts/ux_check.py .
bash scripts/ux_browser.sh          # the state probes are the point here
```

The forced states are what distinguishes an audited product surface from a
described one: abort a request and find out whether the spinner is immortal.

Next: [polish.md](polish.md).
