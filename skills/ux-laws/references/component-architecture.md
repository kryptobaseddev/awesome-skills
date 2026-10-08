# Component architecture — reusable, interchangeable, built to scale

Consolidation only pays off if the new components can be dropped into any screen, swapped for each other
where their jobs match, and extended without being copied. That's an API problem more than a styling
problem. This file is framework-neutral; examples are React/TSX, with Vue and Svelte equivalents noted.

## Contents
1. Token layers
2. The shared prop contract (interchangeability)
3. Variants, sizes and slots
4. Composition over configuration
5. States live in the component
6. The four-state data pattern
7. Responsive strategy
8. Utilities worth centralizing
9. Folder layout and ownership
10. Documentation and enforcement

---

## 1. Token layers
```
reference tokens    --blue-600: #2563eb; --space-4: 16px; --radius-md: 8px
semantic tokens     --color-action: var(--blue-600); --color-text-muted: …; --surface-raised: …
component tokens    --button-height-md: 44px; --card-padding: var(--space-4)   (only where a component needs its own knob)
```
- Components consume **semantic** tokens, never reference ones. That's what makes themes (dark mode, brand, density) a token swap instead of a rewrite.
- Name color tokens by **role** (`action`, `danger`, `surface`, `text-muted`, `border-subtle`), not by hue.
- The spacing scale is a short list (e.g. 4, 8, 12, 16, 24, 32, 48, 64). The type scale is a short list with paired line heights. The radius scale follows size (component-systems.md → Radius). Motion tokens: durations and easings, plus a `prefers-reduced-motion` override.
- Breakpoints and container widths are tokens too, so the layout and the docs agree.
- Tailwind v4: put tokens in `@theme` and use the generated utilities. v3: `theme.extend` in the config. CSS-in-JS: a typed theme object that emits CSS custom properties.

## 2. The shared prop contract (interchangeability)
Components that do the same kind of job take the same props with the same meaning, so a `TextField` can be
swapped for a `Select` or `Combobox` in a form without touching the form logic:

| Concern | Prop (same name everywhere) |
|---|---|
| value | `value` / `defaultValue` (controlled and uncontrolled), `onChange(value)`; native event via `onChangeEvent` if needed |
| validity | `invalid` (boolean) + `error` (message), wired to `aria-invalid` and `aria-describedby` |
| guidance | `label` (required for fields), `hint`, `required` |
| availability | `disabled` (truly inert), `readOnly`, `loading` |
| size and look | `size: 'sm' \| 'md' \| 'lg'`, `variant` (from a closed list) |
| identity | `id`, `name`, pass-through of other native attributes (`...rest`) |
| refs | forward the ref to the native element (`forwardRef`, or the `ref` prop in React 19) |
| styling escape | `className` merged last (one `cn()` helper), never replaced |

The same applies to overlays (`open`, `onOpenChange`, `trigger`), collections (`items`, `getKey`,
`renderItem`, `emptyState`), and actions (`onAction`, `loading`, `disabled`). Write the contract into
DESIGN.md so new components follow it.

## 3. Variants, sizes and slots
- Variants are a **closed set** expressed in one place (`cva`, `tailwind-variants`, or a variants map). Adding a variant means adding a design-system decision, not a one-off class.
- Sizes map to tokens. `md` is the default and meets 44px hit areas on coarse pointers (padding, or an `::after` hit-area extension, keeps the visual size small).
- Slots for content that varies: `leadingIcon`, `trailingIcon`, `media`, `actions`, `footer`. A slot beats a boolean (`showIcon`) and beats a new component.
- Polymorphism (`asChild` à la Radix Slot, or `as`) lets a Link look like a Button without nesting interactive elements.
- Vue: props plus named slots, `defineModel` for `value`/`onChange`. Svelte 5: `$props()`, snippets for slots, `bind:value`.

## 4. Composition over configuration
When a component grows past ~10 props or gains `if (variant === 'deal')` branches, split it into
**compound parts**:
```tsx
<Card interactive href={url}>
  <Card.Media ratio="4/3"><img … /></Card.Media>
  <Card.Body><Card.Title>{name}</Card.Title><Price value={price} /></Card.Body>
  <Card.Footer><AddToCart id={id} /></Card.Footer>
</Card>
```
Domain components (`ProductCard`) become a few lines composing the parts. This is how three near-duplicate
cards become one primitive plus thin compositions (brownfield-decomposition.md → section 7).

