# Usability principles

14 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Nielsen's heuristics and their relatives, written as testable requirements. They are heuristics, not laws, and the acceptance column is what makes them checkable. Treat them as the questions a competent reviewer would ask.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **UX-001** | P1 | HEURISTIC | MUST expose the current state, selected scope, and outcome of an operation. | Users can distinguish idle, pending, successful, and failed operations. | S17 S00 | `S-STATE-EMPTY`, `R-STATE-OFFLINE`, `R-STATE-EMPTY` |
| **UX-002** | P1 | HEURISTIC | MUST use terminology and ordering that match the user task and domain. | Labels are understandable without internal database or engineering knowledge. | S17 S00 | `M-CONTENT-REVIEW` |
| **UX-003** | P1 | HEURISTIC | MUST provide a safe exit, cancellation, or correction path wherever the operation permits it. | Back, cancel, undo, or corrective action has a tested result. | S17 S00 | `S-TRUST-DESTRUCT`, `M-KEYBOARD-TASK`, `M-DESTRUCTIVE-WALK` |
| **UX-004** | P1 | HEURISTIC | MUST keep repeated actions consistent while honoring platform-specific conventions. | Equivalent components behave consistently within each platform. | S17 S00 | `M-JUDGE-CONSISTENCY` |
| **UX-005** | P1 | HEURISTIC | MUST prevent predictable high-impact errors before submission. | Review or safe reversal protects consequential actions. | S17 S00 | `M-DESTRUCTIVE-WALK` |
| **UX-006** | P1 | HEURISTIC | MUST make required context visible instead of demanding unnecessary recall. | Users do not need to memorize information from a previous screen. | S32 S00 | `M-JUDGE-RECALL` |
| **UX-007** | P2 | HEURISTIC | SHOULD support efficient repeated work through safe defaults, shortcuts, or bulk actions. | Expert paths preserve confirmation, permissions, and accessibility. | S17 S00 | `M-JUDGE-EXPERT-PATH` |
| **UX-008** | P1 | HEURISTIC | MUST remove irrelevant competition without hiding necessary controls or information. | Every prominent element supports the current task or essential context. | S17 S00 | `M-JUDGE-COMPETITION` |
| **UX-009** | P1 | HEURISTIC | MUST explain what failed and provide an available recovery action. | Error message identifies the affected action and an actual next step. | S17 S00 | `S-STATE-ERROR`, `S-CONTENT-ERRORTEXT`, `R-STATE-ERROR` |
| **UX-010** | P1 | HEURISTIC | MUST provide task-relevant help at a consistent, discoverable location. | Help answers the current problem without abandoning entered work. | S17 S00 | `M-JUDGE-HELP` |
| **UX-011** | P1 | PROJECT | MUST make interactive elements appear actionable and represent their state truthfully. | Static, interactive, selected, disabled, and pending elements are distinguishable. | S00 | `S-UX-FAKE-INTERACTIVE` |
| **UX-012** | P1 | HEURISTIC | MUST reveal optional complexity progressively without hiding costs, risks, prerequisites, or common actions. | Advanced controls are discoverable. Consequential information precedes commitment. | S33 S00 | `M-JUDGE-PROGRESSIVE` |
| **UX-013** | P1 | PROJECT | MUST align controls with the objects, directions, or values they change. | Control labels, placement, and resulting changes agree. | S00 | `S-UX-CONTROL-ALIGNMENT` |
| **UX-014** | P2 | PROJECT | MUST preserve user control over personalization and remembered preferences. | Users can inspect, reset, or change consequential remembered settings. | S00 | `S-UX-PREFERENCE-CONTROL` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S17 |  — 10 Usability Heuristics for User Interface Design | original_practitioner_framework |
| S32 |  — Recognition vs. Recall in User Interfaces | practitioner_guidance |
| S33 |  — Progressive Disclosure | practitioner_guidance |
