# clarify — make the screen say what it is

A clarity pass targets comprehension, not appearance. The test is whether a
stranger can say, in one sentence, what this screen is for and what to do next.

Derived from impeccable's `clarify` (Apache-2.0) — see NOTICE.md.

## Read it cold

Open the screen with no context and answer, in this order:

1. **Where am I?** Does the page say so without the URL?
2. **What is this?** Can the primary object be named from the screen?
3. **What do I do?** Is the primary action the easiest thing to find (UX-008)?
4. **What happened?** After an action, does the screen say what changed
   (STATE-002, SC 4.1.3)?
5. **What went wrong, and what now?** An error that names a failure without a
   recovery is half an error message (UX-009, CONTENT-002).

Each "no" is a clarity defect with a rule behind it. Fix the copy before
touching the layout — copy is the cheapest intervention and usually the right
one.

## Copy is interface

- Label the action with its outcome. "Save changes", not "Submit".
- The accessible name must contain the visible label (NUM-011 / SC 2.5.3), or
  voice control cannot operate the control the user can see.
- No internal vocabulary. If the term only exists in your database, it is not a
  label.
- Say what will happen before it happens, for anything irreversible or external
  (TRUST-001, UX-005).
- Empty states orient before they charm: what goes here, and how to put the first
  one in (UX-001).

`M-CONTENT-REVIEW` is the question: read every string on one flow aloud,
including error and empty states, and name the ones that say what went wrong
without saying what to do.

## Structure carries meaning

Headings in order, no skipped levels (A11Y-011). A list marked up as a list. A
table with headers. Landmarks that match the regions a sighted reader sees. These
are clarity for the reader using a screen reader, and they are the same clarity
for everyone else — a skipped heading level is a hierarchy nobody agreed to.

## Verify

| Detector | What it settles |
|---|---|
| `S-CONTENT-ERRORTEXT` | No "Something went wrong" with no next step. |
| `S-SLOP-COPY` | No placeholder copy shipped. |
| `S-A11Y-HEADING` | Heading levels are in order. |
| `S-A11Y-ICONBTN`, `S-A11Y-LABEL` | Every control has a name. |
| `S-COMP-VAGUE-LABEL` | The label says what the action does. |
| `S-STATE-EMPTY` | The empty state offers a next action. |
| `M-CONTENT-REVIEW`, `M-SCREENREADER` | The two things a scan cannot read. |

Hand off to [polish.md](polish.md).
