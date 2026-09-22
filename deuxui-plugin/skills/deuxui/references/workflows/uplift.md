# uplift — raise an existing design (brownfield)

For a product that already has a design. The job is to make it better **without
replacing it**, which is a different and harder task than designing something new.

The failure mode is not ugliness. It is an agent redesigning a mature product into a
collage of generated screens, because creating is easier than reading what is there.

## 1. Derive the contract from the code, not from taste

This is the step that makes everything after it checkable, and it runs before any edit.

```bash
python3 scripts/derive_contract.py <project>            # read it, do not write yet
python3 scripts/derive_contract.py <project> --write    # writes .deuxui/design.contract.yaml
```

This reads the real font sizes, families, radii, shadows, durations and colour roles and
reports the **dominant** value of each with the spread beside it. It reports what it
found; it does not decide. Anything it cannot determine is left `UNKNOWN`, which reports
NOT_RUN downstream — true, where a plausible default would quietly become the standard
the product is judged against.

**Then edit it, and this is the part that matters.** A project with ten type steps does
not have a ten-step scale, it has a scale plus drift. Every step you leave in becomes a
value the product is measured as conforming to, so delete the drift before you commit the
file. The spread report tells you which is which: a size used 307 times is the scale, one
used twice is not.

Deriving it from the existing product is what puts the source of truth outside you. A new
component that departs from it is then measurably a departure rather than a matter of
opinion — and that is the entire difference between design review and design argument.

Where the existing system is inconsistent, record the **dominant** value and note the
spread. That inconsistency is usually the thing worth fixing, and now it is visible.

## 2. Lock the identity

Follow `references/preserve.md`. Write the identity sentence in observable values before
touching anything, then decide preserve or depart — and the default is preserve, because
the costs are not symmetric. Being wrong about preserving costs a conservative variant,
which is recoverable. Being wrong about departing rewrites someone's product in a style
they never asked for, which is not.

Departure needs an explicit request, or a `PRODUCT.md` anti-reference aimed at this
surface. "It looked dated to me" is not either of those.

## 3. Capture a baseline

```bash
agent-browser open <url> && agent-browser screenshot .deuxui/reports/baseline.png
```

Pass it back with `--baseline` on the way out. `R-BASELINE-DIFF` then reports the actual
pixel difference, which is how you show that the parts nobody asked you to change did not
move. It reports the number and sets no threshold: how much movement was the change you
were asked for is your call.

## 4. Find what is actually wrong

```bash
python3 scripts/ux_check.py <project> --json > .deuxui/reports/static.json
bash scripts/ux_browser.sh <url> --routes <routes> --api '**/api/**'
```

Work from findings, not impressions. With the contract in place the report now separates
three different things, and they have different fixes:

- **Contract escapes** (`S-CONTRACT-*`) — a value outside the declared system. Usually the
  cheapest real win, and the one that most changes how coherent the product feels.
- **Craft floor** (`S-CRAFT-*`) — mechanics below the bar: flat type scale, two depth
  metaphors, unthemed browser surfaces, content hidden at rest.
- **UX defects** (`A11Y-*`, `STATE-*`, `FORM-*`, `TRUST-*`) — the interface failing people.
  These outrank everything above; a beautiful screen that cannot be used by keyboard is
  not a design success with an accessibility problem.

Fix in that reverse order: defects, then floor, then coherence.

## 5. Change the smallest thing that fixes it

Resist the rewrite. Prefer raising the floor across the product to redesigning one screen
beautifully — a consistent product at a good floor beats one excellent page beside twenty
untouched ones, and the second outcome is what an agent produces when it optimises for
the screenshot.

Climb the preserve ladder before writing a new component: `PRESERVE > MODIFY > COMPOSE >
CREATE`, and `--inventory <intent>` tells you what already exists.

## 6. Report what moved and what did not

Re-run the checks, merge, and lead with what was **not** verified. Then state the baseline
diff, and name the things you deliberately left alone — a report that only lists changes
reads as though everything else was examined.
