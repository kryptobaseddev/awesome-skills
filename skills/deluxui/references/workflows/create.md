# create — a new screen, flow or component

## Before writing anything

1. Read `.deluxui/PRODUCT.md` and `DESIGN.md`, or run `init`.
2. Run the inventory. `PRESERVE > MODIFY > COMPOSE > CREATE` applies most strongly
   here, because a brand-new surface is where inventing feels most justified.
   ```bash
   python3 scripts/ux_check.py <project> --inventory "<what you are about to build>"
   ```
3. Name the task in one sentence: who is doing what, and what tells them it worked.
   If you cannot write that sentence, you are not ready to build the screen.

## Write the component contract first

Fill `assets/templates/component-contract.md` before the markup. It takes two
minutes and it is the difference between a component and a picture of one:

- semantic role and where the accessible name comes from
- every state it can reach — default, hover, focus-visible, active, selected,
  disabled, pending, error, empty
- the keyboard pattern, named (APG pattern or a native element)
- what happens when its data is missing, slow, stale or forbidden
- the target-size profile for the platforms you support

## Build in this order

**Semantics, then states, then looks.** Role, name and keyboard behaviour first;
then make every state reachable; then style it. Built the other way round, states get
retrofitted and semantics never arrive at all.

Specifics that repeatedly go wrong:

- Use the native element. `<button>`, `<dialog>` with `showModal()`, the `popover`
  attribute, `<details>`. They bring focus containment, the top layer, Escape and
  `::backdrop` with no code.
- If a headless primitive is installed, compose it instead of hand-rolling.
- Reserve layout space for anything that loads. Space reserved late is measured as CLS.
- Give every list an empty state that says what is missing and offers the first action.
- Give every mutation a pending state and an in-flight guard.
- Give every destructive action either a confirmation or an undo. Prefer undo.

## Verify before reporting

```bash
python3 scripts/ux_check.py <path>
bash scripts/ux_browser.sh <dev-url> --routes <new-route> --api '**/api/**'
python3 scripts/ux_report.py --merge --feature forms
```

New work has no excuse for unforced states: you built the component, so you know
where its data comes from. Force the failure and look at it.
