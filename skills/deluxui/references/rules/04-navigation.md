# Information architecture and navigation

10 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Where am I, what can I do, how do I get back. Most navigation defects are really semantic defects: an action dressed as a link, or a destination that cannot be linked to.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **NAV-001** | P1 | PROJECT | MUST give each route or screen a clear purpose, title, and relationship to surrounding navigation. | Users can identify current location, available task, and exit path. | S00 | _manual only_ |
| **NAV-002** | P1 | STANDARD | MUST distinguish navigation from actions. On the web, use genuine links for destinations and buttons for actions. | Links support expected browser behavior. Buttons do not masquerade as destination links. | S12 S00 | `S-A11Y-DIVCLICK`, `S-A11Y-HREFHASH` |
| **NAV-003** | P1 | PROJECT | MUST preserve back navigation, meaningful browser history, and deep links where the application supports addressable screens. | Back returns to the expected screen and task state without creating navigation loops. | S00 | _manual only_ |
| **NAV-004** | P1 | PROJECT | MUST preserve appropriate list context after viewing or editing an item. | Relevant filters, sort, page or cursor position, and scroll context are restored safely. | S00 | _manual only_ |
| **NAV-005** | P2 | HEURISTIC | MUST keep navigation labels stable and specific. MUST NOT rename the same destination across routes without a domain reason. | Routes use the approved terminology inventory. | S18 S00 | _manual only_ |
| **NAV-006** | P1 | STANDARD | MUST choose tabs, navigation links, menus, and accordions according to their interaction purpose. | The selected pattern matches the official keyboard and semantic contract. | S11 S00 | _manual only_ |
| **NAV-007** | P1 | PROJECT | MUST indicate the current destination or selected view visually and programmatically. | The accessibility tree and visible selection identify the same item. | S00 | _manual only_ |
| **NAV-008** | P1 | PROJECT | MUST provide a predictable invalid-route, unavailable-content, and insufficient-permission experience. | Users receive a safe relevant destination without unauthorized information disclosure. | S00 | _manual only_ |
| **NAV-009** | P0 | PROJECT | MUST NOT encode private data, credentials, or sensitive drafts in shareable URLs or browser history. | URL inspection and history inspection reveal no prohibited data. | S00 | _manual only_ |
| **NAV-010** | P1 | PROJECT | MUST avoid unexpectedly moving focus during background updates. For intentional screen changes, move or announce context predictably. | Keyboard and screen-reader users can continue from a meaningful location. | S00 | _manual only_ |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S11 |  — ARIA Authoring Practices Guide | official_non_normative_guidance |
| S12 |  — Read Me First: ARIA Authoring Practices | official_non_normative_guidance |
| S18 |  — End of Web Design | original_practitioner_source |
