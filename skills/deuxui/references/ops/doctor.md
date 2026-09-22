# doctor — what this installation can and cannot check

Maintenance, not design. Run it first in any project, and run it again whenever a
report looks unexpectedly quiet.

```bash
python3 scripts/doctor.py .
python3 scripts/doctor.py . --json
```

Derived in spirit from impeccable's `doctor` (Apache-2.0); the checks are
deuxui's own — see NOTICE.md.

## Why this exists

Every tier of this tool degrades quietly. No browser means the runtime rules stay
NOT_RUN. No contract means the conformance rules stay NOT_RUN. No `manual.yaml`
means the judgement rules stay NOT_RUN. No Xcode means the iOS evidence rules stay
NOT_RUN. A reader who does not know that reads a page of NOT_RUN as pessimism
about the code, when it is a list of things nobody has set up.

Three kinds of "out of date" travel together and the report keeps them apart:

- **Install drift.** A missing dependency, shipped bytecode, a broken registry.
  Mechanical, and the report names the fix.
- **Setup drift.** No config, no contract, no manual sheet, no dev URL. Each one
  is a set of rules that cannot report anything. Fixable in minutes.
- **Truth drift.** The contract no longer describes the code. No file comparison
  settles this — `derive_contract.py` measures what the code says now, and the
  difference is a conversation, not a defect.

## Read the states literally

| State | Meaning |
|---|---|
| `ok` | This check ran and found what it expected. |
| `warn` | It works, degraded, and the consequence is stated. |
| `GONE` | A set of rules will report NOT_RUN no matter how good the code is. |

The exit code is 2 when anything is `GONE`, so this composes in CI: a pipeline
that runs an audit without a browser installed is a pipeline reporting on a
fraction of the rules, and it should say so rather than go green.

## What it will not do

It will not fix your project, redesign anything, or run another operation as a
side effect. It reads, reports, and names the command that would close each gap.

And it never reports a tier as fine because it did not look. A check that cannot
be performed is listed as unavailable, which is the same discipline the rest of
the tool applies to rules.
