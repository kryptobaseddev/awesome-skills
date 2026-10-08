# Visual quality gate — a green scorecard is not a good design

The scorecard measures what can be counted: reflow, targets, labels, contrast, sprawl. It can't see that a
product photo shows coffee beans for a watch, that a sticky bar covers the field you're typing in, that a
price sits lower than its title, or that the page reads as one more template. **Every changed screen gets
this gate after the scorecard, from screenshots you actually look at.**

What this gate draws on: the Laws of UX (lawsofux.com), the project-owner's Anti-AI Generic UI checklist
(anti-generic.md), and taste rules in the style of the `design-taste-frontend` skill. If that skill is
installed, use it for marketing and landing surfaces (heroes, feature sections, portfolios). This skill
owns product surfaces (forms, tables, settings, dashboards, checkout), which that skill explicitly leaves out.

## Contents
1. Screenshot review protocol
2. References before taste (the new-template trap)
3. Design read and dials
4. Locks (accent, shape, theme, type)
5. Imagery
6. Copy
7. Layout tells
8. Worked example (the bundled before/after fixture)

---

## 1. Screenshot review protocol
- **Review viewport slices, not only full-page captures.** Full-page screenshots repaint fixed and sticky elements (tab bars, sticky actions, headers) in the wrong place, so they both invent overlaps and hide real ones. `walk.mjs --slices` saves viewport-height shots down the page; review those at 390 and 1440.
- **Interact before you judge:** focus a field, submit invalid, open a menu, add to cart, and screenshot each state. "Focus not obscured" (WCAG 2.4.11) failures only appear with the keyboard or the sticky bar in play.
- **Check both color schemes** (`colorScheme: 'dark'` in Playwright, or DevTools rendering emulation).
- **Read the screenshot like a stranger:** in 5 seconds, what is this and what do I do? Then check alignment baselines (title vs price), image-to-content match, crowding at the thumb zone, and anything clipped or overlapping.
- Write what you saw into the report next to the scorecard. Visual findings cite a law like any other finding (Prägnanz, Common Region, Von Restorff, Aesthetic-Usability, Mental Model).

## 2. References before taste
**The most common failure is not the old AI look; it's the new one.** Ban Inter and purple and the output
moves to Geist with an emerald accent, a split hero with headline, subtext, button and text link, rounded
bordered cards with outline buttons, and a row of three icon-plus-bold-lead-in facts. It's still a template,
just a newer one. Swapping tokens doesn't change the structure, and the structure is what reads as generated.

The fix is Jakob's Law applied to taste: **every category has its own conventions, and generated UI imports
generic SaaS conventions instead.** Before designing, capture 3–6 real products in the same category and
copy their *structure*, not their pixels:
```bash
node <skill>/scripts/walk.mjs --base https://www.example-retailer.com --routes / --widths 390,1440 --out ux-audit/refs/example
```
Then write down what they share. For example, outdoor and apparel retail (Norse Projects, Satisfy, Arc'teryx,
Patagonia) shares:
- full-bleed, art-directed photography as the design, with the hero as a photo plus a short caption;
- small, monochrome, square UI chrome in a neo-grotesk, with color coming from the photos and not from button accents;
- product grids with no card chrome: image on a neutral ground, then name, price and color swatches, with no button;
- trust facts in a thin announcement bar;
- prices set in mono or tabular figures.

SaaS dashboards, banking, healthcare and media each have different conventions. Look them up the same way,
and cite the references in DESIGN.md. If the owner has a brand or a reference vault, that comes first.

## 3. Design read and dials
Before redesigning a surface, state one line: *"Reading this as: <surface> for <audience>, with a <vibe>
language, leaning toward <system or aesthetic>."* Then set three dials and let them gate decisions:

| Dial | 1–3 | 4–7 | 8–10 |
|---|---|---|---|
| Variance | symmetric, predictable (forms, settings, public sector) | offset, varied ratios (commerce, SaaS) | asymmetric, editorial (marketing, portfolio) |
| Motion | hover/active only | short transitions on state change | choreographed (marketing only) |
| Density | airy (onboarding, landing) | daily app | cockpit (ops tables, dashboards: hairlines, no card boxes, tabular numbers) |

Write the design read from the references, not from adjectives. Product UI usually sits at variance 3–5, motion 2–4, density 4–7. A brownfield cleanup that keeps the brand
matches the existing dials. Say when you're changing them.

