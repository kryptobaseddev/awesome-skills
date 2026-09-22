---
description: Pick an element in the running app, compare two or three variants in its own position, and accept one into the source — every variant built from declared values only, and accept refused if it introduces a P0 or P1 finding.
argument-hint: "[pick|vary ID|show ID|accept ID --variant B]"
---

Invoke the `deuxui` skill and read `references/ops/live.md`.

```bash
python3 scripts/ux_live.py pick                         # point at it
python3 scripts/ux_live.py vary REQ-001 --count 3        # variants, from the contract
python3 scripts/ux_live.py show REQ-001                  # all of them, in the page
python3 scripts/ux_live.py accept REQ-001 --variant B --who "NAME"
```

A person looks at the real app, says *that bit*, sees honest alternatives **in the
element's own position**, picks one, and the pick lands in the source. Nothing else
in this skill edits the thing while somebody is looking at it — which is why it is
the one that refuses the most.

**A variant can only propose declared values.** Sizes off the type ladder, colours
by role, gaps on the spacing scale, raises using the one declared depth metaphor. So
the alternatives are conformant by construction and choosing between them cannot
accidentally choose drift. Where the project has a custom property for a value, the
variant emits `var(--color-canvas)` rather than the literal — a literal in a rule is
a token that escaped, and it will not follow the theme or flip in dark mode.

**One axis at a time.** `type-up`, `type-down`, `space-loose`, `space-tight`,
`surface`, `emphasis`, `depth`, `radius-card`, `radius-control`. Three variants that
move everything at once cannot tell you which change did the work. Steer with
`--direction "bolder"` (also `quieter`, `tighter`, `roomier`, `lift`, `flatter`); a
direction with no matching axis is reported as unmatched rather than approximated.

**Ambiguous source refuses.** The element must resolve to exactly one place — by its
text first, then its classes. Zero or several, and it names the anchors it tried and
stops. Writing to the wrong line is worse than not writing: the edit is plausible,
the page does not change, and nobody knows why.

**Accept is measured.** The edit goes onto a copy of the tree, the static tier runs,
and a variant that introduces a P0 or P1 is refused with the number quoted:

```
REFUSED. This variant introduces 2 P0/P1 finding(s):
  P1  S-CONTRAST-PAIR  src/styles/tokens.css:7
    Contrast 1.98:1 is below the 4.5:1 floor for normal text (NUM-001).
```

Taste chooses between admissible options. It does not make an inadmissible one
admissible.

The accepted change becomes one commented rule in the stylesheet that already holds
the project's tokens, scoped to a class the element already has — never a new file
nobody imports, never an invented class name that leaves the change half-applied.
`--into PATH` and `--scope '.sel'` override that. `--dry-run` shows the diff and
writes nothing.

Every accept records a decision with the axis, the declarations, the file written to,
the check delta and the hash of the contract it was decided against, and archives
that contract's bytes — so `/ux-ledger show DEC-003` can print what was declared
**then**. It is not a build approval: it changed one element's rule.

The phase gate applies. Production UI edits wait until somebody has used a prototype
and accepted it; `--force` writes anyway, on the record.

For "did that edit help", use `/ux-delta` — a different question, and it needs no
person to answer it.
