# UX audit — {{product}} · iteration {{N}} · {{date}}

## Summary
- **Scope:** {{routes walked}} at {{widths}} · {{source root}} · critical paths: {{list}}
- **Scorecard:** {{F}} FAIL · {{W}} WARN · {{P}} PASS · {{NM}} NOT_MEASURED (measured coverage {{x/y}})
- **Biggest wins available:** the 3 changes that clear the most FAILs on the most-used paths
- **Observed on:** {{dev build of src / staging / static preview}}; drift from source: {{none found / list}}
- **Not covered:** {{what wasn't measured and why, e.g. auth routes (no test account), INP (no field data)}}

## Broken or unsafe (fix before any UX work)
{{functional bugs, security and privacy exposures, lost-work defects found by reading the critical-path code; or "none found" with what was read}}

## Findings (ranked: critical path first, then fan-in, then severity)
Each finding names its law with a link, its evidence (file:line, capture or measured value), and a concrete fix.

### 1. {{title}}: {{FAIL|WARN}}
- **Law:** [{{law}}]({{url}}) · **Standard:** {{WCAG x.x.x, if any}}
- **Where:** {{route@width}} · `{{file:line}}` · affects {{fan-in}} screens through `{{Component}}`
- **Evidence:** {{measured value / screenshot path / probe field}}
- **Fix:** {{specific change; component-level if the cause is a shared component}}
- **Verify by:** {{metric id that must move, and the target}}

## Component map
- Layers: primitives {{n}} · patterns {{n}} · domain {{n}} · screens {{n}}
- Consolidation candidates: {{family: members → target}} (plan in ux-audit/component-map.md)
- Library bypass: {{raw elements where a primitive exists}}
- Token adoption: {{ratio}}; runtime sprawl: {{font sizes / radii / shadows}}

## Flows
| Path | Screens | Taps | Fields | Decisions | Waits >400ms w/o feedback | Dead ends | Survives refresh |
|---|---|---|---|---|---|---|---|

## Conflicts for the owner to decide
{{rules that disagree (component-systems.md → Conflicts) and the options, with no winner picked}}

## Plan
| Order | Change | Laws | Metrics that move | Size | Risk / blast radius |
|---|---|---|---|---|---|

## Changes since the previous iteration
{{scorecard Δ, flow-cost Δ, screenshots side by side}}
