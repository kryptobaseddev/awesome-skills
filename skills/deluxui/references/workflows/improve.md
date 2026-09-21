# improve — polish, redesign, simplify, harden the look

The request sounds like permission to change everything. It is not.

## 1. Lock the identity first

Follow `references/preserve.md`. Write the identity sentence in observable values
before you touch anything. Then decide preserve or depart — and remember the default
is preserve, because the cost of being wrong is not symmetric.

## 2. Capture a baseline

```bash
agent-browser open <url> && agent-browser screenshot .deluxui/reports/baseline.png
```

Without this, `R-BASELINE-DIFF` reports NOT_RUN and you have no way to show that the
parts you were not asked to change did not move.

## 3. Find out what is actually wrong

```bash
python3 scripts/ux_check.py <path> --json > .deluxui/reports/static.json
bash scripts/ux_browser.sh <url> --routes <routes> --api '**/api/**'
```

Work from findings, not impressions. "The spacing feels off" is usually one of:
inconsistent scale steps, groups spaced the same as their contents (LAW-04), or
optical misalignment. The checks distinguish them; squinting does not.

## 4. Change the smallest thing that fixes it

Resist the rewrite. If the complaint is hierarchy, fix hierarchy — do not also change
the palette because you were in there. Each unrequested change is one the user has to
review, understand and either accept or ask you to undo.

`references/anti-slop.md` is the list of moves to avoid reaching for, plus the
second-order trap of reaching for their opposite.

## 5. Prove you preserved the rest

```bash
agent-browser diff screenshot --baseline
python3 scripts/ux_report.py --merge
```

Report what changed, what you deliberately left alone, and what the diff shows. GOV-004
asks you to preserve existing working behaviour; the diff is the evidence.
