# Component contract — <name>

Fill this in **before** writing the markup. It takes two minutes and it is the
difference between a component and a picture of one.

**Task purpose.** What can the user finish with this that they could not before?

**Platform and stack.** Where it renders, and which primitive it is built from.

**Reuse decision.** Which existing component or primitive this is built from, or why
none fitted. (`PRESERVE > MODIFY > COMPOSE > CREATE`.)

**Semantic role.** The native element or ARIA role. Native first — `<button>`,
`<dialog>`, `<details>`, the `popover` attribute — because they bring behaviour you
would otherwise have to rebuild and get wrong.

**Accessible name.** Where it comes from, and whether the visible text is inside it
(COMP-002: speech users activate controls by what they can see).

**States.** Which of these it can reach, and what each looks like:
default · hover · focus-visible · active · selected · disabled · pending · error ·
empty · loading · stale · forbidden

**Keyboard pattern.** Named — an APG pattern or a native element's behaviour. Include
where focus enters and where it goes on exit.

**Target size.** The hit area for each supported platform. Measure the touch target,
not the icon.

**Data dependencies.** What it needs, and what it renders when that is missing, slow,
stale or forbidden.

**Responsive behaviour.** What changes and at which container width. Prefer
`@container` — a component keyed to the viewport breaks the moment it is reused in a
sidebar.

**Rules that apply.** The rule IDs you will verify.

**How it will be verified.** Which detectors, which manual checks.
