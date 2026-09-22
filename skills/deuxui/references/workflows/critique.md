# critique — read-only review

**Change nothing.** This mode produces a judgement, not a diff. It is also the right
default when a request is ambiguous: reviewing is never the wrong first move.

## Run

```bash
python3 scripts/ux_check.py <path> --json > .deuxui/reports/static.json
python3 scripts/ux_check.py <path> --max 60          # readable, P0 first
bash scripts/ux_browser.sh <url> --routes <routes> --api '**/api/**'   # if it runs
```

## Keep the evidence and the judgement apart

Produce the deterministic findings first, then form your own opinion, and keep the
two visibly separate in the report. Detector output is accurate but it anchors
judgement — if you read "41 failures" first, you will write a review about those 41
things and miss that the flow asks for a credit card before explaining the price.

If you have subagents, have one read the code and one read the detector output
without seeing each other's conclusions. If you do not, say so in the report rather
than pretending the separation happened.

## What to look at that no detector can

- Does the primary task have a visible path from the entry point?
- Does the hierarchy survive real content — the longest name, the empty list, the
  account with 400 rows?
- Is anything consequential disclosed *after* the commitment rather than before?
- Does the copy say what happened, or does it say "Something went wrong"?
- Is there an action here that cannot be undone and has no confirmation?
- Would this be usable if you could not see colour? If you could not use a mouse?

## Report

Lead with the P0 and P1 findings and the counts, then your qualitative read, then
what was not checked. Order by severity, not by file. Offer to fix; do not fix.
