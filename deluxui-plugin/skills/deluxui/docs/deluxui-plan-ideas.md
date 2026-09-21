The rulebook and Impeccable overlap, but they operate at different layers.

Impeccable is primarily an AI design skill and workflow system. It gives an agent design vocabulary, specialized operations such as `critique`, `layout`, `typeset`, `polish`, `harden`, `optimize`, and `document`, project context through `PRODUCT.md`, design-system memory through `DESIGN.md`, browser-assisted iteration, and automated detection of common AI design problems. ([Impeccable Style][1])

Our `UX_UI_AGENT_RULES.md` is closer to a design constitution. It tells an agent what properties an interface must satisfy. It contains explicit requirements, UX laws, accessibility constraints, interaction rules, acceptance tests, and verification requirements.

So I would not describe our current file as "better than Impeccable."

I would build something substantially bigger that combines both concepts.

### What I think we should build

Think:

```text
IMPECCABLE
+
UX LAWS
+
WCAG / ACCESSIBILITY
+
DESIGN SYSTEM ENGINE
+
PRODUCT CONTEXT
+
INTERACTION ENGINEERING
+
RESPONSIVE RULES
+
PERFORMANCE UX
+
MOBILE UX
+
AI-SLOP DETECTION
+
AUTOMATED QA
+
VISUAL QA
+
AGENT WORKFLOWS
=
OUR UX ENGINEERING SKILL
```

That would be an improvement over simply giving an agent our 209 rules because rules alone don't tell the agent how to work.

Impeccable's architecture solves that problem particularly well. Its current system has a single primary skill with focused operations underneath it. Its documentation lists creation, evaluation, refinement, simplification, hardening, and system operations. ([Impeccable Style][2])

It also separates product knowledge from visual-system knowledge. `PRODUCT.md` records audience, purpose, and constraints. `DESIGN.md` records the established visual system. ([Impeccable Style][3])

That separation is worth adopting.

### Where ours could go considerably further

Impeccable now has deterministic detection too. Its current site says its detector has 61 checks, while its April 2026 v2.0 announcement described the earlier version as having 28 deterministic rules. It can inspect source and rendered interfaces and feed findings back into the agent. ([Impeccable Style][4])

I would take that concept much further.

```text
ux-engine/
│
├── SKILL.md
│
├── PRODUCT.md
├── DESIGN.md
│
├── UX-CONFIG.yaml
│
├── rules/
│   ├── ux-laws.md
│   ├── hierarchy.md
│   ├── layout.md
│   ├── typography.md
│   ├── color.md
│   ├── navigation.md
│   ├── interaction.md
│   ├── forms.md
│   ├── feedback.md
│   ├── states.md
│   ├── accessibility.md
│   ├── responsive.md
│   ├── mobile.md
│   ├── motion.md
│   ├── performance.md
│   ├── content.md
│   ├── onboarding.md
│   ├── errors.md
│   └── anti-patterns.md
│
├── workflows/
│   ├── create.md
│   ├── redesign.md
│   ├── critique.md
│   ├── audit.md
│   ├── polish.md
│   ├── simplify.md
│   ├── harden.md
│   ├── accessibility.md
│   ├── responsive.md
│   └── optimize.md
│
├── checks/
│   ├── static/
│   ├── browser/
│   ├── accessibility/
│   ├── responsive/
│   └── performance/
│
└── templates/
    ├── design-brief.md
    ├── component-contract.md
    ├── audit-report.md
    └── exception.md
```

And the main skill would enforce an execution loop rather than merely supplying design advice.

```text
REQUEST
   ↓
UNDERSTAND USER + JOB
   ↓
READ PRODUCT.md
   ↓
READ DESIGN.md
   ↓
INSPECT EXISTING UI
   ↓
CLASSIFY SCREEN / TASK
   ↓
SELECT APPLICABLE UX RULES
   ↓
PLAN
   ↓
IMPLEMENT
   ↓
RENDER
   ↓
VISUAL INSPECTION
   ↓
STATIC UX CHECK
   ↓
ACCESSIBILITY CHECK
   ↓
RESPONSIVE CHECK
   ↓
INTERACTION / STATE CHECK
   ↓
PERFORMANCE CHECK
   ↓
FIX VIOLATIONS
   ↓
RE-RUN CHECKS
   ↓
REPORT
```

That last half is important.

The agent shouldn't be allowed to say:

```text
Looks good.
```

It should need evidence.

For example:

