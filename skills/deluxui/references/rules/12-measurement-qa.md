# Measurement and verification quality

13 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

How to know whether any of this worked, and what counts as evidence. QA-001 onwards is the answer to 'can I just say it passed'.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **MEASURE-001** | P2 | PROJECT | MUST define success as a completed user outcome rather than a click, screen visit, or animation. | The measurement identifies the correct final state. | S00 | _manual only_ |
| **MEASURE-002** | P2 | PROJECT | MUST mark missing baselines as UNKNOWN and avoid inventing improvement percentages. | Before-and-after claims use comparable measured data. | S00 | _manual only_ |
| **MEASURE-003** | P2 | PROJECT | MUST evaluate task errors, completion, and recovery alongside conversion or engagement. | An apparent business gain is not accepted if it creates a prohibited safety or accessibility regression. | S00 | _manual only_ |
| **MEASURE-004** | P2 | PROJECT | MUST record sample, population, environment, and uncertainty for usability results. | A small convenience sample is not described as universal proof. | S00 | _manual only_ |
| **MEASURE-005** | P2 | PROJECT | MUST NOT impersonate real users or report simulated agent behavior as human usability testing. | Human sessions and simulation results are labeled separately. | S00 | _manual only_ |
| **MEASURE-006** | P2 | PROJECT | MUST prioritize both frequent tasks and rare high-impact tasks. | Account recovery, cancellation, correction, and destructive actions appear in the risk-based plan. | S00 | _manual only_ |
| **MEASURE-007** | P2 | PROJECT | MUST distinguish percentage change from percentage-point change when reporting rates. | Metrics preserve denominator, time window, and comparison meaning. | S00 | _manual only_ |
| **QA-001** | P1 | PROJECT | MUST map each applicable mandatory rule to tests or review evidence before marking it satisfied. | The rule report contains no unsupported PASS. | S00 | _manual only_ |
| **QA-002** | P1 | PROJECT | MUST test complete changed workflows, not only isolated components. | Successful and failed paths include all dependent screens and embedded steps. | S00 | _manual only_ |
| **QA-003** | P1 | HEURISTIC | MUST include manual checks for functionality not covered by automation. | Required manual checks are executed or remain NOT_RUN. | S34 S00 | _manual only_ |
| **QA-004** | P1 | PROJECT | MUST retest after fixing a defect and retain the failing scenario as a regression test where practical. | The final evidence references the corrected build. | S00 | _manual only_ |
| **QA-005** | P1 | PROJECT | MUST surface any required environment or tool limitation in the final report. | Unavailable checks affect the release decision under Section 19. | S00 | _manual only_ |
| **QA-006** | P1 | PROJECT | MUST NOT call an existing defect out of scope when the change worsens it or depends on the broken path. | Legacy issues have explicit scope, impact, owner, and regression assessment. | S00 | _manual only_ |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S34 |  — Accessibility Testing | official_testing_documentation |
