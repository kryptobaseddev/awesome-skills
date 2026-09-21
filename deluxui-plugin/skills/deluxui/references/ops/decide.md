# decide — serve the choice, and record the answer as evidence

An approval that lives in a chat transcript gates nothing. Six weeks later nobody
can say which comp was approved, by whom, or against what — so in practice the
approval does no work, and the first person to disagree re-opens the decision.

`decide` serves the choice as a real page on localhost and writes the answer to
`.deluxui/decisions/DEC-NNN.yaml`, hashed against exactly what was shown.

impeccable's `serve-question` is the ancestor; what deluxui adds is that the
record is admissible — see NOTICE.md.

## Serve it

```bash
python3 scripts/ux_question.py ask .deluxui/comps/<surface>.comps.yaml
python3 scripts/ux_question.py ask question.yaml --port 8787 --timeout 1800
```

The page is themed from `.deluxui/design.contract.yaml` — the project's own
canvas, ink, accent and families — so the decision is made in the product's own
world rather than in a generic chrome. Its type ladder is its own, because
inheriting a flat project scale would make deluxui's surface fail deluxui's craft
check for a reason that is about the contract rather than the page.

Each option shows the comp, the thing it decides, and its **region table**: name,
medium, share, what it holds. That table is the structural claim the build has to
honour. A page that shows three pictures and no claim collects an approval of the
atmosphere.

Then hand over the URL and **wait**. Do not summarise the options in chat and ask
for a letter back; that is the transcript approval this operation exists to
replace.

## What it refuses

| Refused | Why |
|---|---|
| No `who` | An approval with no author cannot be weighed and cannot gate anything. |
| A `who` naming the agent | The party proposing the direction cannot be the authority approving it. This is the same bar `ux_report.vet_attestation` applies to a manual check, for the same reason. |
| A reason under 40 characters | The reason is what the next person reads when they are about to undo this. |
| No choice | Nothing is recorded. |
| Nobody answering | Exit 3, nothing written. NOT_RUN — never a default that a later summary describes as approved. |

`combine` and `reject` are first-class answers. A combination has to say which
parts of which options, specifically enough to build from.

## What gets recorded

```yaml
id: DEC-002
chosen: B
who: Dana Okafor
date: '2026-09-21'
rationale: Buyers arrive with a shortlist, so price and specs decide before any photograph does.
options_sha: c7fd6e07ec54ccc5     # the question, the claims, and the image bytes
shown:
  - {id: A, title: Imagery leads, image: ..., image_sha: e69a2b448002468e}
```

`options_sha` covers what was on the screen, not the file that generated it. Edit
an approved comp afterwards and the approval no longer matches:

```bash
python3 scripts/ux_question.py check       # exit 2 on a stale approval
python3 scripts/ux_question.py list
```

The phase gate reads the same records, so a build cannot proceed on an approval
for a file that has since changed. A later decision about the same comp set
supersedes an earlier one — superseded records authorise nothing and are not
counted as defects.

## Verified by

`A-COMP-APPROVED` (`GOV-011`) · `A-DECISION-VETTED` (`GOV-012`) ·
`A-COMP-CONFORM` (`VIS-001`, `GOV-013`)

Next: [phase.md](phase.md) to advance, and only then write code.
