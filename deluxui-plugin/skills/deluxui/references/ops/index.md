# Operations

Thirty-three operations, each one a named job with a mechanism behind it and a set
of detectors that adjudicate its output. The ten broader
[workflows](../workflows/) are the modes; these are the moves inside them.

Every one of these is derived from the impeccable skill (Apache-2.0,
github.com/pbakaus/impeccable), whose command set is the most complete statement
of design craft for an agent that exists. What is added here is a verdict: each
operation ends by naming the detectors that will judge it, so "the hierarchy
holds" becomes a row with a status. See [../../NOTICE.md](../../NOTICE.md) for
what was taken and what was changed.

## Deciding what to build

| Operation | For |
|---|---|
| [routing](routing.md) | The request does not name an operation. Start here. |
| [shape](shape.md) | Discovery. Returns a brief and no code. |
| [new-work](new-work.md) | Originate a visual world and commit it to the contract. |
| [visualize](visualize.md) | **Stage one.** Three wireframes — rendered from the contract, generated where a model exists, then measured back against it. |
| [decide](decide.md) | Serve the wireframe choice as a page and record who chose, when, why, and against exactly what. |
| [prototype](prototype.md) | **Stage two.** Generate a working prototype from the contract and let a person use it, clicking elements to say what is wrong in their own words. |
| [phase](phase.md) | The gate: discover, declare, comp, approve, build, verify, release. Refuses UI edits before a direction is approved. |

## Making the system

| Operation | Tool behind it |
|---|---|
| [colorize](colorize.md) | `palette.py` — OKLCH roles, every pair contrast-checked |
| [typeset](typeset.md) | `typescale.py` — a ladder whose steps can carry different jobs; `fontindex.py` — whether the declared face is one the product can actually render |
| [layout](layout.md) | priority first, then the grid; `R-REFLOW` settles it |
| [animate](animate.md) | the motion band, the banned curves, one authored moment |
| [craft](craft.md) | the sixteen-detector floor |

## Changing what exists

| Operation | The move |
|---|---|
| [bolder](bolder.md) | Raise one part, in the system's own vocabulary. |
| [quieter](quieter.md) | Reduce competition, not content. |
| [distill](distill.md) | Remove, without removing a recovery path. |
| [clarify](clarify.md) | Make the screen say what it is. |
| [delight](delight.md) | Character at the moments that earn it. |
| [overdrive](overdrive.md) | The top of the system's range, still inside it. |
| [extract](extract.md) | Consolidate what repeats three times with one intent. |
| [adapt](adapt.md) | A different viewport, input mode, locale or theme. |
| [polish](polish.md) | The last pass. Produces the verdict. |

## Native platforms

| Operation | For |
|---|---|
| [ios](ios.md) | 20 rules, 18 static detectors, Simulator evidence. |
| [android](android.md) | 18 rules, 16 static detectors, emulator evidence. |
| [adapt-native](adapt-native.md) | Phone to tablet, platform to platform, web to native. |
| [audit-native](audit-native.md) | A code-level audit with no composite score. |

## Working

| Operation | For |
|---|---|
| [onboard](onboard.md) | The first five minutes in a new project. |
| [document](document.md) | Derive the contract the code already implies. |
| [generate](generate.md) | Scaffold from the contract, with every state. |
| [live](live.md) | Change something, see what moved. |
| [live-setup](live-setup.md) | Wire the loop once so it runs without flags. |
| [hooks](hooks.md) | Surface the defect while the file is still open. |
| [doctor](doctor.md) | What this installation can and cannot check. |
| [operate](operate.md) | Depth for product and reading surfaces. |

## The one rule that spans all of them

An operation ends in a status, not an impression. If yours ends with "this looks
better now", it has not finished — run the detectors it named and read what they
say. And if they all pass, that is a floor: it means nothing is in the way, which
is not the same as it being good.
