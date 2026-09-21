# Content, localisation and data presentation

11 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Copy is interface. So are units, currencies, time zones and the difference between zero, missing and stale. Test with real and extreme content, because placeholder text hides every layout problem you have.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **CONTENT-001** | P1 | PROJECT | MUST use concise, task-specific language and consistent domain terminology. | Action labels predict outcomes. Instructions explain only what the user needs at that point. | S00 | `S-SLOP-EMOJI` |
| **CONTENT-002** | P1 | PROJECT | MUST avoid blaming users or exposing raw stack traces as the only error message. | Errors identify the problem, preserve context, and offer an available correction. | S00 | `S-CONTENT-ERRORTEXT`, `M-CONTENT-REVIEW` |
| **CONTENT-003** | P1 | PROJECT | MUST use real representative content in testing. MUST include long text, zero records, missing values, extreme valid values, and large collections. | The interface survives realistic content without placeholder-dependent layout. | S00 | `S-SLOP-COPY` |
| **CONTENT-004** | P1 | PROJECT | MUST keep translated strings externalized where localization is in scope. MUST avoid sentence construction that breaks grammar or pluralization. | Supported locales display correct complete messages and count forms. | S00 | `S-CONTENT-I18N` |
| **CONTENT-005** | P1 | PROJECT | MUST use locale-aware dates, numbers, currencies, and units while preserving unambiguous meaning. | Ambiguous dates and mixed currencies are not silently guessed. | S00 | `S-CONTENT-FORMAT` |
| **CONTENT-006** | P1 | PROJECT | MUST expose timezone or absolute time when relative time could change a consequential interpretation. | Deadlines and event timestamps remain understandable across supported regions. | S00 | `S-CONTENT-FORMAT` |
| **CONTENT-007** | P2 | PROJECT | MUST support right-to-left layout where required using logical layout properties and correct text direction. | Mixed-direction names, numbers, controls, and icons remain coherent. | S00 | _manual only_ |
| **CONTENT-008** | P1 | PROJECT | MUST distinguish calculated, measured, estimated, missing, and stale data. | Precision, provenance, and freshness match the underlying data. | S00 | `M-CONTENT-REVIEW` |
| **CONTENT-009** | P1 | PROJECT | MUST preserve chart meaning with truthful scales, labels, units, and comparison periods. | The visualization does not imply a stronger change or certainty than the data supports. | S00 | _manual only_ |
| **CONTENT-010** | P0 | PROJECT | MUST avoid using lorem ipsum, fake testimonials, fake customer counts, or invented performance statistics in production. | Every factual product claim has an approved factual source. | S00 | _manual only_ |
| **CONTENT-011** | P1 | PROJECT | MUST keep instructions independent of visual-only direction such as click the green item or use the box on the right. | Instructions identify controls by meaningful names and work in alternate layouts. | S00 | `S-VIDEO-LEGIBILITY` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
