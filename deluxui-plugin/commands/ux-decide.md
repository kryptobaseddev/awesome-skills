---
description: Serve a design decision as a page on localhost and record the answer as evidence — who chose, when, why, and against exactly what.
argument-hint: "[path to a comps.yaml]"
---

Invoke the `deluxui` skill and read `references/ops/decide.md`.

Asking "which of these three?" in a chat transcript gets an answer that lives
nowhere. Six weeks later nobody can say which comp was approved or by whom, so the
approval gates nothing — and in practice it does not.

```bash
python3 scripts/ux_question.py ask ${1:-.deluxui/comps/*.comps.yaml}
```

Hand the URL to the person and **wait**. Do not summarise the options in chat and
ask them to reply with a letter: the page shows the comps side by side with the
structural claim each one makes, which is the part the build has to honour.

What it refuses, and why each refusal matters:

| Refused | Because |
|---|---|
| An answer with no name | An approval with no author cannot be weighed, and cannot gate anything. |
| Your own name in the `who` field | The agent proposing a direction cannot be the authority approving it. |
| A reason under 40 characters | The reason is what the next person reads when they are about to undo this. |
| Nothing at all, on timeout | Nobody chose, so there is no choice. Exit 3, NOT_RUN, no default. |

The answer lands in `.deluxui/decisions/DEC-NNN.yaml` with a hash of exactly what
was shown. Editing an approved comp afterwards makes the record stale, and
`ux_question.py check` says so — as does the phase gate, which will not let the
build proceed on an approval for a file that has since changed.

Then: `/ux-phase` to advance, and only then write code.
