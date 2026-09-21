---
description: Host two live variants side by side and let a person click any element and say, in their own words, what is wrong — captured as work items the agent reads.
argument-hint: "[A=target B=target]"
---

Invoke the `deluxui` skill and read `references/ops/prototype.md`.

```bash
python3 scripts/ux_review.py serve \
    --variant "proposed=.deluxui/proto/index.html" \
    --variant "current=http://localhost:5173/" \
    --question "Does this work when you use it?"
```

A variant is a URL on a running app or an HTML file, and the server **hosts** both:
a file is served, a URL is proxied, the selection script is injected into each and
the frame-blocking headers are dropped on the way through. Same origin, so a click
inside the frame is readable — no dev-server plugin, no framework adapter, no build
step.

Hand over the URL and **wait**. The reviewer gets the real interface side by side
at whichever width they choose, and **Alt-clicks any element** to type what is
wrong with it. Each note is captured with the element — selector, its own text, its
computed type, colour, spacing, radius, shadow, box and viewport — written to
`.deluxui/requests/REQ-NNN.yaml`, and printed in your terminal as it is written.
Do not wait for a summary; act on them as they arrive.

Five outcomes, and only three are approvals:

| Outcome | Means |
|---|---|
| Accept `<variant>` | Build on this one. |
| Combine | Parts of more than one — the reason says which. |
| **Request changes** | **Not an approval.** The notes are the work list, and `build` stays locked. |
| Reject | Wrong direction. |
| Nobody answers | NOT_RUN. An unreviewed screen is not an approved one. |

Refused: an answer with no author, an author naming you, and a reason too thin to
weigh.

Then fix things **in the source**, not in the DOM — the dev server reloads and the
reviewer looks again:

```bash
python3 scripts/ux_review.py notes --source review
bash scripts/ux_live.sh http://localhost:5173
```
