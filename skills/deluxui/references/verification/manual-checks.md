# What no machine can check

Automated testing finds a minority of accessibility problems and almost none of the
usability ones. A11Y-014 and GOV-009 are explicit about this: a scan is not
conformance, and a changed-component audit does not make an application conformant.

These checks stay **NOT_RUN** until a person does them and records the result. There
is no way to earn a PASS here by reasoning about it.

## Recording a result

`.deluxui/reports/manual.yaml`:

```yaml
attestations:
  M-KEYBOARD-TASK:
    status: PASS          # PASS | FAIL | NOT_RUN
    evidence: "Completed checkout keyboard-only, Firefox 141 / macOS, 2026-09-19.
               Focus visible throughout. One issue: the coupon field is reachable
               but its error is announced only visually -- filed as UI-441."
    who: "a designer on the team"
    date: "2026-09-19"
  M-SCREENREADER:
    status: NOT_RUN
    evidence: "No screen-reader pass yet."
```

`ux_report.py --merge` folds these in. Writing PASS without actually doing it is the
one failure mode this whole skill exists to prevent, and nothing downstream can detect
it — which is precisely why it matters that you do not.

## The checks

**`M-KEYBOARD-TASK`** — complete the primary task using only the keyboard. Tab,
Shift-Tab, Enter, Space, Escape, arrows. You are watching for: focus you cannot see,
focus that vanishes into a closed menu, a modal you cannot leave, an action reachable
only by pointer, and focus landing somewhere meaningless after a route change.

**`M-SCREENREADER`** — one pass with a real screen reader (VoiceOver, NVDA, TalkBack).
Not the accessibility tree, not a linter. Listen for: controls announced as "button"
with no name, headings that do not describe their section, form errors never announced,
status changes that pass silently, and live regions that will not stop talking.

**`M-TOUCH-DEVICE`** — the app on an actual phone. Reachability one-handed, targets
big enough for a thumb, the keyboard not covering the field being typed into, no
hover-only affordances, safe-area insets respected, and it still working in landscape.

**`M-CONTENT-REVIEW`** — read every string aloud. Does it use the user's words or the
database's? Does each error say what failed and what to do? Does any button lie about
what it commits? Is anything consequential disclosed only after the commitment?

**`M-DESTRUCTIVE-WALK`** — actually perform each irreversible action in a safe
environment. Delete the thing. Make the payment. Then: was the consequence clear
beforehand, is there an undo, does a double-click commit twice, and what does the
interface claim if the response is lost?

**`M-FIELD-PERF`** — real users on real devices and networks. NUM-012 is a 75th
percentile field metric; RUM data is the only thing that can satisfy it.

## The cheapest useful version

If you have ten minutes, not a day: do the keyboard pass on the primary task and read
the error messages aloud. Those two find more than any scan, and both are things you
can do right now without installing anything.
