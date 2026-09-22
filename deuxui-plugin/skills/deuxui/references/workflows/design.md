# design — originate a visual world (greenfield)

For work with no established design to preserve: a new product, a new surface in a
product that has no system yet, or a deliberate reset the user asked for.

The output is not a screen. It is **a world plus a contract**, and then a screen built
from them. Skipping to the screen is how a project ends up with four visual languages and
nobody able to say which is correct.

## 1. Decide who this is for and what they came to do

Read `.deuxui/PRODUCT.md`, or write it (`init`). Then pick the visitor mode —
`references/design/visitor-modes.md`. Everything downstream inherits from it, and getting
it wrong makes the craft irrelevant: a beautifully typeset dashboard that reads like a
landing page has failed at the only thing it was for.

## 2. Commit to a world, in observable values

One sentence a reader could check you against:

> Warm paper ground, one serif display voice against a grotesque body, ink-black text,
> a single accent at `oklch(0.55 0.18 25)`, depth by border only.

"Modern and clean" is not a world. It names nothing, commits to nothing, and cannot be
wrong — which is exactly why it gets written.

Where the world comes from, in order: what the user said; what the product *is* (a
clinical tool and a music app do not get the same ground); what the domain expects and
where departing from it is the point. Pick the hue from meaning, never from category
reflex — blue because it is software is not a decision.

## 3. Write the contract before the code

Copy `assets/templates/design.contract.yaml` to `.deuxui/design.contract.yaml` and fill
it: type roles and families, colour roles and ramp steps, one depth metaphor, the
elevation set, spacing base, radii, grid, motion band.

**This ordering is the whole point.** A contract written afterwards describes whatever got
emitted, always shows conformance, and is worth nothing. Written first, it is the thing
every later check compares against — and it is what makes "does this belong to the
system?" a question with an answer.

Leave anything you have not decided as `UNKNOWN`. It reports NOT_RUN, which is true.
Filling it in to quieten the report is the one move this skill exists to prevent.

For colour, work in OKLCH: lightness and chroma move predictably, which is what lets a
ramp stay coherent. Reduce chroma near white and black rather than holding it constant to
make the numbers tidy.

## 4. Build the primitives first

Not the page — the vocabulary the page is made of. Surface, text, action, field, and the
one or two components the primary task actually needs. Each one gets a component contract
(`assets/templates/component-contract.md`): semantic role, accessible name, every reachable
state, the keyboard pattern.

Semantics, then states, then looks. In that order, because built the other way round the
states get retrofitted and the semantics never arrive.

## 5. Compose the surface

Now the screen. One thing is primary per viewport. Vary spacing for rhythm — tight groups,
generous separation, more space above a heading than below it. Let the content set the
shape rather than pouring it into same-size cards.

## 6. Verify against what you declared

```bash
python3 scripts/ux_check.py <path>          # craft floor + contract conformance
bash scripts/ux_browser.sh <dev-url> --api '**/api/**'
python3 scripts/ux_report.py --merge
```

New work has no excuse for unforced states: you built it, so you know where its data comes
from. Force the empty, failed and offline paths and look at them.

Then read the report against the contract. A conformance FAIL here is not a style
disagreement — it is a value that escaped a system you yourself declared ten minutes ago,
and the fix is either to use the declared value or to record it in `departures` with a
reason a reader can weigh.
