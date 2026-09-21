# State coverage and asynchronous behaviour

12 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

The states nobody builds and everybody reaches. Note the asymmetry the rules keep returning to: an unknown outcome is not a success, and a dismissed panel is not a cancelled operation. `ux_browser.sh --api` forces most of these so you can see them rather than reason about them.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **STATE-001** | P1 | PROJECT | MUST model pending, success, failure, and unknown outcomes explicitly for each mutation. | Tests include server success, rejection, lost response, and repeated activation. | S00 | `S-STATE-ERROR`, `S-STATE-LOADING`, `R-CONSOLE`, `R-STATE-ERROR` |
| **STATE-002** | P0 | PROJECT | MUST show confirmed success only after the required durable system acknowledgement. | The displayed result matches the persisted operation, not merely the button click. | S00 | `S-STATE-PREMATURE` |
| **STATE-003** | P0 | PROJECT | MUST guard duplicate operations in the UI and use appropriate backend deduplication for consequential mutations. | Repeated clicks, retries, refreshes, and reconnects do not cause unintended duplicate commits. | S00 | `S-STATE-DUPE` |
| **STATE-004** | P1 | PROJECT | MUST use optimistic updates only for actions with a defined safe rollback or reconciliation strategy. | A failed mutation restores or reconciles visible state and explains the outcome. | S00 | `S-STATE-OPTIMISTIC` |
| **STATE-005** | P0 | PROJECT | MUST NOT optimistically represent a high-risk external action as completed when its outcome is unconfirmed. | Payments, irreversible deletion, and other consequential actions show truthful pending status. | S00 | `S-STATE-OPTIMISTIC` |
| **STATE-006** | P1 | PROJECT | MUST avoid indefinite spinners. Define operation-specific timeout, escalation, and recovery behavior. | Simulated stalled requests produce an understandable state and a real next action. | S00 | `R-STATE-ERROR`, `R-STATE-SLOW` |
| **STATE-007** | P1 | PROJECT | MUST prevent stale responses from overwriting newer state and avoid updating destroyed or irrelevant views. | Race-condition tests preserve the newest valid task state. | S00 | `S-STATE-RACE` |
| **STATE-008** | P1 | PROJECT | MUST distinguish locally saved, queued, synchronizing, and server-saved work. | Autosave labels and timestamps reflect the actual storage state. | S00 | `R-STATE-OFFLINE` |
| **STATE-009** | P0 | PROJECT | MUST preserve drafts only in approved storage, for an approved duration, with user and account boundaries. | Logout, shared-device use, account switching, and expiration do not expose another user draft. | S00 | `S-DRAFT-BOUNDARY` |
| **STATE-010** | P0 | PROJECT | MUST resolve concurrent edits without silent destructive overwrite when the domain requires conflict protection. | Version mismatch produces a reviewable conflict path. | S00 | `S-CONFLICT-OVERWRITE` |
| **STATE-011** | P0 | PROJECT | MUST expose retry only when its semantics are safe. MUST reconcile an unknown consequential outcome before repeating it. | Retry tests verify idempotency or an equivalent safe recovery contract. | S00 | `S-RETRY-SAFETY` |
| **STATE-012** | P1 | PROJECT | MUST distinguish frontend cancellation, request abort, queued-job cancellation, and confirmed backend cancellation. | A dismissed panel never falsely implies the underlying operation was cancelled. | S00 | `S-STATE-CANCEL` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
