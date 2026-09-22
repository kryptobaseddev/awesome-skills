# Forms, validation and authentication

15 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Forms are where users lose work. The rules cluster around three failures: asking for what you do not need, telling people they are wrong before they have finished, and discarding what they typed when something fails.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **FORM-001** | P1 | PROJECT | MUST request only information required for the current task or an explicitly explained optional purpose. | Every field has an identified use and owner. | S00 | `S-FORM-EXCESSIVE` |
| **FORM-002** | P1 | STANDARD | MUST give every input a persistent meaningful label and expose required, optional, format, and unit information when relevant. | Labels remain available after entry and are programmatically associated. | S10 S00 | `S-A11Y-LABEL`, `S-A11Y-PLACEHOLDER` |
| **FORM-003** | P1 | STANDARD | MUST use appropriate native input types and autocomplete metadata. MUST preserve valid international names, addresses, and formats. | Representative locale data and browser autofill work without arbitrary rejection. | S10 S30 S00 | `S-FORM-AUTOCOMPLETE`, `S-FORM-INPUTTYPE` |
| **FORM-004** | P1 | PROJECT | MUST keep safe user input after validation, network, or server errors. MUST NOT repopulate sensitive values contrary to the data policy. | Retry does not require re-entering unrelated valid fields. | S00 | `S-FORM-LOST-INPUT` |
| **FORM-005** | P1 | STANDARD | MUST provide timely field errors without treating every partially typed value as a completed invalid answer. | Initial, typing, blur, and submit states avoid premature error spam. | S10 S00 | `S-FORM-VALIDATION` |
| **FORM-006** | P1 | STANDARD | MUST associate each error with its field and explain the correction. For multiple submit errors, provide an accessible summary and navigation to affected fields. | Users can locate, understand, and correct all errors with keyboard and assistive technology. | S10 S00 | `S-FORM-ERROR-LINK` |
| **FORM-007** | P1 | PROJECT | MUST explain any blocked submission. SHOULD allow an attempted submission to reveal actionable validation rather than presenting an unexplained disabled button. | An invalid form never leaves the user guessing why progression is blocked. | S00 | `S-FORM-DISABLED`, `S-COMP-DISABLED-MUTE` |
| **FORM-008** | P1 | PROJECT | MUST retain appropriate field dependencies and make changes to derived fields visible. | Changing an upstream selection does not silently leave stale downstream values. | S00 | `S-FORM-DERIVED-STALE` |
| **FORM-009** | P0 | HEURISTIC | MUST apply server-side validation and authorization independently of client feedback. | Invalid, stale, and unauthorized requests fail safely even with client checks bypassed. | S30 S00 | `S-SERVER-VALIDATION` |
| **FORM-010** | P1 | STANDARD | MUST allow password managers and paste. MUST satisfy accessible-authentication requirements for the web. | Authentication does not rely on a prohibited cognitive test without an allowed alternative or assistance. | S08 | `S-FORM-PASTE` |
| **FORM-011** | P1 | STANDARD | MUST make previously supplied same-process information available for reuse unless an applicable exception justifies re-entry. | Redundant-entry cases are removed or documented under SC 3.3.7. | S43 | `S-FORM-REDUNDANT` |
| **FORM-012** | P0 | PROJECT | MUST make password visibility controls accessible and user-operated. MUST NOT log, persist, or transform passwords for convenience. | Visibility state is announced appropriately and secrets remain out of logs. | S00 | `S-SECRET-LOG`, `S-PASSWORD-HANDLING` |
| **FORM-013** | P0 | STANDARD | MUST provide a review, correction, or reversal mechanism appropriate to legal, financial, or protected-data submissions. | Applicable SC 3.3.4 conditions and domain risk controls are satisfied. | S44 S00 | `S-COMMIT-REVIEW`, `M-DESTRUCTIVE-WALK` |
| **FORM-014** | P0 | PROJECT | MUST identify recipient, object, amount, currency, unit, and consequence wherever ambiguity could cause harm. | The final commit view matches the exact backend operation. | S00 | `S-COMMIT-DISCLOSURE` |
| **FORM-015** | P1 | PROJECT | MUST support input composition, paste, and keyboard editing. MUST NOT trigger premature submission during composition or intercept standard editing keys without need. | Composition input and multiline fields behave correctly in supported environments. | S00 | `S-FORM-PASTE-BLOCK` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S08 |  — Understanding Accessible Authentication Minimum, SC 3.3.8 | official_explanation |
| S10 |  — Forms Tutorial: Validating Input | official_tutorial |
| S30 |  — Input Validation Cheat Sheet | primary_security_guidance |
| S43 |  — Understanding Redundant Entry, SC 3.3.7 | official_explanation |
| S44 |  — Understanding Error Prevention Legal Financial Data, SC 3.3.4 | official_explanation |
