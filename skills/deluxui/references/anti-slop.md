# The AI-tell catalogue

These patterns are not ugly. They are *recognisable* — the visual equivalent of a
tell. They appear because a model reaching for "looks designed" converges on the same
handful of moves, and a reader who has seen a hundred generated interfaces clocks it
in under a second. Several also cause measurable harm; those are marked.

Detectors: `S-SLOP-GRADIENT`, `S-SLOP-BLUR`, `S-SLOP-CARDNEST`, `S-SLOP-EMOJI`,
`S-SLOP-COPY`, `S-SLOP-UNIFORM`. The rest need your judgement.

## Colour and surface

| Tell | Why it reads as generated | Also harmful? |
|---|---|---|
| Purple-to-blue gradient on the hero, heading or primary button | The single most recognisable signature. It is the default "make it look techy" move. | Gradient text usually fails contrast against part of its own run. |
| Gradient as decoration on more than one or two surfaces | Gradients are emphasis. Everywhere means nowhere. | Yes — contrast varies across the surface. |
| Frosted glass on every panel | Reached for as a texture rather than to show depth. | Yes — kills text contrast, costs real paint time. |
| Cream or warm off-white as the "tasteful" background | The safe choice a model makes when no palette was decided. | No |
| Dark mode as an inverted light theme | Real dark themes reduce contrast *and* saturation; inversion produces glare. | Yes — pure white on pure black causes halation. |

## Shape and depth

| Tell | Why it reads as generated |
|---|---|
| Card inside card inside card | Each border repeats a boundary the eye already had. Detected at depth 3. |
| `rounded-3xl` and `shadow-2xl` on everything | If every surface floats, nothing is primary. Detected as a ratio, not a count. |
| A 1px border *and* a wide soft shadow on the same element | Two different depth metaphors arguing. Pick one. |
| A coloured accent stripe down the left edge of a rounded card | A stripe implies a category system. Usually there is no system. |
| Icon in a tinted rounded square, repeated down a feature list | The default "feature grid" shape. |

## Type

| Tell | Why it reads as generated | Also harmful? |
|---|---|---|
| One font at four weights doing all the work | No pairing decision was made. | No |
| Enormous hero heading with tight negative tracking | Scale used instead of hierarchy. | Tight tracking hurts legibility at small sizes. |
| Every section opens with a small uppercase eyebrow label | A rhythm nobody asked for, repeated per section. | No |
| Emoji in headings and buttons | Detected. | Yes — screen readers announce the full Unicode name; rendering varies per platform; rarely survives translation. |
| Em-dashes everywhere in UI copy | A writing tic, not an interface decision. | No |

## Copy

| Tell | Why it reads as generated |
|---|---|
| "Elevate your workflow", "Unlock the power of", "Seamlessly integrate" | Detected. Says nothing, could describe any product. |
| Three benefit cards of near-identical length | Content shaped to fit the grid rather than the other way round. |
| Lorem ipsum, "Your Company", "John Doe" shipped | Detected. Placeholder content hides every layout problem real content would expose. |
| "Something went wrong." | Detected. Names nothing, offers nothing. See UX-009. |

## The second-order trap

The obvious fix is to avoid the obvious thing. The trap is one level deeper: avoiding
the cliché by reaching for its equally predictable opposite. Fintech that is not
navy-and-gold becomes terminal-green monospace on black. A landing page that is not
a purple gradient becomes stark Swiss black-on-white with one red square.

That is the same reflex wearing a different coat. The escape is not a different style
— it is a reason. What does this product do, who is it for, what did they tell you in
`PRODUCT.md`? A choice you can defend from the product is never a tell, even when it
happens to be a gradient.

## What is not slop

Do not strip a design to avoid looking generated. Deleting labels, status text,
constraints or empty-state copy to make a screenshot look cleaner is a worse defect
than any tell on this page — it usually fails A11Y-005, and it is what LAW-12 (Prägnanz)
warns against, though no detector reads the laws. A dense,
plain, well-labelled interface is a good interface.
