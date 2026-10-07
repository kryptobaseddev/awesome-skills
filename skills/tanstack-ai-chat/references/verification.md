# Verification and release evidence

Choose tests that prove requested behavior. A checklist is a release plan until outcomes are recorded. These source-derived A01–A25 scenarios retain their original IDs for traceability.

| ID | Scenario | Passing evidence |
|---|---|---|
| A01 | Open/close/dock while streaming | Same thread/run, draft preserved, no extra provider call |
| A02 | Shrink app panel in wide viewport | Navigation follows app width |
| A03 | Add nested toolbar container | Named queries retain correct ancestor |
| A04 | Bottom dock, long content | Independent scroll; reachable composer |
| A05 | Mobile keyboard, rotate, dismiss | Reachable actions; state survives close/swipe |
| A06 | Navigate after Send | Original snapshot retained; next chip follows route |
| A07 | Context off | Future request omits implicit page/entity data |
| A08 | Rapid duplicate submit | One accepted turn/run; fingerprint conflicts reject |
| A09 | Network/reload mid-answer | Same-run replay; no second provider call or insert |
| A10 | Replay on another instance | Shared log and tenant/run authorization work |
| A11 | Kill producer | Partial history; accurate interruption, no false completion |
| A12 | Close versus Stop | Dismiss differs from acknowledged cancellation |
| A13 | Approve, reconnect, resubmit | One domain commit; existing receipt returned |
| A14 | Tamper tenant/context/approval | Denied; no leakage or write |
| A15 | Revision changes before approval | Reject stale proposal or prepare new review |
| A16 | Commit succeeds, refresh fails | Receipt shown; refresh retry does not mutate |
| A17 | Deny interrupt | Normal denied outcome; no automatic execution |
| A18 | Unsupported part/version | Safe fallback; durable result retained |
| A19 | Provider/storage/upload fails | Draft/output remain; truthful recoverable state |
| A20 | Read older content while streaming | Anchor retained; Jump to latest |
| A21 | IME + Enter | No accidental send |
| A22 | Keyboard-only use | Open/resize/dock/close/approve/send/stop work |
| A23 | Screen reader/reduced motion | Useful labels, coarse status, proper modality |
| A24 | Long code/URL/table/filename | Overflow confined to relevant region |
| A25 | Sign-out/tenant switch | Old private views/subscriptions cleared; reauthorization |

## Layers

Unit-test mode/clamp calculations, snapshot freezing, fingerprints and resource mapping where logic is nontrivial. Component-test IME, focus, approvals and scroll anchors. Integration-test parsing, store contention, authorization, continuation, replay and cancellation with observable invocation/commit counters. Use browser/device tests for geometry, portals, keyboard, touch and accessibility. Compile SDK wiring and build generated CSS against chosen packages.

For critical fault tests use controlled provider/domain stubs with invocation counters, revision conflicts, delayed commits and uncertain outcomes. Do not infer absence of side effects from an HTTP error alone. Correlate durable receipts and downstream state. Test simultaneous duplicate requests across two instances, not only sequential retries in one process.

## Scaling additions

| ID | Test | Passing evidence |
|---|---|---|
| S01 | Sustained and burst traffic | Declared latency/resource objectives and bounded admission |
| S02 | Noisy tenant + small tenant | Fair service; per-tenant limits hold across workers |
| S03 | Slow consumers/large transcript | Bounded buffer/memory; usable replay and UI |
| S04 | Worker takeover race | Fencing prevents stale local writes; external effects reconcile |
| S05 | Database/log/provider outage | Defined degraded behavior; no unrecorded consequential actions |
| S06 | Tool runaway/token budget | Server budgets terminate execution; accurate partial state |
| S07 | Rollout/rollback with live runs | History/receipts readable; no duplicate actions |
| S08 | Privacy and retention | No body/secrets in default telemetry; scoped deletion policy |
| S09 | Log expiry and cancellation race | Resume/Retry and committed/cancelled outcomes stay distinct |

## Evidence record

For each check record: scenario ID, revision and package versions, environment, workload/fixture, command or manual procedure, observed result, artifact/counter, pass/fail/unavailable and limits. A screenshot supports appearance only. Load-test numbers require workload and environment. Unit tests cannot certify a physical mobile keyboard or screen reader.

For a review, distinguish confirmed findings from hypotheses. Include trigger, source location, impact, correction and targeted verification. For production release, unresolved mandatory scenarios remain open; mocks prove integration logic, not provider/host behavior.
