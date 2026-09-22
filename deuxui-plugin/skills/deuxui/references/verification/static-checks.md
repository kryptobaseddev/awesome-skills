# The static tier: what it sees and what it cannot

`scripts/ux_check.py` scans source text. It is deliberately a tolerant scanner rather
than a parser — it reads the shape of markup well enough to answer attribute and
nesting questions across JSX, Svelte, Vue, Astro and HTML without a per-framework
toolchain. That trade buys speed and breadth, and costs certainty.

So every finding carries a **confidence**, and the honest reading of a `PASS` here is
"no source evidence of a defect" — not "verified".

## What it genuinely finds

Missing `alt`; icon-only controls with no accessible name; inputs with no label
association; placeholder-as-label; `onClick` on a `div`, `span` or a presentational
wrapper like `Card`; `href="#"` actions; positive `tabindex`; `aria-hidden` over
focusable content; interactive nested in interactive; heading-level skips; removed
focus outlines with no replacement; contrast for resolvable colour pairs; hit areas
expressible from utility classes; lists with no empty branch; async reads with no
error or pending path; submits with no in-flight guard; optimistic updates on
destructive actions with no rollback; missing `autocomplete`; email and phone fields
typed as text; `:invalid` used instead of `:user-invalid`; fixed pixel widths; `100vh`;
missing safe-area insets; tables with no narrow strategy; truncation with no full
value; animation with no reduced-motion path; hover-only reveals; hardcoded colours
where theme variables exist; off-scale spacing; components that duplicate an installed
primitive; undeclared UI dependencies; the AI tells; vague error copy; hand-rolled
money formatting; destructive handlers with no confirm or undo; images with no
intrinsic size; canvases with no text equivalent; 3D canvases with no frame or dpr
budget; video with no captions.

## What it cannot see, at all

- **Computed styles.** A class may be overridden, a variable may resolve elsewhere.
- **Real hit areas.** Padding, line-height, transforms and pseudo-elements all change
  the box. Only layout knows the answer.
- **The actual backdrop behind text.** Contrast against an ancestor guess is a guess;
  against a background image it is unknowable from source.
- **Focus order.** DOM order is not focus order once `order`, `grid-area` or portals
  are involved.
- **Any runtime state.** Whether the error state renders, whether the spinner ever
  resolves, whether the empty state exists in practice.
- **Anything conditional.** Code behind a flag, a role check or a route it did not take.

All of that belongs to `browser-checks.md`, and until you run it those rules are
NOT_RUN.

## Tuning without lying

A check that fires wrongly is a bug in the check. Fix it, add the case to
`scripts/checks/fixtures/`, and run `scripts/selftest.py` — which asserts every check
fires on known-bad source and stays silent on known-good source.

Disabling a check in `.deuxui/ux.config.yaml` is legitimate when it does not apply to
your project. It is not a way to make a real finding go away: the rule still reports,
now as NOT_RUN, which is exactly what it is.

## Using it as an editor hook

```bash
echo '{"tool_input":{"file_path":"src/App.tsx"}}' | python3 scripts/ux_check.py --stdin
```

Reads a PostToolUse payload and scans the one file that changed, so violations surface
while the code is being written rather than at review. Exit `0` clean, `2` findings.
