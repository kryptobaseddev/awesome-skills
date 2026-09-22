# craft — the floor, and what it does not tell you

`craft` is the shortest operation here because it is a gate, not a job: run the
craft floor, read the sixteen results, fix what they name.

```bash
python3 scripts/ux_check.py . --json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); \
   [print(f\"{v['status']:<8}{k}\") for k,v in sorted(d['detectors'].items()) \
    if k.startswith('S-CRAFT-')]"
```

The full statement of each threshold, and why it is where it is, lives in
[../design/craft-floor.md](../design/craft-floor.md). The numbers are in
`references/rules/thresholds.yaml` and every one is overridable by a project that
genuinely chose a different bar — with a reason on the record.

## The floor is a floor

Everything green here means the mechanics are not in the way. It says nothing
about whether the design is any good, and a detector that implied otherwise would
be lying. What the floor catches is the set of habits that make an interface read
as assembled rather than built: type roles too close to tell apart, three
families where two would do, a coloured glow standing in for depth, a zero-blur
shadow, an easing curve nobody chose, sixteen surfaces, a z-index of 9999.

What it cannot catch is in [polish.md](polish.md)'s manual tier and in the eleven
`M-JUDGE-*` questions. Those are where taste lives, and the honest handling of
taste is a question somebody answers — not a threshold pretending to settle it.

## The second-order reflex

The floor names the obvious tells. It is equally possible to fail by reaching for
the obvious anti-tell: refusing all gradients, all shadows, all motion, and
arriving at a different template. A world that chose a gradient and recorded it
in `departures:` is a decision. A codebase with no gradients because a checker
mentioned them is a different kind of absence, and no better.

Next: [colorize.md](colorize.md), [typeset.md](typeset.md), [layout.md](layout.md), [animate.md](animate.md).
