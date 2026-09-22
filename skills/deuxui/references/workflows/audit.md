# audit — the full matrix and the gate

The mode that answers "is this ready". It is the only mode where NOT_RUN blocks, and
that is the whole point of it.

## 1. Declare what the product has

Feature-gated rules are `NOT_APPLICABLE` unless you declare the feature. Declaring
honestly is what keeps the matrix meaningful — inflating the applicable set to look
thorough is as dishonest as suppressing it.

```
forms  authentication  payments_or_legal  destructive_actions  charts  tables
uploads  drag_interactions  search_or_filter  pagination  bulk_actions  modals
i18n  offline_or_drafts  media  ai_features  measurement_program  ios  android
```

## 2. Run all three tiers

```bash
python3 scripts/ux_check.py <path> --json > .deuxui/reports/static.json

bash scripts/ux_browser.sh <url> \
  --routes /,/settings,/billing --api '**/api/**' \
  --out .deuxui/reports/runtime

# record the manual results a machine cannot produce
$EDITOR .deuxui/reports/manual.yaml      # see verification/manual-checks.md
```

Route coverage matters more than route count. Include: the primary task, one dense
data view, one form, and every screen with an irreversible action.

## 3. Merge and gate

```bash
python3 scripts/ux_report.py --merge --release \
  --feature forms --feature payments_or_legal --feature destructive_actions \
  > .deuxui/reports/agent_report.yaml
```

| Decision | Meaning |
|---|---|
| `BLOCKED` | A P0/P1 rule is failing, or a P0 rule was never checked |
| `CONDITIONAL` | Nothing failing, but P0 rules are unverified |
| `READY` | Every applicable rule checked, none failing |

## 4. Report honestly

Lead with `counts.not_run`. An audit that reports 38 failures and 84 unchecked rules
is a useful document. An audit that reports 38 failures and implies the other 152
passed is a false one.

State the scope explicitly: which routes, which viewports, which tiers, which
browser. A changed-component audit does not make an application conformant, and an
automated scan covers a minority of the WCAG criteria (A11Y-014, GOV-009). Say so.

## Exceptions

A deviation goes in `.deuxui/exceptions.yaml` using `assets/templates/exception.md`:
rule ID, scope, reason, alternatives considered, user impact, compensating controls,
owner, review date. An exception may lower a **PROJECT**-class rule. It may not make
a failed **STANDARD** report as passing — that one stays visible in the matrix.
