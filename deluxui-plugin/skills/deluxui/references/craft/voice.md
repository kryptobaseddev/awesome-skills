# Voice

Every string in the product is a design decision, and most of them are made by
whoever typed fastest.

## Say what happened and what to do next

"Something went wrong" is the canonical failure. It names nothing, offers nothing,
and is indistinguishable from the product having no idea what state it is in —
which, when it appears, it usually does not. `S-CONTENT-ERRORTEXT` flags it, along
with `Error: undefined` and its relatives.

An error message has three jobs:

1. Name what failed, in the user's terms. *"We could not save your changes."*
2. Say whether their work survived. *"Your draft is still here."* This is the part
   that is almost always missing and the part people actually need.
3. Give the next action, as a control if possible. *[Try again]*

A message that does all three is rarely longer than two lines.

## Buttons say what they do

"Submit" describes the mechanism. "Book the viewing" describes the outcome, and it
is the label that lets someone confirm they are about to do the right thing
without reading the dialog again. This matters most on destructive confirmations,
where "OK" and "Delete 2,400 rows" are the difference between a confirmation and a
formality. `S-COMP-VAGUE-LABEL` catches the generic family.

## The voice of the product is one voice

Playful empty states next to formal error messages next to a breezy onboarding is
three products. The tell is usually exclamation marks and jokes in exactly the
places where somebody has just lost work — humour at the moment of failure reads as
the product not taking the user's problem seriously.

`S-CRAFT-VOICE` looks at the marketing register leaking into the interface:
"Unlock", "Supercharge", "Effortlessly", "Seamlessly". `S-SLOP-EYEBROW` catches
the little uppercase label above every heading, which is a template rather than a
voice.

## Emoji are not an interface

An emoji in a heading or a button renders differently on every platform, is read
aloud by screen readers in full ("grinning face with smiling eyes"), and cannot be
styled. `S-SLOP-EMOJI`. In user-generated content they are content; in the
product's own chrome they are a decision to look informal that nobody made
deliberately.

## Numbers, dates and money belong to a locale

`1,234.56` and `1.234,56` are the same number. `03/04` is two different days.
Rendering either with string concatenation is a bug that only appears for users you
are not testing with. `Intl.NumberFormat` and `Intl.DateTimeFormat` exist;
`S-CONTENT-FORMAT` flags raw rendering, and `S-CONTENT-I18N` flags hardcoded
strings in a product that has an i18n setup.

Relative time — "3 days ago" — is friendly and lossy. Where the exact moment
matters (an audit log, a deadline, a transaction), show both.

And if the product ships to an RTL locale, the layout mirrors: `S-CONTENT-RTL`
looks for the physical properties (`margin-left`, `text-align: left`) that do not.

## Placeholder is not a label

A placeholder disappears the moment someone types, so a form filled in from a
placeholder cannot be checked. It also fails contrast almost everywhere by
default. `S-A11Y-PLACEHOLDER` and `S-A11Y-LABEL`. Use a real label, and keep the
placeholder for an example of the format.

## What a checker cannot decide

Whether the copy is *right* — whether it uses the words this audience uses, whether
it is honest about what the product does — is `M-CONTENT-REVIEW`, and it stays
NOT_RUN until a person records an answer. Tone is not detectable; lorem is.

## Adjudicated by

`S-CONTENT-ERRORTEXT` · `S-CONTENT-FORMAT` · `S-CONTENT-I18N` · `S-CONTENT-RTL` ·
`S-COMP-VAGUE-LABEL` · `S-CRAFT-VOICE` · `S-SLOP-EMOJI` · `S-SLOP-COPY` ·
`S-SLOP-EYEBROW` · `S-A11Y-PLACEHOLDER` · `S-A11Y-LABEL` · `M-CONTENT-REVIEW`
