# Component systems — rules per UI system

A product screen is several systems, each with its own rules. Name the system first, then apply only that
system's rules. Three moves recur everywhere: **match the surface to the stakes** (inline, toast, banner,
modal, page), **always leave a way forward** (retry, suggestion, next action, a way back), and **say the
specific thing that happened** instead of a generic success or error.

Provenance markers:
- unmarked: a stated rule from the source set
- **[unconfirmed]**: the rule came from on-screen captions without confirmed audio. Apply it, but say it's unconfirmed.
- **[conflict]**: the sources disagree. Write both sides into the audit and let the owner pick. Don't average them, and don't pick whichever is easier to build. The full list is in [Conflicts](#conflicts--write-both-sides).

Numbers printed on mock screens in the sources (recovery %, click shares, cognitive-load %, prices) are
**not** measurements. Never cite them.

## Contents
Search · Forms and wizards · Card entry · Errors · Notifications · Toasts · Settings · Hover, touch and
tooltips · Dark mode · Radius · Data tables (desktop, mobile) · Long lists · Login · Dashboards · Icons ·
Success · Buttons and cards (house rules) · Conflicts

---

## Search
- The placeholder says what's searchable, how, and the scope ("Search by name, SKU, or brand"). "Search" alone fails.
- On focus, show recent searches. One activation fills the field.
- Rank suggestions by use, not alphabet. Give each a category badge. Keep the list short; three good results beat ten.
- Keyboard: arrows move, Enter selects, Escape closes, and the focus ring stays visible.
- Zero results offer a way out: popular queries or a category jump. Never a blank dead end.
- Mobile: the search field opens full-screen with the keyboard up and `type="search"` plus `enterkeyhint="search"`; the recents list must be reachable above the keyboard.

## Forms and wizards
- Chunk long forms. Twelve fields in one wall is the failure; three fields read without effort. Split by **context** (personal, shipping, payment, review), not by an even count.
- Use one progress pattern (linear bar, numbered dots or step labels), not several stacked.
- Validate inside the step and block Next while the step is invalid. Inline failure beats rejection on the final screen. **[conflict: validation timing]**
- Save state on every step change, so Back and refresh keep the answers (Zeigarnik).
- Labels are persistent (above the field), never placeholder-only (Working Memory).
- Correct `type`, `inputmode` and `autocomplete` on every field (Postel). Inputs are ≥16px font on mobile so iOS doesn't zoom on focus.
- Mobile: one column; the primary action is sticky at the bottom on long steps; the keyboard must not cover the active field or the error.

## Card entry [unconfirmed]
- Group 16 digits in fours. The first digit names the brand (4 Visa, 5 Mastercard, 3 Amex).
- Keep the caret where it was while reformatting. Don't jump it to the end.
- Validate on blur, not on each keystroke; no premature "invalid" while typing. **[conflict: validation timing]**
- Strip pasted separators and regroup. Display the formatted groups; store the raw digits.
- `inputmode="numeric"` and `autocomplete="cc-number"`.

## Errors
1. Type the error first: validation, network, server or permission. Each gets a different pattern. No 500-style modal for a typo.
2. Every error has a way out: retry, refresh or contact. A dead end is the worst thing you can ship.
3. Severity picks the surface: inline when the user can fix it, toast when it's transient, modal only when nothing else works. Most apps overuse modals. **[conflict: modals]**
4. Human copy: "Lost connection, reconnecting in 5 seconds", not "An error occurred" or `0x80004005`.
5. Prevent: inline validation, and disable submit until the input is valid. (The source's "kills 80% of errors" is a spoken claim, not a measured number. Don't cite it.)

## Notifications [unconfirmed]
- Four volumes for news: **toast** (corner, auto-dismiss), **banner** (full width, stays until closed), **modal** (blocks, demands a choice), **badge** (waits until cleared).
- Mapping: a new message is a toast, a degraded server is a banner, a declined card is a modal, unread items are a badge.
- Three toasts may stack; three modals are a train wreck. Choose by severity, not by habit.

## Toasts
1. Position: desktop bottom-right; mobile top. Never center, because center blocks the work.
2. Timing: info 4s, warnings 7s, errors stay until acknowledged. One timer for every toast is a bug. **[conflict: toast time]**
3. Stack: at most 3 visible; new ones push older ones. (Stated motion: a spring, damping 20, stiffness 180.)
4. Always dismissible: close button, swipe on mobile, pause on hover. If it can't be escaped, it's a modal.
5. Status is an icon plus a left-border color, never a background tint alone (color is not the only signal).
- Use `role="status"` (polite) for info and `role="alert"` for errors.

## Settings
- Low stakes are instant toggles: flip, done. Identity fields (email, name, password) get an explicit save bar and cancel. Match the model to the blast radius.
- Forty settings in one list is a phone book. Group by task; hide advanced behind one click.
- Search finds a setting three levels deep, highlights the match and shows the path.
- Every changed setting shows a marker and a one-step reset.
- Danger zone at the bottom with a red border. Delete requires typing the name; the button stays disabled until it matches.

## Hover, touch and tooltips
- Touch has no hover; the first tap is spent as a fake hover. Guard hover styles with `@media (hover: hover)`, never with device sniffing (`if (isMobile)`). Pair with `@media (pointer: coarse)` to grow targets.
- Hover may reveal extras. The **primary action never lives only behind hover**. On touch, hidden actions go in the card, on a swipe, or in a bottom sheet. **[conflict: row actions]**
- Hit target: 44px around a 20px icon. Pad the hit area and keep the icon small. **[conflict: 44 vs 48]**
- Tooltips: wait 300ms (instant tooltips are noise); an arrow points at the trigger; flip at viewport edges (a clipped tooltip is worse than none); dismiss on mouse leave, Escape, blur and outside tap; max 300px wide and one sentence. A tooltip is a hint, not documentation, and it's never the only home for essential information on touch.

## Dark mode
- Not pure black with pure white (`#000` and `#fff` read as a terminal). Start near black so stacked surfaces can get lighter.
- Shadows die on dark: elevation is **lightness**, so higher surfaces are lighter. **[conflict: shadows]**
- Text is three tiers of one white variable: 87%, 60% and 38% alpha.
- Accents keep the hue but get lighter and less saturated, so they don't bleed.
- Hairlines are 1px white at about 8% alpha, not a fixed gray, so they adapt as surfaces lighten.
- Photos are dimmed to about 90% brightness. Illustrations get a redrawn dark variant, not a filter.
- Hex values in the sources are examples, not a palette to copy.

## Radius
- Concentric corners: inner radius = outer radius − padding (12 outer, 8 padding, 4 inner).
- Radius follows size: small elements get small radii. **[conflict: radius scale]**
- A full pill is a shape for one line only (chips, avatars, toggles). Multi-line containers get a real number.
- A corner touching a screen edge is 0. A bottom sheet is `16px 16px 0 0`.
- A selection or focus ring = inner radius + gap (8 inside, 2px gap, 10 outside), or the corners pinch.
- Edge-to-edge images in a rounded card are clipped by the card (`overflow: hidden`). Inset images subtract the padding.

## Data tables (desktop)
- Numbers right-aligned with tabular figures (`font-variant-numeric: tabular-nums`); text left. Centered amounts are a failure.
- One hairline between rows plus a hover highlight. Zebra stripes only on very wide rows.
- Row height is a choice: compact 40, default 48, comfortable 56, with one density toggle.
- Pin the identity column and the header.
- An empty cell is a dash, so missing isn't confused with zero or loading.
- Truncate long text with a tooltip. Never truncate numbers, and never wrap cells.
- Row actions appear on hover **or focus**; touch gets a kebab menu. 50 rows should not mean 50 pencils. **[conflict: row actions]**
- Show the sort arrow only on the active column.

## Data tables (mobile)
- Don't shrink the desktop grid. Restructure it.
- Rank columns by use (identity, value, state), not "the leftmost three". The ID goes first.
- Stack two lines: name left, amount right; status and date underneath.
- One amount slot, top-right of every card, with tabular figures, so a list of cards still compares.
- Label ambiguous values ("Due Mar 4", not "Mar 4"). An amount needs no label.
- Sort becomes a control; hiding a column doesn't delete its sort.
- Tap expands two more fields in place, or opens the full record in a bottom sheet. Never a new page for a glance.
- The breakpoint belongs to the table, not the viewport: `@container (max-width: 700px)` → cards. This also covers a narrow desktop side panel.

## Long lists [unconfirmed]
- Paginate by a stable cursor (`id < last_id`), not by offset, so inserts don't skip or duplicate rows.
- Numbered pages are for jumping, load-more for user control, infinite scroll for feeds. They are different jobs.
- Keep first and last reachable, and show about 7 cells: first, gap, current, gap, last. Don't render 500 page links.
- Back from a detail page restores scroll to the row, not to the top.
- Put the page or cursor in the URL so refresh and sharing keep the place.

## Login
- A solid surface, or a split screen with the product on one side. Not a card floating on a gradient blob.
- One primary social button (the one users actually pick); the others are text links.
- Product name plus one line of value, not "Welcome back".
- A wrong password says "email or password is incorrect", never which one. Lock after repeated failures; offer to resend an unverified email.
- Logo about 24px at the top left, with the name beside it. The form is the hero.
- Use `autocomplete="username"` / `current-password`, and allow paste and password managers (Postel).

## Dashboards [unconfirmed]
- One flat accent, not decorative gradients on the header, buttons and chart fills.
- The number is the hero, not a row of colored icon tiles.
- One primary metric and three secondary ones, not four equal cards.
- Shadows only on what floats (menus, popovers, dialogs). **[conflict: shadows]**
- Copy with a specific shape (a date range, a split such as subscriptions vs one-time), not a repeated "+12.5%" or "Welcome back".
- Mobile: the primary metric first, full width; secondaries in a 2-up grid or horizontal scroll with snap, and charts simplified, not shrunk.

## Icons
- One stroke width for the whole product: 1.5 or 2, never both.
- A 16px glyph sits in a 20px box. Directional icons (arrows, play) shift 1px toward their point.
- Sizes lock to type: 16 beside 14px text, 20 beside 16px, 24 beside headings. Never a one-off 18.
- Icon color is the text color: secondary at rest, full on hover, accent only when active. Ten accent icons are ten shouts.
- Outline by default; filled means selected (outline star vs filled star).
- Icon-only buttons need an accessible name (`aria-label`); for anything not universally understood, show the label too.

## Success
1. Say what happened: the object, who it went to, the date ("Invoice sent to Northwind Labs, due Oct 12"). "Success" alone is a maybe.
2. Offer a next action and a way back ("View invoice", "Send another"). A checkmark with no button is a dead end.
3. Dismissal follows stakes: a settings save is a ~4s toast; a payment gets a page that stays, with a receipt and an email.
4. Leave one open loop (track it, share it, invite the team).
5. Celebration scales with rarity: confetti for the first invoice paid, not for every save.

## Buttons and cards (house rules for consolidation)
These are synthesis for the brownfield consolidation work, not quotes from the sources.
- **Button:** one component, variants `primary | secondary | ghost | danger` (and `link` if needed), sizes `sm | md | lg`, where md meets a 44px hit area on coarse pointers. Built-in `loading` (keeps its width, shows a spinner, disables re-submit), `disabled` with a reason available, an icon slot (leading or trailing), and `asChild`/`as` so a link can look like a button without nesting. **One primary per view** is a composition rule enforced in review, not in the component.
- **Card:** one container primitive (surface, radius, padding, optional interactive state) plus composed parts (`Card.Media`, `Card.Header`, `Card.Body`, `Card.Footer`/`Actions`). Domain cards (`ProductCard`, `DealCard`) are thin compositions over the primitive, not separate styling. A whole-card link uses one real `<a>` (stretched link), with secondary actions layered above it. Number slots use tabular figures. Media takes an `alt` through the data shape (`imageAlt`), defaults to the product name, and is never hard-coded to `alt=""` in the primitive. Decorative-only is a call-site decision, not a component default (WCAG 1.1.1).
- **Field:** one `Field` wrapper owns label, hint, error, required marker and ids (`aria-describedby`, `aria-invalid`). Inputs inside are swappable (text, select, combobox, date). That's what makes data-entry components interchangeable.

---

## Conflicts — write both sides
| # | Topic | Side A | Side B |
|---|---|---|---|
| 1 | Validation timing | Card entry: validate on blur, not keystroke [unconfirmed] | Errors: live inline validation, submit disabled until valid · Wizard: validate in-step, block Next |
| 2 | Radius scale | Spoken: 4 / 8 / 16 | On screen: 4 / 8 / 12 / 16 / full (9999) |
| 3 | Shadows | Light dashboards: shadow only on what floats [unconfirmed] | Dark mode: no shadows; elevation by lightness. Different contexts, so don't merge them into one ban |
| 4 | Modals | Notifications: a declined card is a modal [unconfirmed] | Errors: modal only when nothing else works |
| 5 | Row actions | Tables: reveal on hover or focus, kebab on touch | Touch rule: the primary never lives only on hover. State both; keep the kebab |
| 6 | Toast duration | Info 4s / warning 7s / error until acknowledged (toast rules) | Settings-save success ~4s; notifications show 4s on screen. Only the toast rules state 7s and "until acknowledged" |
| 7 | Hit target | 44px (spoken; Apple HIG 44pt) | Material 48dp. Keep both citations. WCAG 2.5.8's 24px is the legal floor, not the goal |

When a project already has a written standard (its own DESIGN.md or design system docs), that wins over both
sides. Cite it.
