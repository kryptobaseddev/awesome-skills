# prototype — build the thing, then let somebody use it

A wireframe settles **structure**: what is on the screen, in what order, at what
proportion. It cannot settle whether the thing works, because a drawing cannot be
used. Using an interface and looking at one are different activities, and almost
everything that goes wrong is only findable by the first.

So there are two review stages, and this is the second one.

| Stage | Artefact | Question it can answer | Tools |
|---|---|---|---|
| wireframe | SVG sheets drawn from the contract | Is this the right structure? | `ux_image.py`, `ux_question.py` |
| **prototype** | **real, working HTML** | **Does this work when you use it?** | **`ux_proto.py`, `ux_review.py`** |

## Generate a working prototype

```bash
python3 scripts/ux_proto.py --write .deluxui/proto/index.html --title "Jobs"
```

Everything it emits comes from `.deluxui/design.contract.yaml`: the colour roles
become custom properties with a composed dark theme, the type ladder becomes the
only sizes on the page, the spacing scale the only gaps, the one declared depth
metaphor the only way anything is raised. It is conformant by construction — which
also means `ux_check.py` over its output is a positive control on the generator
rather than a review of somebody's taste.

What it emits is not a picture of components. It is components:

- **the five states, as a switch** — ready, loading, empty, error, offline. The
  reviewer flips between them and sees what a person actually meets, which is the
  part that never gets built and never gets looked at.
- a **form** with real labels, `:user-invalid` validation, an error summary whose
  entries link to their fields, and a submit that guards a double submission
- a **dialog** that traps focus and closes on Escape, a destructive action with a
  confirm **and** an undo that actually puts the row back
- **tabs** with roving `tabindex` and arrow keys, because a row of buttons that
  looks like tabs does none of that
- a **table** with real header scope, tabular figures, and zero shown differently
  from not-collected
- a **switch**, disabled controls that say *why*, theme and density toggles
- an **activity list**, because a confirmation that exists only in a toast is gone
  in ten seconds along with anything the user needed to refer back to

Notes stay editable for as long as the review is open: note mode is sticky, a pin
reopens its note, and the panel edits or withdraws one. A reviewer working out
what they think will rewrite a sentence three times, and that third version is
usually the one worth reading.

If the contract declares a typeface this project does not ship, the page says so
on its own face. Judging type in a fallback nobody chose wastes the review.

## The wrapper is a template, not output

Every prototype uses the same shell, so a reviewer learns the chrome once and
then only has to think about the screen:

```
assets/templates/prototype-shell.html
```

It has named slots — `{{title}}`, `{{tokens}}`, `{{css}}`, `{{depth}}`,
`{{banners}}`, `{{header}}`, `{{sections}}`, `{{script}}`, `{{density}}` — and
`ux_proto.py` fills them from the contract. Edit that file and every prototype
the project generates from then on inherits the change. Its own documentation
block is stripped before filling, so it never reaches the output.

The built-in systems are sections with stable ids — `states`, `controls`, `tabs`,
`form`, `table`, `durable` — and a real product screen is another one:

```bash
cat > screens.html <<'HTML'
  <section class="proto-section" id="reschedule">
    <h2>Reschedule</h2>
    <div class="card"> ... only tokens: --role, --t*, --s*, --r-ctl ... </div>
  </section>
HTML
python3 scripts/ux_proto.py --write .deluxui/proto/index.html --sections screens.html
python3 scripts/ux_proto.py --write .deluxui/proto/index.html --shell my-shell.html
```

Two rules for anything added, and both are checkable rather than advisory:

1. **Only declared values.** Every colour a `--role`, every size a `--t*`, every
   gap a `--s*`, every radius `--r-ctl` or `--r-card`. A literal is a departure
   and `ux_check.py` names it with the line.
2. **Every state, not the happy one.** A section that renders one state teaches
   the reviewer nothing about the four they will actually meet.

## Put it in front of a person

```bash
python3 scripts/ux_review.py serve \
    --variant "proposed=.deluxui/proto/index.html" \
    --variant "current=http://localhost:5173/jobs" \
    --question "Does this job list work in a corridor?"
```

Both variants are **hosted by this server** — a file is served, a URL is proxied,
the selection script is injected into each and the frame-blocking headers are
dropped on the way through. Same origin, so a click inside the frame is readable.
No dev-server plugin, no framework adapter, no build step.

The reviewer gets the real interface side by side at whichever width they want to
judge it at, and then the part that usually evaporates: **Alt-click any element
in either variant and type, in their own words, what is wrong with it.**

That note is captured with the element it is about — selector, its own text, its
computed type, colour, spacing, radius, shadow, box, and the viewport it was seen
at — and written to `.deluxui/requests/REQ-NNN.yaml`. It appears in the agent's
terminal as it is written, so a long review is a stream of work items rather than
a summary at the end.

```
REQ-001  proposed/quieter   #del
    "Delete sits in the same row as Primary action at the same size. On a phone
     in a corridor that is one thumb-width from a mistake nobody can undo."
```

## Five outcomes, and only three are approvals

| Outcome | What it means |
|---|---|
| Accept `<variant>` | Build on this one. |
| Combine | Take parts of more than one — say which, in the reason. |
| **Request changes** | **Not an approval.** The notes are the work list. |
| Reject | None of these. Say what is wrong with the direction. |
| (nobody answers) | NOT_RUN. An unreviewed screen is not an approved one. |

The phase gate reads the outcome, so "request changes" leaves `build` locked while
the notes are acted on. That is the point of separating the two: a work list
cannot authorise the build it is a list of complaints about.

Refused, for the same reasons everywhere else in this tool: an answer with no
author, an author naming the agent, and a reason too thin to weigh.

## The loop

Act on the notes **in the source**, not in the DOM — the dev server reloads, the
reviewer looks again. A variant that exists only in the page has to be committed
back afterwards, and that round trip is where an edit gets lost.

```bash
python3 scripts/ux_review.py notes --source review   # the work list
python3 scripts/ux_check.py .deluxui/proto           # did the fix conform
bash scripts/ux_live.sh http://localhost:5173        # what moved, what regressed
```

## Verified by

`A-PROTO-ACCEPTED` (`GOV-014`) — somebody used a working version and accepted it,
which is a different fact from somebody liking a drawing. `A-COMP-APPROVED`
(`GOV-011`), `A-DECISION-VETTED` (`GOV-012`), and the whole static tier over the
prototype's own source.

Next: [phase.md](phase.md) to advance to `build`.
