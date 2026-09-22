---
description: Show or advance the build phase — discover, declare, comp, approve, build, verify, release — with each transition's requirements machine-checked.
argument-hint: "[status|advance|check]"
---

Invoke the `deuxui` skill and read `references/ops/phase.md`.

```bash
python3 scripts/ux_phase.py status
```

deuxui's claim has always been that the visual contract is declared **before** the
code it governs, because a contract written afterwards is a description of whatever
got emitted: it will always show conformance and it is worth nothing. That was a
comment until this gate existed.

```
discover -> declare -> comp -> approve -> build -> verify -> release
```

Entering `comp` snapshots the contract's hash, the git head, and the hash of every
UI file. Entering `verify` compares against it, so "the declaration came first" is
measured from the tree rather than asserted in a report. `A-PHASE-ORDER` FAILs when
the contract was declared and not one UI file has changed since — which is what a
contract written to describe existing code looks like from the outside.

A brownfield project says so (`ux_phase.py init --brownfield`) and the same
snapshot answers the honest version: the contract was derived from what was there,
and conformance is a claim about what changed after.

```bash
python3 scripts/ux_phase.py advance      # checks the next phase's requirements
python3 scripts/ux_phase.py check        # the three process detectors, as a verdict
```

Before `build`, writing UI source is refused — by the plugin's PreToolUse hook, in
the moment, not at review time. The refusal names the missing requirement and the
one command that satisfies it. If proceeding anyway is the right call, say so on
the record:

```bash
python3 scripts/ux_phase.py override build --who "NAME" --reason "..."
```

That is deliberate. A gate with no way past it gets bypassed by deleting the state
file, and then there is no record at all. An override leaves one, with a name and a
reason, and the report carries it.

The gate is opt-in: with no `.deuxui/phase.yaml` nothing is refused, and the
process detectors report NOT_RUN rather than passing.
