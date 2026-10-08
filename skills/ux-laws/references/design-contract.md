# Design contract and direction loop

Two jobs: **lock** a design contract (DESIGN.md) before generating or restructuring UI, and, for
greenfield work or a redesign, **choose a direction** from real references instead of adjectives.

## Contents
1. Lock the contract (brownfield: extract it; greenfield: write it)
2. What DESIGN.md must contain
3. Direction loop (greenfield and redesigns)
4. Motion is a separate, explicit pass
5. Share prototypes as prototypes

---

## 1. Lock the contract
**Brownfield:** extract what's actually shipped before changing anything. Read the theme and token sources,
and measure what renders: `probe.system` lists the fonts, sizes, radii and shadows really in use, and
`inventory.style` shows where the literals are. The extracted contract usually has too many values. The
consolidation proposal is to keep the most-used value in each cluster and map the near-duplicates onto it
(13px, 14px and 15px → 14px). Show that mapping to the owner before rewriting.

**Greenfield:** write DESIGN.md from the product brief and the chosen direction (section 3) before
writing components. An agent generating UI without a contract falls back to its defaults (anti-generic.md).

Negation isn't a contract. "No Inter, no purple" moves the output to the next default. Name the replacement.

## 2. What DESIGN.md must contain
Copy `assets/DESIGN.template.md` into the project. Minimum sections:
- **Product and users:** a few sentences on what it's for and who uses it, on which devices (decides mobile-first priorities and density).
- **Type:** families and their roles, the scale (sizes with line heights), weights in use, and numeric style (tabular for data).
- **Color roles:** surface levels, text tiers, border, action, danger, warning, success and info, for both light and dark (dark follows component-systems.md → Dark mode).
- **Space, radius, shadow, motion:** short scales, with rules (radius follows size; shadow only on floating layers; motion durations and reduced-motion behavior).
- **Breakpoints and containers:** widths, and which components use container queries.
- **Density:** compact, default or comfortable, per area (ops tables compact, onboarding airy).
- **Component prop contract:** component-architecture.md §2.
- **Composition rules:** one primary action per view; surface by severity for feedback; the four states for data views; no primary behind hover.
- **Voice:** domain vocabulary, banned filler phrases, error and success copy patterns.
- **Accepted exceptions:** each with a reason (e.g. "default theme accepted for internal admin").

## 3. Direction loop (greenfield and redesigns)
Use this when the visual direction itself is undecided. Skip it for a brownfield cleanup that keeps the
current look.
1. **Name the product before the style.** A few sentences on what the page is for. Adjectives ("clean", "make it pop", "minimal") are the failure mode.
2. **Collect references from the same category first** (visual-quality.md §2): screenshot 3–6 real products with `walk.mjs`, and write down the structure they share before choosing any style. **Then collect taste references.** Screenshots of real pages you like, kept in a folder (a reference vault), grouped into named families in your own words (e.g. "editorial monumental", "product-led minimal", "technical systems"). An extracted system from a live site (a DESIGN.md-style export: type, color, spacing, buttons, layout) is the other way in. Keep adding over time.
3. **Generate several directions from one brief,** each tied to a different family. If a design skill or plugin is in play, also generate a **no-skill baseline** of the same family. Compare side by side before deciding a tool helped; baseline output isn't automatically worse.
4. **Pick one family, then a few variations inside it.** Small flavor changes are normal; ask explicitly for a bigger jump if you want one.
5. **Micro-edit with visible controls** (type weight, size, letter spacing, image treatment, accent, grid) or with one copied component from a component gallery, rather than a new prompt per pixel. A single good component can set the direction for the page.
6. **Look at it.** Screenshot at 390 and 1440 (browser-walkthrough.md), and judge from the pixels, not the description.
7. **Lock DESIGN.md** from the chosen direction, then build components against it.

## 4. Motion is a separate, explicit pass
Don't add motion by default. If you add it, write down which rule set you follow. A sensible default set:
- motion explains change (enter, exit, reorder, state); it doesn't decorate;
- springs or ease-out at most with a tiny overshoot; no bouncy easing, particle bursts, glows or gradients on UI chrome;
- durations from tokens; feedback motion starts within 100ms, and the full response lands inside Doherty's 400ms;
- everything honors `prefers-reduced-motion: reduce` (cross-fade or no motion);
- never invent copy or data for an animated demo; use the product's real components and words.
If a project's own motion guide says otherwise, it wins. Cite it.

## 5. Share prototypes as prototypes
Quick-share hosting (preview deployments, sandbox sites) is for feedback. Label those links as prototypes in
the report, and don't describe them as production.
