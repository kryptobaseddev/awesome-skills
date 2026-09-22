# routing — which operation, for what the user actually said

Read this when the request does not name an operation. Do not run anything yet:
pick, say why in one line, and let the user confirm.

Derived from impeccable's `routing` (Apache-2.0) — see NOTICE.md.

## Make the recommendation from measurements

```bash
python3 scripts/doctor.py . --json      # what is set up, what is missing
python3 scripts/ux_check.py . --signals # what kind of codebase this is
```

`--signals` returns raw facts and **no score**: the Tailwind major version, the
theme variable count, the token sources, the component count, the detected
platforms, whether i18n and container queries are present. Reason over them; there
is no number to obey, on purpose — a composite score lets a 2 in accessibility
average away against a 4 in performance, and the 2 is somebody unable to use the
product.

Lead with the two or three highest-value next steps, each with a one-line reason
drawn from the signals:

| Signal | Route |
|---|---|
| no `.deuxui/` at all | [onboard.md](onboard.md) |
| code but no contract | [document.md](document.md) |
| a contract with most values UNKNOWN | [new-work.md](new-work.md), or derive |
| `agent-browser` missing | [live-setup.md](live-setup.md) — most rules cannot run |
| platforms detected, no native captures | [audit-native.md](audit-native.md) |
| a wide type or colour spread in the derived contract | [typeset.md](typeset.md), [colorize.md](colorize.md) |
| many `S-CRAFT-*` failures | [craft.md](craft.md) |
| many `A11Y-*` or `STATE-*` failures | [../workflows/harden.md](../workflows/harden.md) |
| nobody has answered any manual question | `manual_sheet.py --check` |
| changed files point at one surface | scope the audit to those files, and name them |

## What the words usually mean

| They said | They usually want | Not |
|---|---|---|
| "make it look better" | [polish.md](polish.md), then [craft.md](craft.md) | a redesign |
| "the design feels off" | [craft.md](craft.md) — the floor first | taste advice |
| "make it bolder" | [bolder.md](bolder.md), scoped to one thing | a new world |
| "simplify this" | [distill.md](distill.md) | deleting recovery paths |
| "clean it up" | [quieter.md](quieter.md) or [distill.md](distill.md) — ask which | removing the focus ring |
| "is this accessible" | [../workflows/harden.md](../workflows/harden.md) + `M-SCREENREADER` | a scan alone |
| "redesign this" | [new-work.md](new-work.md) **only** if visual authority allows | assuming it does |
| "make it responsive" | [../workflows/responsive.md](../workflows/responsive.md) | breakpoint guesses |
| "it's slow" | [../workflows/optimize.md](../workflows/optimize.md) | a spinner |

## Two rules about routing

**Never auto-run.** The recommendation is a suggestion the user confirms. This
tool changes files and records verdicts; both deserve a yes.

**"Redesign" is the one word to slow down on.** CTX-005 makes introducing a new
visual language a defect unless authority allows it, and the asymmetry is the
reason: being wrong about preserving costs a conservative variant, which is
recoverable. Being wrong about departing costs an off-brand rewrite of somebody's
product, which is not. Establish authority first —
[new-work.md](new-work.md) opens with how.
