# The 30 Laws of UX — audit lenses

Source: [Laws of UX](https://lawsofux.com/) by Jon Yablonski ([llms.txt](https://lawsofux.com/llms.txt)).
Definitions below are short quotations with a link, so they can be cited exactly. The site's content is
CC BY-NC-ND 4.0: quote and link it, but don't paste or rewrite its pages into deliverables. The **Check**,
**Evidence** and **AI tell** lines are product-UI synthesis, not text from the site.

Cite a failure as: **law name + URL + what is wrong + concrete fix**. Never attach an invented lift
("+23% conversion") to a law. The only numbers the site itself states are Doherty **<400ms**, Miller
**7±2** (which the site warns against using as a hard limit) and Pareto **80/20**.

## Contents
- [Lens 1 — Decisions](#lens-1--decisions): Hick's, Choice Overload, Pareto, Occam's Razor, Parkinson's
- [Lens 2 — Perception and grouping](#lens-2--perception-and-grouping): Proximity, Similarity, Common Region, Uniform Connectedness, Prägnanz, Von Restorff, Aesthetic-Usability
- [Lens 3 — Memory](#lens-3--memory): Miller's, Working Memory, Chunking, Serial Position, Zeigarnik
- [Lens 4 — Motor and time](#lens-4--motor-and-time): Fitts's, Doherty Threshold, Flow
- [Lens 5 — Expectations](#lens-5--expectations): Jakob's, Mental Model, Paradox of the Active User, Postel's, Tesler's
- [Lens 6 — Attention, experience and ethics](#lens-6--attention-experience-and-ethics): Cognitive Load, Selective Attention, Peak-End, Goal-Gradient, Cognitive Bias
- [Law → component system map](#law--component-system-map)

Evidence keys: `probe.*` = a field in probe.js output, `inv.*` = a field in inventory.json, *manual* = a
human or agent has to look, click or time it.

---

## Lens 1 — Decisions

### Hick's Law — https://lawsofux.com/hicks-law/
> "The time it takes to make a decision increases with the number and complexity of choices."
- **Check:** one primary action per view; recommended option highlighted; complex tasks split into steps; nav and settings not flat walls. Don't oversimplify into abstraction.
- **Evidence:** `probe.primaryActions.firstViewportFilled` (≤1), `probe.structure.topNavLinks` (a review trigger above ~7), `probe.fields.forms[].fields`.
- **AI tell:** "Get started" + "Learn more" with equal weight, plus three equal feature cards.

### Choice Overload — https://lawsofux.com/choice-overload/
> "The tendency for people to get overwhelmed when they are presented with a large number of options, often used interchangeably with the term paradox of choice."
- **Check:** featured or default option, filters, side-by-side compare when choice is real; progressive disclosure for the rest.
- **Evidence:** count of equal-weight options per decision (*manual*); `inv.families` showing many near-identical variants.
- **AI tell:** 3- or 6-card grids where everything is equally important.

### Pareto Principle — https://lawsofux.com/pareto-principle/
> "The Pareto principle states that, for many events, roughly 80% of the effects come from 20% of the causes."
- **Check:** the core tasks get disproportionate prominence; rare power features are demoted, not deleted.
- **Evidence:** compare visual weight to usage (analytics if available; otherwise ask) — *manual*.
- **AI tell:** identical cards for every capability.

### Occam's Razor — https://lawsofux.com/occams-razor/
> "Among competing hypotheses that predict equally well, the one with the fewest assumptions should be selected."
- **Check:** every element earns its place; one clear path beats several weak ones; one component beats four near-copies.
- **Evidence:** `inv.families` with >1 member, `inv.unused`, duplicate names.
- **AI tell:** logo clouds, fake testimonials and three pricing tiers added by default.

### Parkinson's Law — https://lawsofux.com/parkinsons-law/
> "Any task will inflate until all of the available time is spent."
- **Check:** flows are bounded: sensible defaults, autofill, short forms, a recommended path through configuration.
- **Evidence:** steps and fields on the critical path (*manual*), `autocomplete` attributes (`probe.fields.forms[].autocomplete`).
- **AI tell:** "build your own" configurators with no recommended path.

## Lens 2 — Perception and grouping

### Law of Proximity — https://lawsofux.com/law-of-proximity/
> "Objects that are near, or proximate to each other, tend to be grouped together."
- **Check:** tight spacing inside a group, looser between groups; labels sit on their fields; actions sit on their objects.
- **Evidence:** screenshots at 390 and 1440 (*manual*); `probe.system.spacingValues` (too few = uniform gaps, too many = no scale).
- **AI tell:** the same `gap-6` everywhere, so everything looks equally related.

### Law of Similarity — https://lawsofux.com/law-of-similarity/
> "The human eye tends to perceive similar elements as a complete picture, shape, or group, even if those elements are separated."
- **Check:** same function looks the same everywhere; different function looks different. This is the law that component consolidation enforces.
- **Evidence:** `inv.families`, `inv.raw_element_bypass`, `inv.style.token_adoption`, `probe.system.fontSizes / radii / shadows`.
- **AI tell:** gradient, outline and ghost buttons with no role system; identical cards for different content types.

### Law of Common Region — https://lawsofux.com/law-of-common-region/
> "Elements tend to be perceived into groups if they are sharing an area with a clearly defined boundary."
- **Check:** cards, panels and bordered groups mean something; not every section is a card.
- **Evidence:** `probe.system.shadows`, `probe.system.radii`; screenshots.
- **AI tell:** every section is a `rounded-2xl shadow-lg` card.

### Law of Uniform Connectedness — https://lawsofux.com/law-of-uniform-connectedness/
> "Elements that are visually connected are perceived as more related than elements with no connection."
- **Check:** steppers, breadcrumbs, connected rows and shared backgrounds show real relationships; decorative lines don't imply false ones.
- **Evidence:** *manual* on multi-step flows and lists.
- **AI tell:** orphan step cards with nothing linking them.

### Law of Prägnanz — https://lawsofux.com/law-of-pr%C3%A4gnanz/
> "People will perceive and interpret ambiguous or complex images as the simplest form possible, because it is the interpretation that requires the least cognitive effort of us."
- **Check:** layouts read as simple structure; state is never carried only by an illustration; icons are unambiguous.
- **Evidence:** squint test on screenshots (*manual*); `probe.system.gradientElements`.
- **AI tell:** decorative blobs, overlapping glass panels, ambiguous icon metaphors.

### Von Restorff Effect — https://lawsofux.com/von-restorff-effect/
> "The Von Restorff effect, also known as The Isolation Effect, predicts that when multiple similar objects are present, the one that differs from the rest is most likely to be remembered."
- **Check:** exactly one thing is distinct per view (the primary action or the key status); distinction isn't color-only; motion respects `prefers-reduced-motion`.
- **Evidence:** `probe.primaryActions`, `probe.text.lowContrast`, `probe.system.gradientElements`.
- **AI tell:** glowing CTAs everywhere, gradient text on "AI"; or no difference between primary and secondary.

### Aesthetic-Usability Effect — https://lawsofux.com/aesthetic-usability-effect/
> "Users often perceive aesthetically pleasing design as design that's more usable."
- **Check:** polish supports hierarchy; usability is tested separately from looks, because polish hides bugs in review.
- **Evidence:** the whole scorecard. A screen that looks great but FAILs states, targets or contrast is this law's warning.
- **AI tell:** uniform gloss masking missing states, contrast and hierarchy.

## Lens 3 — Memory

### Miller's Law — https://lawsofux.com/millers-law/
> "The average person can only keep 7 (plus or minus 2) items in their working memory."
- **Check:** chunk content so users never hold unbound items. **Do not** use 7±2 as a hard cap on nav items or options; the site itself warns against that.
- **Evidence:** chunking of long lists and forms (*manual*).
- **AI tell:** long unlabeled icon rows; sprawling settings with no groups.

### Working Memory — https://lawsofux.com/working-memory/
> "A cognitive system that temporarily holds and manipulates information needed to complete tasks."
- **Check:** state is externalized: persistent labels (not placeholder-only), step summaries, visible selections, recent items.
- **Evidence:** `probe.fields.unlabeled`, icon-only nav (`probe.targets.unnamed`).
- **AI tell:** placeholder-as-label fields; wizards that make you remember step 1 on step 4.

### Chunking — https://lawsofux.com/chunking/
> "A process by which individual pieces of an information set are broken down and then grouped together in a meaningful whole."
- **Check:** long forms are split by context (who, where, how to pay, review), not by equal field counts; content has labeled modules and a sane heading outline.
- **Evidence:** `probe.fields.forms[].fields` (a single wall above ~7 visible fields is a review trigger), `probe.structure.headingSkips`.
- **AI tell:** one 12-field wall; "Feature 1/2/3" labels.

### Serial Position Effect — https://lawsofux.com/serial-position-effect/
> "Users have a propensity to best remember the first and last items in a series."
- **Check:** key destinations first and last in nav; critical actions at the start and end of flows; mobile tab bars put the most-used items at the ends.
- **Evidence:** nav order vs usage (*manual*).
- **AI tell:** alphabetical or arbitrary nav order.

### Zeigarnik Effect — https://lawsofux.com/zeigarnik-effect/
> "People remember uncompleted or interrupted tasks better than completed tasks."
- **Check:** drafts persist; "continue where you left off"; multi-step forms survive Back and refresh.
- **Evidence:** reload mid-flow and check (*manual*); `localStorage`/server draft in source.
- **AI tell:** no resume; or guilt counters with no next action.

## Lens 4 — Motor and time

### Fitts's Law — https://lawsofux.com/fittss-law/
> "The time to acquire a target is a function of the distance to and size of the target."
- **Check:** primary targets are big, spaced, and near where the thumb or cursor already is (mobile: bottom half, sticky primary action on long forms). Pad the hit area; the icon can stay small.
- **Evidence:** `probe.targets.below24` (WCAG 2.5.8 floor), `probe.targets.below44` on coarse pointers, `probe.chrome.fixedViewportShare`.
- **AI tell:** tiny icon-only toolbars, cramped ghost buttons, footer-only CTAs.

### Doherty Threshold — https://lawsofux.com/doherty-threshold/
> "Productivity soars when a computer and its users interact at a pace (<400ms) that ensures that neither has to wait on the other."
- **Check:** visible feedback within 400ms of every action, or a designed wait (skeleton, progress, optimistic UI, streaming). Every data view has loading, empty, error and success.
- **Evidence:** `inv.data_views`, `probe.perf`, *manual* timing of clicks (`feedback_ms`), INP from field data where available.
- **AI tell:** silent buttons; spinners blocking the whole page; no loading state at all.

### Flow — https://lawsofux.com/flow/
> "The mental state in which a person performing some activity is fully immersed in a feeling of energized focus, full involvement, and enjoyment in the process of the activity."
- **Check:** no modal spam, forced tours or mid-task upsells; no iOS focus-zoom jolt (inputs ≥16px); continuous feedback.
- **Evidence:** `probe.fields.below16px`, modal count on the critical path (*manual*).
- **AI tell:** generic onboarding modals that interrupt before teaching anything.

## Lens 5 — Expectations

### Jakob's Law — https://lawsofux.com/jakobs-law/
> "Users spend most of their time on other sites. This means that users prefer your site to work the same way as all the other sites they already know."
- **Check:** commodity UX (auth, nav, search, forms, settings, checkout) follows platform conventions; differentiate with type, color, density and domain copy instead. When redesigning, give a familiar path back for a while.
- **Evidence:** native controls replaced by look-alikes without affordances (*manual*); `probe.hover.revealOnHoverRulesNotGuarded` (hover-only patterns break phone conventions).
- **AI tell:** over-copied SaaS templates (fine) or invented controls with no affordance (not fine).

### Mental Model — https://lawsofux.com/mental-model/
> "A compressed model based on what we think we know about a system and how it works."
- **Check:** labels, IA and copy use the user's domain words, not database or API names; success and error copy name the actual thing.
- **Evidence:** `probe.copy.tells`; read the nav and buttons aloud (*manual*).
- **AI tell:** "Dashboard / Projects / Settings" IA and "Welcome back" filler.

### Paradox of the Active User — https://lawsofux.com/paradox-of-the-active-user/
> "Users never read manuals but start using the software immediately."
- **Check:** teach in context: empty states that say what to do, inline hints, sensible defaults, fast first success.
- **Evidence:** first-run and empty states (*manual*; force them, see browser-walkthrough.md).
- **AI tell:** a 5-slide carousel tour; blank first-run screens.

### Postel's Law — https://lawsofux.com/postels-law/
> "Be liberal in what you accept, and conservative in what you send."
- **Check:** accept messy input (spaces in card numbers, pasted phone formats, any date style), normalize it, and say clearly what happened; correct `type`/`inputmode`/`autocomplete`.
- **Evidence:** `probe.fields.typeHints`, `probe.fields.forms[].autocomplete`; paste-test fields (*manual*).
- **AI tell:** forms that look complete with no validation or recovery.

### Tesler's Law — https://lawsofux.com/teslers-law/
> "Tesler's Law, also known as The Law of Conservation of Complexity, states that for any system there is a certain amount of complexity which cannot be reduced."
- **Check:** the system absorbs irreducible complexity through defaults, automation and progressive disclosure. In component terms, the shared component absorbs states, a11y and responsive behavior so every call site doesn't re-implement them.
- **Evidence:** settings exposed vs. defaulted (*manual*); call sites re-implementing loading/error (`inv.data_views`).
- **AI tell:** empty shells, or every setting dumped on one page.

## Lens 6 — Attention, experience and ethics

### Cognitive Load — https://lawsofux.com/cognitive-load/
> "The amount of mental resources needed to understand and interact with an interface."
- **Check:** cut extraneous load (decoration, duplicate CTAs, novelty); structure intrinsic load (steps, disclosure).
- **Evidence:** `probe.text.below12px`, decorative icon count, `probe.system.*` sprawl.
- **AI tell:** decorative Lucide icons, emoji-as-icon, busy bento grids.

### Selective Attention — https://lawsofux.com/selective-attention/
> "The process of focusing our attention only to a subset of stimuli in an environment — usually those related to our goals."
- **Check:** critical info sits where attention already is; nothing banner-like competes with the task; fixed chrome doesn't eat the phone screen.
- **Evidence:** `probe.chrome.fixedViewportShare`, `probe.system.gradientElements`.
- **AI tell:** everything equally loud.

### Peak-End Rule — https://lawsofux.com/peak-end-rule/
> "People judge an experience largely based on how they felt at its peak and at its end, rather than the total sum or average of every moment of the experience."
- **Check:** success says what happened and what's next; errors are human and recoverable; journeys never end on a blank screen.
- **Evidence:** forced error and success states (*manual*); `probe.copy.tells` ("An error occurred", "Success!").
- **AI tell:** flows that dump you on "Welcome back".

### Goal-Gradient Effect — https://lawsofux.com/goal-gradient-effect/
> "The tendency to approach a goal increases with proximity to the goal."
- **Check:** multi-step flows show honest progress (one pattern: bar, dots or labeled steps).
- **Evidence:** *manual* on wizards and onboarding.
- **AI tell:** "Step 1 of N" with no sense of what remains; fake near-completion.

### Cognitive Bias — https://lawsofux.com/cognitive-bias/
> "A systematic error of thinking or rationality in judgment that influence our perception of the world and our decision-making ability."
- **Check:** defaults and framing serve the user's goal; no fake urgency, hidden costs, invented social proof or "Most popular" badges without data.
- **Evidence:** copy and pricing review (*manual*).
- **AI tell:** invented KPIs, placeholder "Trusted by" logo bars.

---

## Law → component system map

Use this to decide which laws to load when auditing one component family (see component-systems.md).

| System | Primary laws |
|---|---|
| Buttons / CTAs | Hick's, Von Restorff, Fitts's, Similarity |
| Cards / tiles | Common Region, Proximity, Similarity, Pareto, Chunking |
| Forms / wizards / fields | Chunking, Postel's, Working Memory, Goal-Gradient, Zeigarnik, Fitts's |
| Search | Hick's, Postel's, Paradox of the Active User, Doherty |
| Errors | Postel's, Peak-End, Doherty, Mental Model |
| Toasts / notifications | Selective Attention, Flow, Doherty |
| Settings | Tesler's, Hick's, Chunking, Choice Overload |
| Tables / lists | Similarity, Proximity, Serial Position, Fitts's (row actions) |
| Navigation | Jakob's, Serial Position, Hick's, Fitts's (thumb zone) |
| Modals / sheets | Flow, Selective Attention, Jakob's |
| Empty / loading / success | Doherty, Peak-End, Paradox of the Active User |
| Login / auth | Jakob's, Hick's, Mental Model, Postel's |
| Dashboards | Pareto, Selective Attention, Von Restorff, Cognitive Load |
