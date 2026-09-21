---
description: Put a selection overlay into the running app so a person can click what is wrong, and capture it as a request that names an operation and an element.
argument-hint: "[url]"
---

Invoke the `deluxui` skill and read `references/ops/live.md`.

```bash
agent-browser open ${1:-http://localhost:5173}
python3 scripts/ux_select.py watch
```

Then hand the browser to the person and **wait**. Hovering outlines an element;
clicking captures it and asks what is wrong with it in the operations' own
vocabulary — `bolder`, `quieter`, `distill`, `clarify`, `layout`, `space`,
`colorize`, `typeset`, `polish`, or `broken` for a defect rather than a
preference.

Each answer lands in `.deluxui/requests/REQ-NNN.yaml` with the selector, the
element's text, its computed type, colour, spacing, radius and shadow, its box and
the viewport it was seen at. That is enough to find it in the source without
guessing which card they meant.

Then, per request: read `references/ops/<action>.md`, make the change **in the
source** — not in the DOM — let the dev server reload it, and measure what moved:

```bash
bash scripts/ux_live.sh ${1:-http://localhost:5173}
```

The delta names what regressed, what stopped running, what was fixed and what is
still failing. A check that stopped running is never counted as a fix.

Nobody pointing at anything is NOT_RUN, not agreement.
