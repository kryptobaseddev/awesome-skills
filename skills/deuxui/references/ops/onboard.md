# onboard — set this tool up in a project it has never seen

The first five minutes. Get to a report that says something true, then improve
the report.

Derived from impeccable's `onboard` (Apache-2.0) — see NOTICE.md.

## 1. Find out what can run

```bash
python3 scripts/doctor.py .
```

This is the first command in every new project, because every later result
depends on it. It names which tiers can run on this machine, what is missing, and
what each absence costs in rules.

## 2. Scan before configuring anything

```bash
python3 scripts/ux_check.py . 2>&1 | tail -30
```

A cold scan of a real codebase produces a lot. Resist the urge to configure it
quieter. Read the top twenty findings first: they tell you what kind of codebase
this is, and that shapes every choice below.

## 3. Write the project memory

```bash
python3 scripts/derive_contract.py --write     # the visual contract, from the code
python3 scripts/manual_sheet.py --write        # the questions for a person
cp assets/templates/ux.config.yaml .deuxui/ux.config.yaml
cp assets/templates/PRODUCT.md .deuxui/PRODUCT.md
```

Then fill in, in this order of value:

1. **`PRODUCT.md`: the irreversible and external actions.** Nothing in the code
   states these and they drive the whole destructive-action family. This is the
   single highest-value thing a human can write here.
2. **`ux.config.yaml`: `exclude`.** Generated clients, vendored code, a demo
   directory. Excluding noise is legitimate; excluding a failing area is not, and
   the report names which config narrowed the scope.
3. **`app.dev_url` and `api_pattern`.** See [live-setup.md](live-setup.md).
   `api_pattern` is what makes the forced-state probes possible.
4. **`features`.** Declare `forms`, `payments_or_legal`, `ai_features` and the
   rest, so the rules that apply are applicable. iOS and Android are measured
   from the tree and need no declaring.

## 4. Do not start by disabling checks

`disabled_checks` moves a rule to NOT_RUN, never to PASS, and the merged report
says which config silenced it. That is the design: narrowing what was examined is
allowed, and converting an unexamined rule into a passing one is not.

If a detector is genuinely wrong on this codebase, that is a bug worth reporting
rather than a setting worth flipping. A checker with a high false-positive rate
gets ignored, which defeats the whole point.

## 5. Install the hook

See [hooks.md](hooks.md). This is the highest-leverage step and the one most
often skipped: the hook puts a defect in front of the agent while it is still
holding the file, which is the only moment the fix is cheap.

## 6. Baseline, then start

```bash
bash scripts/ux_live.sh http://localhost:5173      # records the baseline
```

Every run after this one shows what moved. Work down a family at a time.

## What good looks like after an hour

Not zero findings. A report where NOT_RUN is small and explained, FAIL is a list
somebody is working through, and no PASS is standing in for something nobody
checked.
