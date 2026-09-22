# shape — decide what to build, and return a brief without code

Discovery, not construction. `shape` ends with a confirmed brief and writes
nothing else.

Derived from impeccable's `shape` (Apache-2.0) — see NOTICE.md.

## Cadence

Two or three questions per round, then stop and wait. One round is the default;
add a second only when the answers expose a material gap. Do not send a
questionnaire, do not re-ask what the brief already settled, and do not turn an
obvious fact into a menu — assert the likely reading and invite correction.

A sparse prompt needs at least one round. A precise prompt may need only a
compact confirmation.

## Round 1 — purpose, people, outcome

Pick the two or three that most change the result:

- What is this for, and what problem must it solve?
- Who reaches it, in what situation and state of mind? This is the **visitor
  mode** (see [../design/visitor-modes.md](../design/visitor-modes.md)) and it
  changes every decision downstream.
- What is the one thing they must understand or do? What would success look like?
- What is true here that a neighbouring product could not claim?

## Round 2 — material, behaviour, boundaries

Only for decisions still genuinely open:

- What real content, data and evidence must this carry? Minimum, typical and
  **maximum** ranges — the maximum is what breaks layouts.
- Which states matter: first run, empty, loading, error, permission, overflow,
  expert use? (STATE-001 onward; these are the states nobody builds and everybody
  reaches.)
- **Which actions are irreversible or external?** This is the PRODUCT.md question
  and it drives UX-003, TRUST-006 and the whole destructive-action family. Ask it
  every time.
- What must remain untouched? What would make the result feel wrong even if it
  looked polished?
- Which platform, performance, accessibility, localisation or delivery
  constraints are binding?

Never ask for CSS values or a menu of aesthetic lanes. Visual direction belongs
to [new-work.md](new-work.md).

## The brief

Three to five bullets when the task is settled; the full structure only for
ambiguous or multi-screen work:

1. **Job and audience** — who arrives, their context, need, visitor mode.
2. **Outcome and proof** — primary task, what success is, the real evidence.
3. **Direction** — structural and interaction thesis, the focal moment.
4. **Scope and boundaries** — what is in, what stays untouched, explicit anti-goals.
5. **States and ranges** — realistic content ranges and the material states.
6. **Interaction and layout** — hierarchy, responsiveness, feedback. Intent, not CSS.
7. **Constraints and open decisions** — what a builder must not invent.

## Stop

Present the brief for confirmation or one correction round, then stop. `shape`
never writes code and never picks a visual direction.

Where there is nobody to answer, mark the assumptions plainly in the brief,
return it, and stop. An assumption on the record is recoverable; one buried in
the implementation is not.

Next: [new-work.md](new-work.md) for a new world, [../workflows/design.md](../workflows/design.md) to build it.
