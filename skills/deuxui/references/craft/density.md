# Density

Density is the domain where consumer-product instincts actively harm the user. A
generous, airy layout is correct for a landing page and wrong for a screen someone
works in for six hours a day, where every row of padding is a row of data they now
have to scroll for.

## Ask what the visitor came to do

`operate` mode — the person has a job, does it repeatedly, and will be back
tomorrow — inverts most defaults: smaller type (14px is defensible here where it
is not elsewhere), tighter rows, more columns visible at once, keyboard paths for
everything, and no animation on anything they do more than twice a day.

`read` and `persuade` want the opposite. Applying an operator's density to a
marketing page makes it look cheap; applying a marketing page's density to an
operator's tool makes it unusable. See
[../design/visitor-modes.md](../design/visitor-modes.md).

`M-JUDGE-DENSITY` is the manual check, and it stays NOT_RUN until somebody answers
it, because the right density is a fact about the task and no scan can see the
task.

## Tables

A table is the densest thing in most products and the most commonly broken.

- **Headers are structural, not decorative.** Without `<th scope>` a screen-reader
  user navigating by column gets orphan values. `S-COMP-TABLE-SEMANTICS`.
- **Numbers align right and use tabular figures.** Proportional digits make a
  column of numbers ragged; `font-variant-numeric: tabular-nums` fixes it in one
  line and almost nobody does it.
- **Units belong in the header**, not repeated in every cell — unless they vary,
  in which case they belong in every cell and the header says so.
- **Zero is not missing.** A blank cell where the value is zero, and a blank cell
  where the value was never collected, are different facts. `S-COMP-ZERO-VS-MISSING`.
- **Narrow viewports need a decision, not a horizontal scrollbar by accident.**
  Either a labelled scroll region or a card layout that keeps every label, unit
  and row action. `S-RESP-TABLE`, `LAY-006`.
- **Truncation must not be the only access to a value.** An ellipsis with no
  tooltip, no wrap and no detail view is data the product has and the user cannot
  read. `S-RESP-TRUNCATE`.

## Long lists

Past a few hundred rows, rendering everything is a performance problem; past a few
thousand it is a broken page. But virtualisation breaks `Ctrl+F`, breaks anchor
links into the list, and breaks screen-reader navigation unless the row count is
announced. `S-PERF-LONG-LIST` flags the unbounded render; the fix has to preserve
the ability to find something.

Pagination has its own trap: a control that says `1 2 3 …` with no total and no
way to jump is a maze. `S-COMP-PAGINATION`.

## Bulk actions

Density and bulk selection arrive together, and bulk actions are where a dense
screen becomes dangerous. "Delete" on 2,400 selected rows must say 2,400, must say
what happens to them, and must be undoable or confirmed — `S-COMP-BULK-SCOPE`
checks that the action names its scope, and `S-TRUST-DESTRUCT` that a destructive
action has a recovery path at all.

The specific failure: a select-all checkbox that selects the *page* while the
button acts on the *query*. Both behaviours are defensible; having one control
mean both is not.

## Compact does not mean cramped

Reducing padding is not the only lever and it is the first one exhausted. Before
taking space away: remove columns nobody sorts by, move secondary actions into a
row menu, replace a two-line cell with one line plus a detail view, and drop the
decorative avatar. A screen that is dense *and* legible got there by removing
things, not by shrinking them.

`S-TYPE-CRAMPED` is the floor — small type with tight leading is where compact
becomes unreadable, and it is a threshold rather than a matter of taste.

## Adjudicated by

`S-COMP-TABLE-SEMANTICS` · `S-COMP-ZERO-VS-MISSING` · `S-COMP-PAGINATION` ·
`S-COMP-BULK-SCOPE` · `S-RESP-TABLE` · `S-RESP-TRUNCATE` · `S-PERF-LONG-LIST` ·
`S-TYPE-CRAMPED` · `S-TRUST-DESTRUCT` · `M-JUDGE-DENSITY` · `M-JUDGE-EXPERT-PATH`
