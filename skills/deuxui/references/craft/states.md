# States

The happy path is the smallest part of the work and the only part that gets built.
Everything here is a state a real user reaches, and each one is a designed surface
rather than a fallback.

## The seven

| State | What it owes the user | Rule |
|---|---|---|
| Empty | Why it is empty, and the one action that ends it | `UX-001`, `COMP-017` |
| Loading | An acknowledgement within 1s; an escalation by 10s | `STATE-001`, `NUM-014` |
| Error | What failed, whether their work survived, what to do | `STATE-001`, `UX-009` |
| Offline | That it is offline, and what still works | `STATE-006` |
| Permission denied | That it is a permission, not a bug, and who to ask | `STATE-001` |
| Conflict | That two edits collided, with both versions reachable | `STATE-004` |
| Maximum content | That it still reads with 400 items and a 90-character name | `CONTENT-007` |

Write them in the same edit as the component. The PostToolUse hook tells you which
are missing while the file is still open, which is the only time adding them is
cheap.

## Empty is the highest-leverage screen in the product

It is the first thing every new user sees and the last thing anyone designs. An
empty list with the word "No results" wastes the one moment when the user is
willing to be told what this screen is for.

Three kinds, and they need different copy:

- **First run.** Nothing exists yet. Say what will be here and give the action
  that creates the first one.
- **Filtered to nothing.** Things exist; this query matched none. Say so, show the
  filter, and offer to clear it. Telling a user "no projects" when they have 200
  and a typo in the search box is actively misleading.
- **Cleared deliberately.** They finished the queue. Say that — it is the one
  empty state that is good news.

`S-STATE-EMPTY` catches a `.map()` with no empty branch; `R-STATE-EMPTY` forces an
empty payload against the running app and checks that what appears offers a next
action.

## Loading, and the two clocks

Under 1 second: acknowledge. A spinner that appears instantly for a 200ms request
is worse than nothing — it flashes. Past 10 seconds: escalate, with progress if it
can be known and an explanation if it cannot.

Skeletons are better than spinners when the shape of the result is known, because
they prevent the layout shift the real content would cause. They are worse when the
shape is wrong, because the page visibly rearranges at the moment of arrival.
Skeletons must be hidden from assistive technology or a screen reader reads a page
of nothing (`S-PERF-SKELETON-ARIA`).

The in-flight guard is the part with money attached: a submit button that stays
enabled during the request charges the card twice. `S-STATE-DUPE`, `NUM-020`.

`R-STATE-SLOW` makes the request genuinely slow and asks what the interface says
while it waits — flight is defined by content arriving, not by `readyState`, so a
page that is "complete" while still fetching is measured as still waiting.

## Error, and the honesty of it

The rule that matters most: **say whether their work survived.** Users do not fear
errors; they fear losing what they typed. A message that says "Your draft is
saved" converts a disaster into an inconvenience.

Errors must be reachable, too. An error announced only in a toast that
auto-dismisses is an error the user missed (`S-COMP-TOAST-ONLY`), and a form error
that is not linked to its field is an error on a 40-field form nobody can find
(`S-FORM-ERROR-LINK`).

`R-STATE-ERROR` aborts the API and asserts a real error state appears — not an
immortal spinner, which is the most common actual behaviour.

## Optimistic updates owe a rollback

Showing the result before the server confirms it is good for a "like" and
dangerous for a payment or a delete. Without a rollback path, the user sees
success and the system has none. `S-STATE-OPTIMISTIC` flags the pattern on
destructive and financial actions; `STATE-005` is the rule.

Related: `S-STATE-PREMATURE` catches the success message that fires before the
promise resolves, and `S-STATE-RACE` the update that applies a stale response
because nothing cancelled the earlier request.

## Destructive actions

Confirmation, undo, or both — and the confirmation must name the scope
(`S-COMP-BULK-SCOPE`) and must not be autofocused on the destructive button
(`S-A11Y-AUTOFOCUS`), which turns a reflexive Enter into a deletion. Undo is
better than confirmation wherever it is technically possible, because it does not
tax the 99 correct actions to prevent the one mistake.

`M-DESTRUCTIVE-WALK` is the manual pass: actually delete something and try to get
it back.

## Adjudicated by

`S-STATE-EMPTY` · `S-STATE-ERROR` · `S-STATE-LOADING` · `S-STATE-DUPE` ·
`S-STATE-OPTIMISTIC` · `S-STATE-PREMATURE` · `S-STATE-RACE` · `S-STATE-CANCEL` ·
`S-COMP-TOAST-ONLY` · `S-FORM-ERROR-LINK` · `S-PERF-SKELETON-ARIA` ·
`S-COMP-BULK-SCOPE` · `S-A11Y-AUTOFOCUS` · `S-TRUST-DESTRUCT` ·
`R-STATE-EMPTY` · `R-STATE-ERROR` · `R-STATE-OFFLINE` · `R-STATE-SLOW` ·
`M-DESTRUCTIVE-WALK`
