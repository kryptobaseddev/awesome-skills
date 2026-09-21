# harden — accessibility, states, and the actions you cannot undo

Use when the interface works for the person who built it and needs to work for
everyone else, and every path through it.

## Accessibility

```bash
python3 scripts/ux_check.py <path> --detector S-A11Y-LABEL --detector S-A11Y-ICONBTN \
        --detector S-A11Y-DIVCLICK --detector S-FOCUS-OUTLINE --detector S-A11Y-NESTED
bash scripts/ux_browser.sh <url> --routes <routes>
```

The runtime tier settles what source cannot: `R-CONTRAST` measures against the
actually painted backdrop, `R-TARGET` measures real hit areas including the SC 2.5.8
spacing exception, and `R-FOCUS-WALK` focuses every control and compares its computed
style before and after — which is the only reliable way to find a focus ring that is
technically present and visually absent.

Then do the part no machine does. `references/verification/manual-checks.md` has the
procedure: one keyboard-only pass through the primary task, one screen-reader pass,
one pass with colour ignored. Record the results, or they are NOT_RUN.

## States

```bash
bash scripts/ux_browser.sh <url> --routes <routes> --api '**/api/**'
```

This forces the aborted request, the empty payload and the offline case, then checks
whether the interface says what happened and offers a way on. The three failures it
reports most often, in order: a spinner that never resolves, a region that goes blank
with no explanation, and a failure message with no recovery action.

Work through the state table in `references/rules/07-state.md`. The two asymmetries
that matter most: an unknown outcome is not a success, and dismissing a panel is not
cancelling the operation behind it.

## Destructive and irreversible actions

For each one listed in `PRODUCT.md`:

- Does the label say what will actually happen? "Continue" on a payment is COMP-003.
- Is the recipient, amount, currency and consequence visible at the moment of commit?
- Is there an undo? Prefer it — confirmations get clicked through, undo actually
  recovers the mistake.
- Does a double-click commit twice? Guard in the UI *and* deduplicate on the server.
- If the response is lost, does the interface claim success anyway?

## Verify

```bash
python3 scripts/ux_report.py --merge --release --feature destructive_actions \
        --feature forms --feature authentication
```
