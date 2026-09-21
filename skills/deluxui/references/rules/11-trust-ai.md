# Trust, safety, privacy and AI features

14 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Consequence disclosure, dark patterns, permissions and the honest handling of generated output. The AI rules apply only when the product actually has a generative feature -- declare it with `--feature ai_features`.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **TRUST-001** | P0 | PROJECT | MUST disclose material costs, recurring terms, permissions, and irreversible consequences before commitment. | The commitment screen matches the actual operation and commercial terms. | S00 | `S-COMMIT-DISCLOSURE` |
| **TRUST-002** | P0 | PROJECT | MUST NOT use disguised advertising, fake urgency, misleading defaults, forced consent, or deliberately obstructive cancellation. | Decline, cancellation, and correction paths are discoverable and truthful. | S00 | `S-DARK-PATTERN` |
| **TRUST-003** | P0 | PROJECT | MUST request sensitive permissions at the point of need with a clear purpose and a usable denial path where feasible. | Permission denial does not produce a broken or deceptive interface. | S00 | `S-PERM-ONMOUNT` |
| **TRUST-004** | P0 | HEURISTIC | MUST distinguish hidden UI from access control. Authorization remains enforced by the trusted system. | Direct unauthorized requests fail regardless of whether controls are visible. | S30 S00 | `S-SERVER-VALIDATION`, `S-AUTHZ-UI-ONLY` |
| **TRUST-005** | P0 | PROJECT | MUST restrict sensitive content in logs, analytics, URLs, notifications, and error reports according to the data policy. | Instrumented events omit prohibited field values and secrets. | S00 | `S-SECRET-LOG` |
| **TRUST-006** | P0 | STANDARD | MUST match confirmation friction to consequence. Use explicit confirmation for high-impact irreversible actions without adding repeated confirmation to every harmless action. | Risk classification explains where review, undo, or confirmation applies. | S44 S00 | `S-TRUST-DESTRUCT`, `M-DESTRUCTIVE-WALK` |
| **TRUST-007** | P0 | PROJECT | MUST ensure undo restores the promised state. MUST NOT offer undo when the irreversible external effect cannot actually be reversed. | Undo tests verify the persisted result and disclosed limitations. | S00 | `S-TRUST-DESTRUCT` |
| **TRUST-008** | P0 | PROJECT | MUST provide clear account, workspace, recipient, and permission context before cross-account or external actions. | A user can identify which entity will be affected before commitment. | S00 | `S-ACCOUNT-CONTEXT` |
| **AI-001** | P0 | PROJECT | MUST distinguish generated suggestions from verified records and completed actions. | The interface never presents a draft recommendation as a confirmed operation. | S00 | `S-AI-PROVENANCE` |
| **AI-002** | P1 | PROJECT | MUST expose uncertainty and limitations that materially affect a user decision. MUST NOT fabricate confidence percentages, citations, or checks. | Confidence and provenance are supported by actual system data or omitted. | S00 | `S-AI-UNCERTAINTY` |
| **AI-003** | P0 | PROJECT | MUST allow review and correction before consequential AI-initiated external actions. | The user sees the actual target, payload summary, and consequence before authorized execution. | S00 | `S-AI-PROVENANCE` |
| **AI-004** | P1 | PROJECT | MUST provide stop, retry, and correction behavior appropriate to generation and execution. | Stopping text generation is not falsely described as cancelling an already executed external action. | S00 | `S-AI-UNCERTAINTY` |
| **AI-005** | P1 | PROJECT | MUST make streamed output readable and accessible without announcing every token. | Keyboard focus remains stable and screen-reader updates are controlled. | S00 | `S-AI-STREAM-A11Y` |
| **AI-006** | P1 | PROJECT | MUST preserve provenance when summarizing source-backed information and mark unavailable evidence honestly. | Presented source references resolve to the content actually used. | S00 | `S-AI-UNCERTAINTY` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S30 |  — Input Validation Cheat Sheet | primary_security_guidance |
| S44 |  — Understanding Error Prevention Legal Financial Data, SC 3.3.4 | official_explanation |
