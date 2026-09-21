# Visitor modes — what the person came to do

Every visual decision downstream depends on one question that has nothing to do with
visuals: **what did this person come here to do?** Get that wrong and the craft is
irrelevant — a beautifully typeset dashboard that reads like a landing page has failed
at the only thing it was for.

This is the layer where UX determines UI. Not as a slogan: the mode picks the density,
the type scale, the colour dosage, the motion budget and the failure tolerance, and it
picks them differently enough that the same component is wrong in one mode and right in
the other.

Adapted from the impeccable skill's visitor-mode model (Apache-2.0,
github.com/pbakaus/impeccable), which is the best formulation of this we have seen.

Declare the mode in `.deluxui/design.contract.yaml` as `visitor_mode`. It is the first
field for a reason — everything under it inherits from it.

## The five modes

| Mode | They came to | Design serves | Gets it wrong by |
|---|---|---|---|
| **persuade** | Decide whether to care | The argument | Being tasteful instead of convincing |
| **experience** | Feel something | The atmosphere | Explaining instead of showing |
| **operate** | Finish a task | The task | Being beautiful at the task's expense |
| **read** | Understand something | The text | Decorating the reading surface |
| **native** | Use their device | Platform convention | Importing web habits |

## What each mode changes

**persuade** — marketing, landing, campaign, pricing. Design *is* the product here.
Display type may carry the voice; colour may own whole regions. One authored moment is
worth more than five safe ones. The failure is timidity, not excess. Hierarchy is
ruthless: one thing is primary per viewport, and if everything is emphasised nothing is.

**experience** — a showcase, a launch, an interactive piece. Atmosphere is the payload.
Motion, depth and material are first-class rather than garnish. The floor still holds:
reduced-motion still needs a path, contrast still has to pass. Ambition is not an excuse,
and "it's an experience" is not a reason a keyboard user cannot get through it.

**operate** — dashboards, admin, tools, settings, anything with a task and a done state.
Density is a feature. Colour encodes action, selection, status and wayfinding — rarity is
what gives an accent force, so spending it on decoration is spending it. Stability beats
delight: a control that moves between visits costs more than it ever gains. Tabular
numerals wherever numbers are compared in a column. This is where most AI design fails,
because it reaches for the marketing register on a tool.

**read** — docs, articles, long-form, reference. The text is the interface. Measure,
leading and rhythm are the whole design. Almost nothing should compete with the prose;
a sidebar that draws the eye during a paragraph is a bug. Scale contrast comes from the
type ramp, not from colour.

**native** — iOS, Android, or a desktop app that should feel like the platform. Platform
convention outranks house style, and Dynamic Type and platform text scaling are not
optional. Importing web patterns here reads as a port, which is exactly what it is.

## Picking one

First match wins:

1. **What the task says.** "landing page" and "dashboard" are different modes and the
   user already told you which.
2. **The surface in focus.** The page, route or file being worked on — not the product
   overall. A marketing site has an `operate` account page, and a SaaS tool has a
   `persuade` pricing page. Mode is per surface.
3. **`visitor_mode` in the contract**, if one is declared.
4. **Ask.** One question, and only when the first three genuinely disagree.

## Why it is a gate rather than advice

A mode chosen after the design exists is a description of what got built. Declared first,
it is a constraint with teeth: it is what makes "this dashboard is too loud" a checkable
statement about density and colour dosage against a declared `operate`, rather than one
person's preference argued against another's.

Recorded in the contract, it also survives you. The next agent to touch the surface
inherits the decision instead of re-deciding it at random, which is how a product ends up
with four visual languages and no one able to say which is correct.
