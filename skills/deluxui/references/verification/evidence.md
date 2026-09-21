# Evidence, statuses and the gate

## The five statuses

| Status | Means | May be claimed when |
|---|---|---|
| `PASS` | Checked, and it met the requirement | A detector ran and found nothing, or a person recorded a passing result |
| `FAIL` | Checked, and it did not | A detector or person found a violation |
| `NOT_RUN` | **Nobody checked** | Always the default. Never a pass |
| `NOT_APPLICABLE` | The product does not reach this rule | The gating feature was not declared |
| `APPROVED_EXCEPTION` | A recorded, owned deviation | Only for PROJECT-class rules, with a written record |

`NOT_RUN` is the load-bearing one. It is the status that makes the rest true — the
moment an unchecked rule can be reported as a pass, none of the other four mean
anything.

## The gate

```bash
python3 scripts/ux_report.py --merge --feature forms --feature payments_or_legal
python3 scripts/ux_report.py --merge --release          # stricter
```

| Decision | When |
|---|---|
| `BLOCKED` | A P0 or P1 rule is failing — or, with `--release`, a P0 rule was never checked |
| `CONDITIONAL` | Nothing failing, but P0 rules are unverified. Fine mid-change; not enough to ship |
| `READY` | Every applicable rule was checked and none are failing |

`--release` treats an unchecked P0 as blocking because for a safety, privacy or
data-integrity rule, "we did not look" and "it fails" are the same position to ship
from.

## Severity

- **P0** — safety, privacy, security, data integrity, irreversible harm.
- **P1** — accessibility failure, blocked task, wrong result, substantial usability failure.
- **P2** — visual consistency, lower-impact refinement.

## Writing the report

Lead with `counts.not_run`, then failures by severity, then what passed, then the
scope: which routes, which viewports, which tiers, which browser, which date.

Good:

> Static and runtime tiers on `/`, `/settings`, `/billing` at five viewports, Chromium,
> 2026-09-20. 190 rules: 38 FAIL, 21 PASS, 65 NOT_APPLICABLE, 66 NOT_RUN. The
> NOT_RUN set is mostly the manual tier — no screen-reader or real-device pass has
> been done. Blocking: NUM-001 (7 text runs below 4.5:1), A11Y-003 (12 controls with
> no visible focus), STATE-001 (aborted requests leave a spinner turning on
> `/billing`). Decision: BLOCKED.

Not good:

> Improved the UI and fixed accessibility issues. Looks good now.

The second says nothing checkable, and the reader cannot tell what was examined.

## Exceptions

`.deluxui/exceptions.yaml`, using `assets/templates/exception.md`: rule ID, scope,
reason, alternatives considered, user impact, safety and accessibility impact,
compensating controls, owner, approver, review date.

An exception may lower a **PROJECT**-class default — those are configurable choices.
It may not make a failed **STANDARD** report as passing. A WCAG criterion your product
does not meet is a criterion your product does not meet; you can decide to ship it,
and that decision belongs in the record where someone can see it, but it does not
become a pass by being written down.