## 5. States live in the component
Every interactive primitive implements, once, all its states: default, hover (inside `@media (hover: hover)`),
focus-visible, active/pressed, disabled, loading, invalid, selected or checked, and read-only. Expose state as
`data-state="open|closed"` / `data-disabled` / `aria-*` attributes, so styling and tests key off the same
truth. Tesler's Law in practice: the component absorbs the complexity so the 40 call sites don't each
half-implement it.

## 6. The four-state data pattern
Give every data view the same shape, so no screen can forget a state (Doherty, Postel's, Peak-End):
```tsx
<AsyncView
  query={productsQuery}                    // or {status, data, error}
  loading={<ProductGrid.Skeleton count={8} />}   // matches the final layout: no CLS
  empty={<EmptyState title="No products match these filters" action={<Button onClick={clear}>Clear filters</Button>} />}
  error={(e, retry) => <ErrorState kind={classify(e)} onRetry={retry} />}   // validation | network | server | permission
>
  {(items) => <ProductGrid items={items} />}
</AsyncView>
```
- `isEmpty` defaults to `Array.isArray(d) && d.length === 0` and is overridable.
- `ErrorState` picks copy and surface by `kind` (component-systems.md → Errors).
- Success after a mutation goes through one `notify()` / toast API with severity-based timing.

## 7. Responsive strategy
- **Mobile-first CSS:** base styles are the phone layout; `min-width` media queries add. Never `max-width` overrides stacked three deep.
- **Container queries for components** (`@container (min-width: 700px)`): a table becomes cards in a narrow panel too. **Media queries for page layout.**
- **Fluid type and space** with `clamp()` tokens, so there are fewer breakpoints.
- No JS viewport branching for layout (`isMobile ? A : B`) unless the structure truly differs, and then render server-safe (CSS-hidden twin) to avoid hydration flashes.
- Pointer features through `@media (hover: hover)` / `(pointer: coarse)`, never user-agent sniffing.

## 8. Utilities worth centralizing
One home each (`lib/` or `packages/ui/lib`), so formatting and behavior can't drift:
- `cn()`: class merge (clsx + tailwind-merge or equivalent).
- Formatting with `Intl`: `formatMoney`, `formatDate`, `formatRelative`, `formatNumber`. Use tabular figures wherever numbers align.
- Input normalizers (Postel's): `normalizePhone`, `normalizeCardNumber` (strip separators, keep the caret), trimming, case-folding emails.
- `classifyError(e)` → `validation | network | server | permission`, feeding ErrorState and copy.
- `notify({ severity, title, action })`, the single toast entry point, which owns position, stacking (max 3) and timing.
- `useDisclosure` / `useControllableState`, so every overlay and field behaves the same.
- Focus helpers: trap, restore, `focus-visible` styles.

## 9. Folder layout and ownership
```
src/
  design/tokens.css (or @theme)      # layer 0
  components/ui/                     # layer 1 primitives (+ stories/tests next to them)
  components/patterns/               # layer 2
  features/<domain>/components/      # layer 3, domain compositions
  app|pages|routes/                  # layer 4
  lib/                               # utilities above
```
In monorepos, layers 0–2 live in `packages/ui` with their own version. Feature code may import downward
only (features → patterns → primitives → tokens). Enforce it with lint (`no-restricted-imports`, or the
`eslint-plugin-boundaries` rule set) if the team agrees.

## 10. Documentation and enforcement
- Each primitive has a story or example page showing **every state and size**, at 390 and 1440.
- DESIGN.md (design-contract.md) records tokens, the prop contract, and the "one primary per view" kind of composition rules.
- Lint the drift: ban raw hex in components (stylelint `color-no-hex`, or a custom rule), ban imports of deprecated components, and flag Tailwind arbitrary values outside an allowlist.
- Re-run inventory.py in CI and fail on new raw-element bypasses or new members of an already-consolidated family (metrics.md → CI).
