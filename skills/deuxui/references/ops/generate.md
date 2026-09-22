# generate — scaffold against the contract, not against a template

Producing a new screen, component or flow from the declared system, so the output
conforms by construction rather than by later correction.

Derived from impeccable's `generate` (Apache-2.0), with generation bound to the
contract — see NOTICE.md.

## The preserve ladder runs first

`PRESERVE > MODIFY > COMPOSE > CREATE`. Before writing a component, find out
whether it exists:

```bash
python3 scripts/ux_check.py . --inventory "modal dialog sheet"
```

It lists matching primitives and the primitive libraries already installed. Record
which you reused, or why none fit. COMP-001 is the rule and `S-A11Y-DIVCLICK` is
one of the consequences of ignoring it: a hand-built control loses the name, the
role, the keyboard pattern and the focus behaviour the native element had.

## Generate from the contract

Read `.deuxui/design.contract.yaml` and use it. Concretely:

```bash
python3 scripts/typescale.py --css > src/styles/type.css      # the declared ladder
python3 scripts/palette.py --seed '#1f6feb' --css > src/styles/color.css
```

Then every generated component references roles and rungs rather than values.
A component written with `text-[19px]` and `#3b82f6` is a component that will
show up as an escape the moment anything checks it, and fixing it later costs
more than reading the contract now.

## Generate every state, not the happy one

This is the single largest difference between generated interfaces and built
ones. The happy path is the easy part and it is the part that gets written.
A new screen is not finished until it has:

| State | Rule |
|---|---|
| empty, with a next action | UX-001, COMP-017 |
| loading, with a pending status by 1s | STATE-001, NUM-014 |
| error, naming the failure and the recovery | STATE-001, UX-009 |
| the in-flight guard, so a double submit commits once | STATE-003, NUM-020 |
| the maximum content length, not three items | CONTENT-007 |
| the single-item case | — |
| offline | STATE-006 |

Write them in the same edit as the component. The PostToolUse hook will tell you
which are missing while you still have the file open, which is the only time the
cost of adding them is small.

## Verify

```bash
python3 scripts/ux_check.py src/components/NewThing.tsx
```

Single-file scope reports every rule as NOT_RUN rather than PASS — one file cannot
establish a product-wide property, and reporting 116 PASS off one edited component
would be the laundering this tool exists to refuse. Read the findings, then scan
the project.

Then: [polish.md](polish.md).