```yaml
ux_validation:
  hierarchy: PASS
  proximity: PASS
  target_size: PASS
  keyboard_navigation: PASS
  focus_visibility: PASS
  contrast: PASS
  responsive_320: PASS
  responsive_768: PASS
  responsive_1440: PASS
  empty_state: PASS
  loading_state: PASS
  error_state: PASS
  destructive_action: PASS
  layout_shift: PASS
  interaction_feedback: PASS

violations: 0
warnings: 2
not_run: 0
```

That changes the skill from "AI knows some design principles" into an actual UI engineering governance system.

### One thing I would not do

I would not install Impeccable and then simultaneously give another agent an enormous competing design prompt.

Interestingly, Impeccable itself warns against overlapping design skills because they can pull the agent in different directions. ([Impeccable Style][5])

Instead, choose one of two architectures.

Use Impeccable as the design engine and add our stricter UX engineering rules around it.

Or build our own unified skill inspired by the workflow concepts, without copying Impeccable's implementation or documentation.

I prefer the second option for what you're describing.

It gives us control over everything and lets us make it framework-aware for the kind of applications you're actually developing.

We could make it understand React, Next.js, Tailwind, shadcn, Radix, React Native, SwiftUI, and other stacks while maintaining the same UX contract.

It could even enforce:

```text
NO arbitrary gradients
NO excessive cards
NO card-inside-card layouts
NO meaningless icons
NO tiny controls
NO mystery navigation
NO placeholder-only forms
NO unnecessary modals
NO layout shift
NO inaccessible custom controls
NO fake loading
NO dead-end empty states
NO desktop-only responsive assumptions
NO destructive actions without recovery
NO animation without purpose
NO rebuilding existing design-system components
NO adding UI libraries without checking project dependencies
```

But importantly, these would not just be prompt instructions.

Where technically detectable, they become tests.

### The bigger opportunity

I would actually expand beyond the original "20 UX laws."

Those laws are useful reasoning primitives. They are not sufficient to govern production application design.

The skill should reason across roughly these layers:

```text
01 Product intent
02 User intent
03 Information architecture
04 Cognitive load
05 Visual hierarchy
06 Gestalt principles
07 Interaction design
08 Navigation
09 Forms and input
10 Feedback
11 System status
12 Error prevention
13 Error recovery
14 Accessibility
15 Typography
16 Color
17 Spacing
18 Layout
19 Responsive behavior
20 Mobile ergonomics
21 Touch interaction
22 Keyboard interaction
23 Motion
24 Loading behavior
25 Perceived performance
26 Actual performance
27 Empty states
28 First-run experience
29 Progressive disclosure
30 Data visualization
31 Design-system consistency
32 Component reuse
33 Content and microcopy
34 Trust and safety
35 Platform conventions
36 AI design anti-patterns
37 Visual QA
38 Functional QA
39 Accessibility QA
40 Release verification
```

The original rulebook becomes one knowledge layer inside this rather than being the entire skill.

And there is another major advantage.

Impeccable explicitly allows the designer to preserve existing decisions during focused improvements rather than indiscriminately redesigning everything. ([Impeccable Style][6])

We should make that a hard rule:

```text
PRESERVE > MODIFY > CREATE > REPLACE
```

Meaning the agent first asks:

```text
Can I preserve the existing component?

No →
Can I modify it?

No →
Can I compose existing primitives?

No →
Create a new primitive.
```

That will dramatically reduce the tendency of coding agents to turn a mature application into a collection of unrelated AI-generated interfaces.

So yes, I think this is worth doing. I would call what we have now Version 0 of the knowledge base, not the finished product. The finished version should be a complete installable agent skill with perhaps 300 to 500 normalized rules, specialized workflows, machine-testable checks, browser validation instructions, project context, design-system memory, framework awareness, and a strict build → inspect → test → fix loop.

[Impeccable documentation](https://impeccable.style/docs/?utm_source=chatgpt.com)

The next move should be to turn the Markdown we already created into that full skill architecture rather than merely adding more rules to the existing file.

[1]: https://impeccable.style/docs/impeccable/?utm_source=chatgpt.com "impeccable | Impeccable"
[2]: https://impeccable.style/docs "Docs | Impeccable"
[3]: https://impeccable.style/docs/init/?utm_source=chatgpt.com "init | Impeccable"
[4]: https://impeccable.style/changelog/?utm_source=chatgpt.com "Changelog | Impeccable"
[5]: https://impeccable.style/designing/?utm_source=chatgpt.com "Designing with Impeccable"
[6]: https://impeccable.style/docs/improve-design/?utm_source=chatgpt.com "Improve an existing design | Impeccable"

