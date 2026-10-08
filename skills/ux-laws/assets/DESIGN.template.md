# DESIGN.md — {{product}}

> The contract every screen and component is built and reviewed against. Change it deliberately, with a reason.

## Product and users
{{what it does, for whom, main devices (phone share if known), the 3-5 critical paths}}

## Type
| Role | Family | Size / line height | Weight |
|---|---|---|---|
| Display | | | |
| Heading | | | |
| Body | | 16 / 24 | |
| Small | | 14 / 20 | |
| Data | (tabular-nums) | | |

## Color roles (light / dark)
| Role | Light | Dark | Use |
|---|---|---|---|
| surface-0 / 1 / 2 / 3 | | near-black, lighter per level | page / card / menu / modal |
| text / text-muted / text-disabled | | white @ 87% / 60% / 38% | |
| border-subtle | | white @ 8% | hairlines |
| action | | lighter, desaturated | the one primary action per view |
| danger / warning / success / info | | | status: always icon + color, never color alone |

## Scales
- Space: 4 8 12 16 24 32 48 64
- Radius: {{sm md lg (+ full for single-line pills)}}. Inner = outer − padding; edge-touching corners are 0
- Shadow: {{floating layers only}} (dark mode: elevation by lightness)
- Motion: durations {{fast 120ms / base 200ms / slow 320ms}}, easing {{…}}, reduced-motion: {{cross-fade / none}}
- Breakpoints: {{e.g. 640 / 768 / 1024 / 1280}} · container queries: {{tables, cards}}

## Density
{{per area: e.g. ops tables compact (40px rows), settings default, onboarding comfortable}}

## Component prop contract
`value`/`defaultValue`/`onChange` · `invalid` + `error` · `label`/`hint`/`required` · `disabled`/`readOnly`/`loading` ·
`size: sm|md|lg` · closed `variant` list · forwarded ref · `className` merged last.

## Composition rules
- One primary action per view; secondary as outline or link.
- Feedback surface by severity: inline (fixable) → toast (transient) → banner (persistent system state) → modal (only when nothing else works).
- Every data view: loading (layout-matched skeleton), empty (teaches the next action), error (typed, human, retry), success (names the thing plus the next step).
- Nothing essential behind hover; targets ≥44px on touch; inputs ≥16px on phones.

## Voice
- Domain words: {{…}}
- Banned filler: "Welcome back", "Get started" (unless literal), "An error occurred", "Success!", "Something went wrong" without a next step
- Error pattern: what happened + why (if known) + what to do. Success pattern: object + recipient/target + date + next action.

## Accepted exceptions
| Exception | Reason | Owner | Date |
|---|---|---|---|
