# Brownfield decomposition — find every component, where it lives, and what it should become

The goal is a map you can restructure from: every UI component, every place it's used, which ones are the
same thing built twice, where the app bypasses its own library, and how users move between screens.
Restructuring without this map is how redesigns break checkout.

## Contents
1. Set up the audit folder
2. Run the inventory, then verify it
3. Classify into layers
4. Map where everything is used (blast radius)
5. Map the app flow
6. Find the consolidation candidates
7. Write the consolidation plan
8. Migrate safely
9. Brownfield traps

---

## 1. Set up the audit folder
Keep every artifact in one folder at the project root so iterations can be compared:
```
ux-audit/
  inventory.json, inventory.md     # scripts/inventory.py output
  captures/<route>@<width>.{json,png}  # scripts/walk.mjs or a manual walk
  scorecard.md, scorecard.json     # scripts/scorecard.py output
  flows.md                         # critical paths (section 5)
  component-map.md                 # layers + consolidation plan (sections 3, 6, 7)
  DESIGN.md                        # the locked contract (design-contract.md)
  report.md                        # the audit report (assets/report-template.md)
```
Ask before committing `ux-audit/`. Some teams want it in the repo; others want it gitignored.

## 2. Run the inventory, then verify it
```bash
python3 <skill>/scripts/inventory.py <project-root> --out ux-audit
python3 <skill>/scripts/inventory.py <project-root> --where Button   # blast radius for one component
```
The inventory is regex-based, so treat every row as a **lead**. Before you put a finding in the report,
confirm it:
- **Usages:** the script maps `<Name>` tags by name. Confirm with your editor's or LSP's find-references, or `grep -rn "<Name[ />]" src`. It misses dynamic usage: `components[type]`, `React.lazy(() => import(...))`, string registries (CMS block maps, MDX components), `cloneElement`, render props passing the component itself, and Storybook-only usage.
- **Unused:** never delete on the script's word. Grep the name, check barrel files (`index.ts` re-exports), lazy imports and the CMS/MDX registry first.
- **Duplicates:** two files defining `Button` may be a deliberate platform split (`Button.native.tsx`) or a package boundary in a monorepo. Check before calling it a duplicate.
- **Data views:** "missing loading?" means no loading-like word appeared in the file. The state may live in a parent, a Suspense boundary, or a route `loader`/`errorElement`. Follow the data up one level before reporting it.
- **Token adoption:** count design-system utility classes (`bg-primary`, `text-muted-foreground`) as tokens even though the script only counts `var(--x)`. Tailwind with a configured theme can be well-tokened with zero `var()` calls; read `tailwind.config` / `@theme` first and adjust the claim.

Also read, by hand, the things no regex finds well:
- the design-system entry point (`components/ui`, `packages/ui`, shadcn `components.json`, Storybook)
- theme and token sources (`tailwind.config.*`, `@theme` in CSS, `tokens.json`, CSS custom properties, MUI/Chakra theme objects)
- the router config (if routes are declared in code rather than files) and the main nav component

## 3. Classify into layers
Place every component into exactly one layer. Atomic-design names are fine, but these layers map better to
how code is actually reused:

| Layer | What it is | Examples | Rule |
|---|---|---|---|
| **0. Tokens** | named values | color roles, type scale, space scale, radii, shadows, motion, z-index, breakpoints | no component uses a raw value that a token covers |
| **1. Primitives** | one job, no domain knowledge | Button, Field, Input, Select, Checkbox, Card, Dialog, Sheet, Toast, Tooltip, Badge, Avatar, Icon, Skeleton, Stack/Inline layout | accessible, stateful (all states built in), themeable, no data fetching |
| **2. Patterns** | primitives composed for a UX job | SearchBox, FormStep/Wizard, DataTable↔CardList, EmptyState, ErrorState, ConfirmDialog, Pagination, FilterBar, SettingsRow | no domain words in the API; reused in ≥2 features |
| **3. Domain components** | patterns plus domain data | ProductCard, InvoiceRow, CheckoutSummary | thin: compose patterns, own no styling of their own |
| **4. Screens/routes** | layout plus domain components plus data loading | /checkout, /settings | own data loading and the four states; no bespoke primitives |

Where a component sits in the wrong layer, the finding is usually one of these: a domain component styling
its own buttons (should use a primitive), a screen defining a one-off modal (should use Dialog), or a
"primitive" that fetches data (should move up).

Write the result into `ux-audit/component-map.md`: one table per layer with name, file, fan-in, family, and
an action (keep / merge into X / extract / delete-after-verify).

## 4. Map where everything is used (blast radius)
For each primitive and pattern, record **fan-in** (how many files use it) from `inventory.json` →
`components[].fan_in` / `used_in_files`, verified as in section 2. Fan-in decides the order and the risk:
- **High fan-in (top 10%):** change its API last, behind a compatibility layer. Visual changes are global, so screenshot several consumers before and after.
- **Fan-in 1:** either a legitimately local component, or a copy-paste that should be a variant of a shared one.
- **Fan-in 0:** a candidate for deletion, after the section 2 checks.

