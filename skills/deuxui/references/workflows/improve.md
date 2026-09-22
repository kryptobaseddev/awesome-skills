# improve — polish, redesign, simplify, harden the look

The request sounds like permission to change everything. It is not.

## 1. Lock the identity first

Follow `references/preserve.md`. Write the identity sentence in observable values
before you touch anything. Then decide preserve or depart — and remember the default
is preserve, because the cost of being wrong is not symmetric.

## 2. Capture a baseline

```bash
agent-browser open <url> && agent-browser screenshot .deuxui/reports/baseline.png
```

Then pass it back on the way out — `ux_browser.sh <url> --baseline .deuxui/reports/baseline.png`
— and `R-BASELINE-DIFF` reports the actual pixel difference. Without a baseline it reports
NOT_RUN and names the path it looked for, and you have no way to show that the parts you
were not asked to change did not move.

The detector reports the number and does not set a threshold. How much movement was the
change you asked for is your call; what it removes is the option of not knowing.

## 3. Find out what is actually wrong

```bash
python3 scripts/ux_check.py <path> --json > .deuxui/reports/static.json
bash scripts/ux_browser.sh <url> --routes <routes> --api '**/api/**'
```

Work from findings, not impressions. "The spacing feels off" is usually one of three
things, and they are not equally checkable — which is worth knowing before you go looking:

| Diagnosis | What can decide it |
|---|---|
| Values off the spacing scale | `S-TOKEN-ARBITRARY` measures it. Arbitrary escapes per file are the one design-coherence signal that separates disciplined codebases from sprawling ones by roughly 10x. |
| Groups spaced the same as their contents | **No detector.** The proximity law (LAW-04) describes it, and nothing reads the laws yet. Look at it at 320px and at your widest viewport, where the failure is most visible. |
| Optical misalignment | **No detector, and no definition in this skill.** An icon or a round shape can sit on the geometric centre and read as off-centre. Only a person looking can call it. |

So: one of the three is measured and two are yours. Squinting is the instrument for the
second and third — say which one you used, and do not report the other two as checked.

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
