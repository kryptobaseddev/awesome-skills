# Performance engineering

10 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Perceived and measured speed, kept apart on purpose. A spinner is not performance, a lab number is not a field number, and reserving layout space costs nothing while layout shift is measured directly.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **PERF-001** | P1 | STANDARD | MUST define performance budgets before optimizing. Use NUM-012 for web field goals and operation-specific completion targets. | Each target identifies metric, environment, percentile, and evaluation window. | S14 S00 | `S-3D-PERF` |
| **PERF-002** | P1 | PROJECT | MUST measure representative routes, devices, and network conditions rather than only the developer workstation. | Performance evidence records hardware or emulation, throttling, route, and content volume. | S00 | _manual only_ |
| **PERF-003** | P1 | PROJECT | MUST reserve space for delayed images, embeds, loading regions, and asynchronously inserted UI where feasible. | Content does not unexpectedly move under a pointer or reading position. | S00 | `S-PERF-IMGDIM` |
| **PERF-004** | P1 | PROJECT | MUST prioritize visible task content and avoid blocking input on unnecessary work. | Critical routes remain interactive while nonessential work proceeds separately. | S00 | _manual only_ |
| **PERF-005** | P1 | PROJECT | MUST choose image dimensions, compression, responsive sources, and loading behavior for actual display needs. | Critical visual content is not accidentally delayed. Offscreen assets do not dominate initial work. | S00 | `R-VITALS`, `M-FIELD-PERF` |
| **PERF-006** | P1 | PROJECT | MUST justify expensive client dependencies, repeated rendering, and virtualization against measured task needs. | Profiling identifies the bottleneck before architecture is complicated. | S00 | _manual only_ |
| **PERF-007** | P1 | PROJECT | MUST keep interaction feedback responsive during computation, large lists, and network updates. | Repeated interaction tests show no avoidable input blocking or focus loss. | S00 | _manual only_ |
| **PERF-008** | P1 | PROJECT | MUST prevent loading skeletons from being announced as meaningful data or creating distracting perpetual motion. | Loading structure reserves space without flooding the accessibility tree. | S00 | _manual only_ |
| **PERF-009** | P1 | STANDARD | MUST distinguish lab regression checks from real-user performance evidence. | A lab-only result is labeled LAB. Production percentile claims use adequate FIELD data. | S14 | _manual only_ |
| **PERF-010** | P1 | PROJECT | MUST define a post-release measurement owner and collection plan when a new product lacks field data. | Unavailable field metrics remain NOT_RUN and are not invented as release-day passes. | S00 | _manual only_ |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S14 |  — Web Vitals | official_metric_guidance |
