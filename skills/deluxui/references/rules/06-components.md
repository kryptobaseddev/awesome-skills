# Component interaction contracts

24 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

What a component owes its user regardless of how it looks: a name, a role, a keyboard pattern, honest states. Native elements and vetted primitives give you most of this for free, which is why COMP-001 comes first.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **COMP-001** | P1 | STANDARD | MUST use native elements or validated existing primitives before inventing custom widgets. | Custom behavior has a documented necessity and a complete tested interaction contract. | S12 | `S-A11Y-DIVCLICK`, `S-DS-REINVENT` |
| **COMP-002** | P1 | STANDARD | MUST keep the visible label inside the accessible name when the control has visible text. | Speech users can activate the control using its visible wording. | S45 | `S-A11Y-ICONBTN` |
| **COMP-003** | P1 | PROJECT | MUST give buttons action-specific labels. MUST NOT use ambiguous labels such as Continue when the action actually commits a payment or irreversible change. | The label accurately predicts the resulting operation. | S00 | _manual only_ |
| **COMP-004** | P1 | STANDARD | MUST distinguish disabled, loading, selected, and unavailable states. MUST explain consequential unavailability near the control. | Users can identify the reason and available alternative without relying on color alone. | S39 S00 | _manual only_ |
| **COMP-005** | P1 | STANDARD | MUST use an established complete keyboard pattern for menus, tabs, listboxes, comboboxes, and trees. | Arrow keys, activation, dismissal, and focus management match the selected APG or native pattern. | S11 | _manual only_ |
| **COMP-006** | P1 | STANDARD | MUST NOT apply application menu semantics to ordinary website navigation solely because it is visually called a menu. | Semantics reflect actual navigation versus application command behavior. | S11 S00 | _manual only_ |
| **COMP-007** | P1 | STANDARD | MUST provide a named modal, meaningful initial focus, contained modal interaction, and a visible close or cancel path when dismissible. | Background content is inactive. Keyboard dismissal follows the declared modal pattern. | S13 | `S-MODAL-NATIVE` |
| **COMP-008** | P1 | STANDARD | MUST restore focus meaningfully when a modal closes. MUST avoid nested modals where an in-place or sequential flow works. | Focus returns to the opener or a logical surviving element. | S13 S00 | `S-MODAL-NATIVE` |
| **COMP-009** | P1 | STANDARD | MUST choose initial focus according to dialog content and risk. MUST NOT autofocus a destructive commitment. | Opening the dialog cannot accidentally confirm the hazardous action. | S13 S00 | `S-A11Y-AUTOFOCUS` |
| **COMP-010** | P1 | PROJECT | MUST NOT trap focus inside nonmodal popovers, ordinary panels, or tooltips. | Users can move between the component and surrounding content normally. | S00 | `S-MODAL-NATIVE` |
| **COMP-011** | P1 | STANDARD | MUST make hover or focus disclosures dismissible, hoverable, and persistent as required by the applicable criterion. | Additional content does not vanish while being read or block access without dismissal. | S40 | `S-HOVER-ONLY` |
| **COMP-012** | P1 | PROJECT | MUST use tooltips only for supplemental information. MUST keep critical instructions and errors persistently available. | Touch users and users who never discover the tooltip can complete the task. | S00 | _manual only_ |
| **COMP-013** | P1 | STANDARD | MUST expose accordion expansion and connect the trigger to the associated content. | Keyboard activation and assistive technology identify the same expanded state. | S11 S00 | _manual only_ |
| **COMP-014** | P1 | PROJECT | MUST keep table headers, row relationships, sorting state, and action context accessible. | A user can identify the record, column meaning, active sort, and row action without visual alignment alone. | S00 | _manual only_ |
| **COMP-015** | P1 | PROJECT | MUST provide a text summary and an accessible data alternative for meaningful charts. | Values, units, time range, source, and relevant comparisons remain available without seeing the chart. | S00 | `S-CANVAS-A11Y` |
| **COMP-016** | P1 | PROJECT | MUST NOT misrepresent zero, missing, estimated, rounded, or stale values as interchangeable. | Data formatting preserves meaning and marks uncertainty or missingness. | S00 | _manual only_ |
| **COMP-017** | P1 | PROJECT | MUST show search scope, current query, active filters, result status, and a clear reset path. | Zero results are distinguishable from loading, failure, or an empty collection. | S00 | `S-STATE-EMPTY`, `R-STATE-EMPTY` |
| **COMP-018** | P1 | PROJECT | MUST handle out-of-order search responses and preserve input focus while results update. | An older response never replaces results for a newer query. | S00 | _manual only_ |
| **COMP-019** | P1 | PROJECT | MUST use pagination, load-more, or virtualization only with a complete navigation and accessibility contract. | Users can reach records, maintain context, and access the end of the list or page. | S00 | _manual only_ |
| **COMP-020** | P1 | STANDARD | MUST provide keyboard and non-dragging alternatives for drag-based tasks unless the exact standard exception applies. | Reordering or moving works through a single-pointer alternative and a keyboard path. | S41 S42 | _manual only_ |
| **COMP-021** | P1 | PROJECT | MUST show upload constraints before selection and provide actual progress, failure details, and safe retry behavior. | Unsupported files, interrupted uploads, duplicates, and partial failures have usable outcomes. | S00 | _manual only_ |
| **COMP-022** | P1 | PROJECT | MUST keep important notifications available beyond a short-lived toast. | Critical confirmations and errors are recoverable from the page, history, or notification center. | S00 | _manual only_ |
| **COMP-023** | P1 | PROJECT | MUST avoid nesting interactive controls in a clickable container in ways that create competing activation targets. | Activating a nested action never triggers the parent action unintentionally. | S00 | `S-A11Y-NESTED` |
| **COMP-024** | P1 | PROJECT | MUST scope bulk actions precisely and disclose selected count, selection boundaries, and consequences. | Visible-page selection and all-result selection are distinguishable before commitment. | S00 | _manual only_ |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S11 |  — ARIA Authoring Practices Guide | official_non_normative_guidance |
| S12 |  — Read Me First: ARIA Authoring Practices | official_non_normative_guidance |
| S13 |  — Dialog Modal Pattern | official_non_normative_guidance |
| S39 |  — Understanding Use of Color, SC 1.4.1 | official_explanation |
| S40 |  — Understanding Content on Hover or Focus, SC 1.4.13 | official_explanation |
| S41 |  — Understanding Keyboard, SC 2.1.1 | official_explanation |
| S42 |  — Understanding Dragging Movements, SC 2.5.7 | official_explanation |
| S45 |  — Understanding Label in Name, SC 2.5.3 | official_explanation |
