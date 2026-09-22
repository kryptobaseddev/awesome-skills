# new-work — originate a visual world, and commit to it in writing

The one operation licensed to introduce a new visual language. Everything else
preserves the one that exists (CTX-005), so this is where a departure becomes
legitimate rather than accidental.

Derived from impeccable's `new-work` (Apache-2.0), with the world written into a
checkable contract — see NOTICE.md.

## Establish visual authority first

Before choosing anything, answer: **who decides?**

- An existing brand with tokens and components: the brand decides, and this is
  not new work. Use [../workflows/uplift.md](../workflows/uplift.md).
- A brand with assets but no system: the assets decide. Derive the world from
  them; `scripts/derive_contract.py --write` reads what the code already says.
- Genuinely nothing: you decide, and the user confirms. Only here does a world
  get invented.

Getting this wrong is the expensive mistake in both directions, and they are not
symmetric. Being wrong about preserving costs a conservative variant, which is
recoverable. Being wrong about departing costs an off-brand rewrite of somebody's
product, which is not.

## Commit to a world, in observable values

A world is a sentence a reader could check you against:

> Warm paper ground, one serif display voice, ink-black text, a single accent at
> `oklch(0.55 0.18 25)`, one-metaphor depth by hairline border, motion in a
> 160–200ms exponential ease-out.

"Modern and clean" names nothing. It cannot be conformed to and it cannot be
departed from, which means it cannot be checked, which means it is not a decision.

Then make the decision with the tools rather than by feel:

```bash
python3 scripts/palette.py --hue 25 --mode persuade --contract
python3 scripts/typescale.py --mode persuade --contract
```

Both emit contract blocks with every constraint already measured — contrast
ratios placed, type steps far enough apart to carry different jobs.

## Visitor mode before aesthetics

What did the visitor come to do? See
[../design/visitor-modes.md](../design/visitor-modes.md). It changes what colour
may own, how dramatic the type ratio can be, how much motion is defensible and
whether familiarity is a feature. A **persuade** world and an **operate** world
built from the same brand are different worlds, and picking the wrong one is a
bigger error than any colour choice inside it.

## Write the contract before the code

```bash
cp assets/templates/design.contract.yaml .deuxui/design.contract.yaml
# paste the palette and type blocks, fill depth, spacing, radius, grid, motion
```

This ordering carries the whole epistemic content. A contract written afterwards
is a description of whatever got emitted; it will always show conformance and it
is worth nothing. Leave genuinely open decisions as `UNKNOWN` — those report
NOT_RUN, which is the honest state for a decision nobody has made. Do not fill
them in to make the report quieter.

## Three variants, not one

One option invites a rubber stamp. Three surface what is actually at stake, and
the spread between them is the information. Vary the structural uncertainty —
topology, sequence, density, focal composition — not the palette three times.

Present them, take the decision or one correction round, then stop and build.

## Verify

The world is now checkable against itself:

```bash
python3 scripts/palette.py --check .deuxui/design.contract.yaml
python3 scripts/typescale.py --check .deuxui/design.contract.yaml
python3 scripts/ux_check.py .        # the seven S-CONTRACT-* rows
```

A declared palette failing its own contrast requirement means every conforming
screen inherits the failure. Catch that here, where it costs one edit.

Build: [../workflows/design.md](../workflows/design.md).
