# document — capture the visual system that already exists

Write down what the code already decided, so there is something to conform to.
The brownfield half of [new-work.md](new-work.md).

Derived from impeccable's `document` (Apache-2.0), with the output made
machine-readable — see NOTICE.md.

## Derive it, do not describe it

impeccable's `document` writes a DESIGN.md by reading the code. deluxui writes
that **and** a contract, because prose cannot be conformed to:

```bash
python3 scripts/derive_contract.py                # look at what it found
python3 scripts/derive_contract.py --write        # commit it
python3 scripts/derive_contract.py --json         # the spread report
```

It reads real font sizes and families, radii, shadows, durations and colour
roles, and emits the **dominant** value for each with the spread beside it. The
spread is the interesting part: a project with 36 declared colour roles and one
hardcoded `#888` has a system and one escape, and a project with 41 font sizes has
no type system at all. Both look identical in a screenshot.

## Read the spread before accepting the contract

The derived contract is a measurement, not a decision. Where the spread is wide,
the tool has picked the most common value and that may not be the intended one:

- **Type.** If four sizes each appear ten times, there is no ladder. Build one
  with `scripts/typescale.py` and treat the existing sizes as the migration, not
  the contract.
- **Radius.** A value used twice is not the system's radius even if it is larger.
  Check the count, not the number.
- **Colour.** Roles derived from CSS custom properties are trustworthy; roles
  derived from utility classes are a guess, and the tool says which is which.

Edit the derived contract before writing it. A contract that describes the mess
faithfully will report conformance to the mess.

## Cross-check the derived contract against what renders

`derive_contract.py` reads the source. `comp_spec.py` reads the pixels. Where they
disagree, the pixels win — the source says what was written, and the screenshot
says what survived the cascade:

```bash
bash scripts/ux_browser.sh http://localhost:5173        # writes a full-page shot
python3 scripts/comp_spec.py .deluxui/reports/runtime/screens/root_fullpage.png
```

A canvas colour that appears in 50% of the rendered pixels and nowhere in the
token file is a value the product depends on and the system has never admitted to.

## Also write the prose

`.deluxui/DESIGN.md` carries what the contract cannot: which components exist and
where, which are deprecated, what the stack is, which primitives are already
installed, and the density and theming decisions. `assets/templates/DESIGN.md` is
the shape. The component inventory is what makes the preserve ladder work —
without it, `--inventory` has nothing to search.

And `.deluxui/PRODUCT.md`: audience, jobs to be done, the rare high-impact tasks
(cancel, refund, delete, recover — LAW-20), the irreversible and external actions,
the supported devices, locales and network conditions. No colours, no fonts. That
file is what decides which rules are even applicable, and nothing in the code
states it.

## Verify

```bash
python3 scripts/ux_check.py .        # the seven S-CONTRACT-* rows now run
python3 scripts/palette.py --check .deluxui/design.contract.yaml
python3 scripts/typescale.py --check .deluxui/design.contract.yaml
```

Before this operation those rows read NOT_RUN — an undeclared system cannot be
conformed to, and saying otherwise would be the contract laundering its own blanks
into evidence. After it, every departure in the codebase is measurable.

Then: [../workflows/uplift.md](../workflows/uplift.md).