## 4. Locks
- **Accent lock:** one accent hue for actions across the whole product; status colors (danger, success, warning) are semantic, not decorative. `probe.taste.accentHues` above 2 means drift.
- **Shape lock:** one radius scale with a written rule (e.g. inputs and buttons 10, cards 14, pills only for single-line chips). Mixed pill buttons and square cards without a rule read as broken.
- **Theme lock:** one theme per page, light/dark through tokens, both tested. No section flips to the inverse theme mid-page unless it's a deliberate, single device.
- **Type lock:** one family (or a justified pair) and a short scale. Don't default to Inter, and don't reach for a serif because something "feels premium"; choose for the brand and write it in DESIGN.md. Emphasis inside a headline uses the same family's weight or italic, not a second family.
- **Icon lock:** one icon library with one stroke width. No hand-drawn SVG icons, and no emoji as UI icons (`probe.taste.emoji`).

## 5. Imagery
- **Images must depict the thing they label.** Random placeholder services (`picsum` seeds and similar) return unrelated photos; a coffee-bean photo on a watch card is worse than no photo. Use the product's real assets, a generation tool if one is available, or verified stock whose content you've looked at. Otherwise leave a labeled placeholder slot and list it for the owner.
- No div-built fake screenshots or fake dashboards as hero art. Show the real UI or a real photo.
- Fixed aspect ratios on media (no layout shift); `alt` describes the image's content; photos dim slightly in dark mode.
- No text pills overlaid on photos, and no decorative photo-credit captions.

## 6. Copy
- **No em or en dashes in UI copy** (`probe.taste.emDashes`); they're the strongest single tell of generated text. Use a period, comma, colon or parentheses.
- Domain words, not filler ("Welcome back", "Elevate", "Seamless", "Build the future"). Read every visible string aloud once; rewrite anything cute-but-wrong into a plain sentence.
- **No fake-precise numbers:** a number is either real (brief, data) or visibly marked as sample.
- One label per intent across the page ("Add to cart" everywhere, not "Buy" / "Grab deal" / "Add"). CTA labels fit on one line at desktop and are 1–3 words where possible.
- Success names the object, the recipient and the date; errors say what happened and what to do.

## 7. Layout tells
- **Eyebrows** (small uppercase tracked labels above headings): at most one per three sections (`probe.taste.eyebrows`).
- No three equal feature cards; no centered hero with two equal CTAs; no logo walls with category labels; no section-number labels ("01 / Features"); no decorative status dots; no scroll cues.
- Cards only where the boundary means "one thing" (a product, a record). Elsewhere group with spacing or a hairline (Common Region).
- Hero (where one exists): headline at most 2 lines, subtext at most about 20 words, one primary action plus at most one text link, all visible without scrolling.
- Sticky and fixed UI on phones never covers the focused field, its error, or the primary action (WCAG 2.4.11). Add `scroll-margin`/`scroll-padding` for sticky bars and scroll the first invalid field into view.
- Prices and other numbers share a baseline with their labels and use tabular figures.

## 8. Worked example
The skill bundles a deliberately broken shop and a rebuilt version of the same content, so you can see
both sides of every rule above:
- `evals/files/brownfield-shop-static/index.html`: **before**. Inter on an indigo-to-pink gradient hero, "Build the future" with dual equal CTAs, three emoji feature cards, a 1200px fixed deals row (overflows phones), a 10-link nav at 15px, a placeholder-only 11-field checkout that submits by GET, hover-only actions, and no viewport meta. Scorecard: 8 FAIL, 10 WARN.
- `evals/files/brownfield-shop-after/index.html`: **after**, in its second version. The first version cleared every measured guardrail and was still rejected as "too AI-generated" by the owner. It was the new template from §2: Geist, an emerald accent, a split hero, bordered rounded cards with outline buttons, and an icon-facts row. The rebuild started from category references instead:
  - system neo-grotesk with mono prices, monochrome square chrome, color only from photos;
  - a thin announcement bar holding the trust facts;
  - a full-bleed hero photo with a one-line caption and a text link;
  - a product grid of image, name, price and swatches with no card chrome;
  - an editorial split for the repair program;
  - checkout as its own route: three steps, labels, autocomplete and inputmode, in-step validation, state that survives refresh without card data, a non-sticky header so the sticky pay bar owns the bottom;
  - dark mode by tokens.

  Scorecard: 0 FAIL, 0 WARN. Visual review across both versions caught what the numbers passed: off-brand random photos, a price baseline offset, an sr-only label escaping a scroller and widening the page, a sticky bar covering the focused field, a broken icon CDN path, and an announcement bar wrapping on phones. A probe flaw (caption text over a photo measured against the wrong background) was also fixed; that text is now reported as unmeasurable for a manual check.

Serve both with `python3 -m http.server` and walk them with `walk.mjs --slices` to calibrate your eye before
auditing a real app.
