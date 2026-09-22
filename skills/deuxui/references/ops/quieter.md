# quieter — lower the volume without lowering the information

The mirror of [bolder.md](bolder.md), and the more dangerous of the two: it is
easy to quiet a screen by removing the thing that told somebody what to do.

Derived from impeccable's `quieter` (Apache-2.0) — see NOTICE.md.

## What quieting is

Reducing **competition**, not content. UX-008 is the rule: every prominent
element should support the current task. A screen is loud when six things claim
first attention, and the repair is to demote five of them — not to delete them.

The order:

1. **Take emphasis off what is not the task.** Weight, size, colour, motion, in
   that order of cost. A secondary action becomes a text button before it becomes
   invisible.
2. **Collapse repeated chrome.** Three cards each with a border, a shadow and a
   background are three depth systems arguing (`S-CRAFT-DEPTH`). One metaphor.
3. **Reduce surface count.** `S-CRAFT-SURFACES` counts the distinct backgrounds
   on a screen; each one is a decision the reader has to make about grouping.
4. **Narrow the palette, not the meaning.** An accent that appears everywhere has
   stopped marking anything, but the status colour still has to be there.

## What must not get quieter

- The primary action. If it is now hard to find, the screen got worse.
- An error, a warning, or the disclosure that precedes a commitment (TRUST-001).
- A focus indicator. Ever. `S-FOCUS-OUTLINE` exists because this is the single
  most common casualty of a visual calm-down pass.
- A required field marker, a destructive confirmation, or a state.

## Verify

| Detector | What it settles |
|---|---|
| `S-CRAFT-DEPTH`, `S-CRAFT-SURFACES` | One depth metaphor, a countable number of surfaces. |
| `S-SLOP-UNIFORM` | Uniform heaviness is gone, not replaced by uniform lightness. |
| `S-FOCUS-OUTLINE` | The focus ring survived. |
| `S-CONTRAST-PAIR`, `R-CONTRAST` | Quieter text is still readable — this is where quieting most often crosses 4.5:1. |
| `M-JUDGE-COMPETITION` | Somebody listed what competes for first attention and confirmed the hierarchy is clean. |

Hand off to [polish.md](polish.md).
