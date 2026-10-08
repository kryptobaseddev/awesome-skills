# Anti-generic pass — chosen design, not the statistical average

Agent-built and template-built UIs converge on one look: Inter or system fonts everywhere, an indigo–purple
gradient, a centered hero with "Get started" and "Learn more", three equal icon cards, `rounded-2xl
shadow-lg` on every surface, and "Welcome back" copy. It isn't ugly. It's **unchosen**, and it usually
hides behavioral failures, because it passes the Aesthetic-Usability glance while failing Hick's, Fitts's,
Doherty, Postel's and Peak-End in the details.

What this pass is not: a claim that Inter or indigo is always wrong. A deliberately chosen Inter with a
real type scale is fine. The failure is defaults nobody chose. Banning a default without naming its
replacement just shifts the output to the next default, so every ban below comes with a replacement.

## Tells → replacements
| Tell | Law in tension | Replace with |
|---|---|---|
| One grotesk for display and body, by default | Aesthetic-Usability (hollow polish), Mental Model (no voice) | A chosen pairing (display + text, or one family with real contrast in weight and size), written in DESIGN.md |
| Indigo–purple gradient on hero, CTA, glow orbs | Von Restorff overused, Selective Attention | A palette from the brand or domain, with roles; one flat accent reserved for the primary action |
| Centered hero + dual equal CTAs | Hick's, Serial Position | One primary action; secondary as a text link; a content-led layout (product shot, live data, the actual tool) |
| Three equal icon cards | Hick's, Pareto, Choice Overload | The vital feature leads with real content (a screenshot, an example, a number with a shape); others demoted |
| Same radius and shadow on every surface | Common Region, Prägnanz | Radius follows size; shadow only on floating layers; flat grouping with spacing or hairlines elsewhere |
| Template copy ("Welcome back", "Build the future", "Everything you need") | Mental Model, Peak-End | Domain sentences: product name plus what it does for this user, in their words |
| Missing empty/loading/error/success | Doherty, Postel's, Peak-End | The four-state pattern (component-architecture.md §6) |
| Decorative icons and emoji-as-icon | Cognitive Load | Icons only where they encode meaning, one stroke, sized to type |
| Fake metrics, testimonials, "Trusted by" logo bars | Cognitive Bias (trust theater) | Real data, or nothing. Never placeholder social proof |
| Even density, the same gap everywhere | Proximity, Chunking | Tight within groups, loose between; dense where experts work |
| No focus/hover/active states | Fitts's, Doherty | Every state designed (component-architecture.md §5) |
| Gradient text on "AI" or "future" | Von Restorff, Cognitive Load | Plain text; let the product carry the claim |

The probe sees some of these (`system.fontFamilies`, `system.gradientElements`, `primaryActions`,
`copy.tells`, `system.radii/shadows`). The rest need a human look at the screenshots.

## Pre-ship checklist
**A. Hierarchy and decisions:** one primary action (Hick's, Von Restorff) · choices minimized or sequenced on the critical path (Choice Overload) · first and last positions used on purpose (Serial Position) · core tasks get the prominence (Pareto).

**B. Structure and perception:** related items grouped by proximity, region or connection (Gestalt) · spacing uneven on purpose (Proximity) · same function looks the same, different function looks different (Similarity) · reads as a simple structure (Prägnanz).

**C. Interaction and feedback:** targets big and spaced (Fitts's) · feedback within 400ms or a designed wait (Doherty) · empty, loading, error and success designed (Peak-End) · forgiving input and clear output (Postel's).

**D. Content and model:** domain language, not filler (Mental Model) · conventions for commodity UX (Jakob's) · complexity absorbed by defaults (Tesler's) · teaching in context (Paradox of the Active User) · visible progress on multi-step goals (Goal-Gradient).

**E. Aesthetics:** type pairing chosen · palette from the brand with roles · layout not "centered hero + 3 cards" unless intentional · limited, meaningful radius and shadow vocabulary · no decorative icons · no invented metrics or placeholder logos · focus, hover, active and disabled designed · contrast, visible focus, never color-only status.

**F. Memory of the journey:** peaks and endings designed (Peak-End) · incomplete work resumable (Zeigarnik).

## When the generic look is acceptable
Internal tools optimizing for speed can reasonably accept the centroid look. Say so explicitly in DESIGN.md
("internal; default shadcn theme accepted"), and still hold the behavioral guardrails: states, targets,
feedback and labels. Differentiation is optional there; usability isn't.
