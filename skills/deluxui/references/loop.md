# The execution loop

The loop exists because each step prevents a specific defect from shipping. It is
not a ritual, and it scales down: a copy change does not need the runtime tier. What
does not scale down is the reporting rule — whatever you skipped, say you skipped it.

## 1. Orient

```bash
python3 scripts/ux_check.py <project> --signals
```

You are looking for: the framework and its major version, whether Tailwind is v3 or
v4, where theme variables live, how many components already exist, whether an i18n
setup is present. Then read `.deluxui/PRODUCT.md` and `.deluxui/DESIGN.md` if they
exist; run `workflows/init.md` if they do not.

Reading the project first is what separates a change from a rewrite.

## 2. Classify the surface and the task

Ordinary DOM, a 3D canvas, or a rendered video? They do not share rules — a Remotion
composition has no hover, no focus and no zoom, so applying interaction rules to it
would produce confident nonsense. The checks classify automatically; you should know
too, because it changes what "good" means.

Then pick a mode from the table in `SKILL.md` and read that one workflow file.

## 3. Select the applicable rules

Not all 190 apply. Feature-gated rules (payments, uploads, drag, charts, AI output)
are `NOT_APPLICABLE` unless the product has the feature — declare what it does have
with `--feature` so the gate counts honestly.

For anything consequential, look up the rule text rather than working from memory:
`references/rules/` is organised by domain, and every rule carries its source.

## 4. Apply the preserve ladder

`PRESERVE > MODIFY > COMPOSE > CREATE`. Ask the inventory before you write a
component. Record what you reused, or why nothing fit. Full reasoning in
`preserve.md`.

## 5. Implement

Build semantics and state transitions before decoration. Concretely: the element's
role, name and keyboard behaviour first; then every state it can reach; then how it
looks. Done the other way round, the states get retrofitted and the semantics never
arrive.

If the project ships headless primitives (Radix, Base UI, Headless UI, Ark, React
Aria), compose them. Focus containment and typeahead are harder than they look and
you will not get them right by hand.

## 6. Static tier

```bash
python3 scripts/ux_check.py <path> --json > .deluxui/reports/static.json
```

Fast, heuristic, source-only. It finds missing labels, removed focus rings, hover-only
reveals, absent empty states, unguarded submits, hardcoded colours and the AI tells.
It cannot see computed styles or anything that only exists at runtime — treat a PASS
here as "no source evidence of a defect", not as a verified pass.

## 7. Runtime tier

```bash
bash scripts/ux_browser.sh http://localhost:5173 --routes /,/settings --api '**/api/**'
```

This is where the real measurements happen: contrast against the actually painted
backdrop, hit areas from real layout boxes, focus rings compared before and after
focus, reflow across the viewport matrix, 200% text, the text-spacing override, Core
Web Vitals — and the forced states.

**Pass `--api`.** Without it the aborted, empty and offline probes never run, and
those three find more real defects than everything else combined. The pattern is a
glob against request URLs, e.g. `'**/api/**'` or `'**/rest/v1/**'` for Supabase.

## 8. Fix, then re-run

Fix the P0 and P1 failures first; they are ordered that way in the output. Re-run the
tier you changed. A fix you did not re-verify is a hypothesis.

If a finding is wrong, it is a bug in the check, not a nuisance to route around. Fix
the check, add the case to `scripts/checks/fixtures/`, and run `scripts/selftest.py`.
A checker people learn to ignore is worse than no checker.

## 9. Report

```bash
python3 scripts/ux_report.py --merge --feature forms > .deluxui/reports/agent_report.yaml
```

Lead with what was not checked. The gate returns BLOCKED, CONDITIONAL or READY, and
in `--release` mode an unchecked P0 rule blocks — because for a safety rule, not
knowing and not passing are the same position to ship from.
