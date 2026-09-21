# animate — motion that explains, and stops when asked

Motion earns its place by making a relationship legible: where a thing came from,
what it turned into, what is still happening. Motion that only decorates costs
attention and, for some people, costs more than that.

Derived from impeccable's `animate` (Apache-2.0) — see NOTICE.md.

## The gate, before anything moves

An animation with no reduced-motion path is not a polish gap; it is an
accessibility failure with a health consequence (A11Y-010, LAY-010). Write the
`prefers-reduced-motion` branch in the same edit as the animation, never after.

On native the same rule has platform names: `IOS-017` reads
`accessibilityReduceMotion`, `AND-015` reads the system animation scale. Both are
checked (`S-IOS-REDUCEMOTION`, `S-AND-REDUCEMOTION`).

## The numbers

From `references/rules/thresholds.yaml`, overridable per project:

| | |
|---|---|
| Micro-interaction | 120–240ms (NUM-018) |
| Easing | Exponential ease-out. `ease-in-out`, `linear` and bounce curves are banned by `S-CRAFT-EASING` |
| Authored entrance moments per page | 1 |

That last one is the rule people resist and it is the one that matters. One
designed moment reads as intent. One identical fade per section reads as a
template, and `S-CRAFT-MOTION` counts them.

## What to animate

- **Continuity.** A thing that moves from A to B should travel, so the eye keeps
  hold of it. Two unrelated things should not.
- **State, not decoration.** Pending, arriving, leaving, invalid. If the motion
  does not correspond to a state change, it is decoration.
- **Reversibility.** A dismissal reverses its entrance. When it does not, the
  gesture and the animation disagree and the user loses the model (IOS-016).
- **Nothing hidden at rest.** Content that is invisible until a scroll listener
  fires is content that never appears when the listener does not (`S-CRAFT-HIDDEN-AT-REST`),
  and it is invisible to search and to a reader with motion reduced.

Never delay a completion to stage a flourish. Never fake progress.

## Write it down

`motion.duration_ms`, `motion.easing` and `motion.authored_moments` go in the
contract. Then a 600ms bounce somewhere in the codebase is measurably a
departure rather than a matter of opinion.

## Verify

| Detector | What it settles |
|---|---|
| `S-MOTION-REDUCE` | Every animation has a reduced-motion path. |
| `S-CRAFT-EASING` | No banned curve. |
| `S-CRAFT-MOTION` | One authored entrance moment, not one per section. |
| `S-CRAFT-HIDDEN-AT-REST` | Nothing invisible until a listener fires. |
| `S-CONTRACT-MOTION` | Durations inside the declared band (NUM-018). |
| `R-MOTION` | With reduced motion on, in a real browser: what still moves. |

Hand off to [polish.md](polish.md).