## 5. Map the app flow
Components only matter in the journeys they serve. Build `ux-audit/flows.md`:
1. **Routes:** from `inventory.json → routes`, or the router config. Mark which are public, which are authenticated, and which are dynamic (and pick one real sample id for each).
2. **Navigation graph:** top nav, tab bar, sidebar, footer and in-page links. Note the order (Serial Position) and the count (Hick's).
3. **Critical paths:** the 3–5 journeys the product exists for (sign up → first value; browse → cart → pay; create → share). For each, list every screen, and on each screen the primary action, the decisions asked, the fields, and every state the user can hit (empty, loading, error, success, permission denied, offline).
4. **Count the cost of each path:** screens, taps or clicks, fields, decisions, waits. These counts are the baseline that later iterations must beat. Record them in the scorecard's manual metrics or in the report.

## 6. Find the consolidation candidates
Signals, strongest first:
1. **Same family, same job:** `inventory.json → families` with several members whose props and markup overlap (`ProductCard`, `ItemCard`, `DealCard`). Open them side by side and list what actually differs. Usually it's data shape, one slot, and accidental styling.
2. **Raw element bypass:** `raw_element_bypass` where a primitive exists, e.g. 11 raw `<input>`s next to a `TextInput`. Each bypass is a place where states, labels and a11y were probably re-done or skipped.
3. **Style drift:** files with high hex/arbitrary-value counts; runtime sprawl (`probe.system.fontSizes`, `radii`, `shadows`) above the scorecard thresholds.
4. **Behavioral duplicates:** two modals, two toast systems, two date pickers, two table implementations. Grep for library imports (`react-modal`, `@radix-ui/react-dialog`, `headlessui`, `sonner`, `react-hot-toast`, `react-toastify`) to find them.

For each candidate group, decide:
- **Merge:** one primitive or pattern with variants or slots; domain wrappers become thin compositions.
- **Keep separate:** the jobs genuinely differ (a `FeatureCard` on marketing pages vs a `ProductCard` in commerce may legitimately differ). Write down why, so the next audit doesn't re-litigate it.
- **Delete:** no usage after verification.

## 7. Write the consolidation plan
For each merge, write a short spec in `component-map.md`:
```
### Card family → Card primitive + ProductCard composition
Members: ProductCard (fan-in 1), ItemCard (1), DealCard (1)   Keep separate: FeatureCard (marketing; different job)
Differences found: image ratio, price slot position, CTA label, badge slot
Target API: <Card interactive?> <Card.Media ratio> <Card.Body> <Card.Footer>; ProductCard = Card + Price + AddToCart
States the primitive owns: hover/focus/pressed (if interactive), loading skeleton, disabled/out-of-stock
Laws: Similarity (same thing looks the same), Common Region (the card boundary means "one product"), Fitts (whole card clickable)
Migration: add Card → reimplement ProductCard on it → point ItemCard/DealCard at ProductCard with an adapter → delete them
Verification: screenshots of /, /deals at 390 and 1440 before/after; inventory shows the card family down from 4 to 2
```
component-architecture.md has the API conventions that make these merges reusable and interchangeable.

## 8. Migrate safely
- **Strangler, not big bang.** Build the new primitive beside the old ones. Move consumers in small batches, highest-traffic path last (or first behind a flag, if the team prefers). Delete the old component when its fan-in reaches 0.
- **Adapters keep call sites compiling.** `export const ItemCard = (p) => <ProductCard product={toProduct(p.item)} />` lets you switch implementation before touching consumers.
- **Deprecate loudly.** Add `/** @deprecated use Card */` (editors strike it through) and, if the project has lint, an `eslint no-restricted-imports` rule for the old paths. That stops new copies while you migrate.
- **Codemods for mechanical moves.** For dozens of call sites with a pure rename or prop mapping, a jscodeshift or ts-morph codemod beats hand edits. Run it in its own commit.
- **Visual verification per batch.** Re-run `walk.mjs` on the routes that consume the changed component and compare screenshots. If the project has visual regression (Chromatic, Playwright `toHaveScreenshot`, Percy), use it.
- **Behavior verification per batch.** Run the project's tests; and, for forms, actually submit with valid, invalid and pasted input.
- **One concern per commit:** tokens, then the primitive, then each consumer batch, then deletions. That makes rollback a revert.

## 9. Brownfield traps
- **Two styling systems at once** (CSS modules + Tailwind + styled-components): consolidate tokens first so both systems read the same values (CSS custom properties work in all of them), then migrate components.
- **A UI kit wrapped and then bypassed** (MUI/Chakra/shadcn plus hand-rolled copies): the fix is usually to extend the kit's theme or variants, not to add a third layer.
- **Global CSS overrides** (`.btn { … !important }`) silently restyle the new primitive. Search for selectors targeting element names or kit class names.
- **Server-rendered markup and hydration:** a component that changes markup by viewport in JS (`isMobile ? <A/> : <B/>`) flashes and shifts layout. Prefer CSS and container queries, and render both only when the structure must differ.
- **Feature flags and A/B variants** hide components from the scan and the walk. Ask what's flagged on in production.
- **Auth-gated routes:** the walk needs a session. Ask for a test account or a seeded local environment. Never use real credentials you weren't given for this.
