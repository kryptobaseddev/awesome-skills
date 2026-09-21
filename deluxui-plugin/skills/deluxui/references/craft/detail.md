# Detail

The last five per cent. Everything here is invisible until it is wrong, and
collectively it is most of what separates an interface that feels made from one
that feels assembled.

Do this after the other eleven domains are right. Polishing a screen whose
hierarchy is wrong is time spent making the wrong thing smoother.

## Focus, which is the one detail with a rule behind it

A focus ring is not decoration. It is the only way a keyboard user knows where
they are, and removing it is the single most damaging one-line change available in
CSS. `outline: none` with no replacement is `S-FOCUS-OUTLINE`, and in Tailwind v4
`outline-none` sets `outline-style: none` — the forgiving old behaviour is now
`outline-hidden`.

The ring must also be *visible*: 2px minimum, 3:1 against what is behind it
(`NUM-011`), and not obscured by a sticky header when the page scrolls the focused
element under it — `R-STICKY-OBSTRUCTION` measures that, `R-FOCUS-WALK` walks the
whole page and reports order, traps and invisible rings.

Focus order follows the visual order. A positive `tabIndex` breaks that by pulling
elements to the front of the entire document (`S-A11Y-TABINDEX`), and a component
that moves focus on mount steals it from whatever the user was doing
(`S-NAV-FOCUS-STEAL`).

## Optical corrections

- **Circular next to square.** A round avatar beside square text needs slightly
  more inset to look level.
- **Cap-height centring.** A button's label centres on its cap height, not its
  line box; all-caps labels sit visibly low unless nudged.
- **Nested radii.** An inner element inside a rounded container wants
  `outer − padding`, not the same value, or the curves run parallel and look
  wrong. `S-CRAFT-CARD-RADIUS` catches the flat-16-everywhere case.
- **Icon-to-text baseline.** Icons align to the text's optical centre, not its
  baseline.

## Numbers and tables

`font-variant-numeric: tabular-nums` on any column of figures. One declaration,
and a ragged column becomes a column. Align on the decimal, not the glyph box.

## Text details

`text-wrap: balance` on headings stops a two-word orphan appearing at one width
and not another; `text-wrap: pretty` does the equivalent for prose.
`S-CRAFT-BALANCE` flags a file full of headings with neither.

Hanging punctuation on pull quotes, real apostrophes and quotes rather than primes,
a non-breaking space before a unit so "4 GB" never breaks across lines, and an
ellipsis character rather than three periods.

## Interaction details

- **Hit areas** are bigger than their visuals: 24px minimum on the web
  (`NUM-004`), 44pt on iOS, 48dp on Android. A 16px icon needs padding, not a
  bigger icon. `S-TARGET-SIZE`, `R-TARGET`, `R-TARGET-COARSE`.
- **Spacing between targets** is part of the same criterion — two adjacent 24px
  targets with no gap fail SC 2.5.8 even though each is large enough.
- **Hover does not exist** on touch or keyboard. Anything revealed only on hover
  is invisible to a large share of users; mirror it on `focus-within`.
  `S-HOVER-ONLY`.
- **Disabled controls** must say why. A greyed button with no explanation is a
  dead end, and a disabled control with muted text usually fails contrast as well.
  `S-FORM-DISABLED`, `S-COMP-DISABLED-MUTE`.
- **Cursors** tell the truth: `pointer` for things that act, default for text,
  `not-allowed` only where an action is genuinely blocked. A `pointer` on a
  non-interactive card is a promise the product does not keep
  (`S-UX-FAKE-INTERACTIVE`).

## Scroll and selection

Scroll containers need a visible affordance that they scroll — a cut-off row, a
shadow at the edge — or people do not scroll them. Selection colour should be a
deliberate value from the palette rather than the browser's blue over a warm
ground. `::selection` is one declaration.

Sticky headers that cover the focused element, anchor targets landing under a
fixed bar, and modals that let the page behind them scroll are the three scroll
bugs that appear in almost every implementation.

## Adjudicated by

`S-FOCUS-OUTLINE` · `S-A11Y-TABINDEX` · `S-NAV-FOCUS-STEAL` · `S-TARGET-SIZE` ·
`S-HOVER-ONLY` · `S-FORM-DISABLED` · `S-COMP-DISABLED-MUTE` ·
`S-UX-FAKE-INTERACTIVE` · `S-CRAFT-CARD-RADIUS` · `S-CRAFT-BALANCE` ·
`R-FOCUS-WALK` · `R-STICKY-OBSTRUCTION` · `R-TARGET` · `R-TARGET-COARSE` ·
`M-KEYBOARD-TASK` · `M-TOUCH-DEVICE`
