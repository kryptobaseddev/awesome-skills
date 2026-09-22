# DeuxUI — the name, and the system it has to keep

A tool that asks every project to declare its visual system before building, and
then themes its own pages from hardcoded hex, has an argument it does not believe.
This file is the declaration. `assets/brand/brand.contract.yaml` is the machine half
of it, in exactly the format every project is asked for, and `selftest.py` measures
the surfaces this skill serves against it with the same detectors it points at
everybody else.

## Three layers, and the name is only the first

| Layer | Its job | The text |
|---|---|---|
| **Name** | Identity and memorability | **DeuxUI** |
| **Tagline** | What it does | *Design system rules for AI agents* |
| **Sub-line** | How it does it | *Strict UX/UI best practices, enforced at the token level* |

The name is the **who**; the tagline is the **what**. Never let the name carry the
product description — a name that has to explain the product is a name that needs a
paragraph, and a paragraph is not a name.

## Say "deuce"

Most English speakers will read **DeuxUI** as *deuce-you-eye*, not the French *doo*.
That is fine, and it is not a problem to be corrected. **Own the "deuce" reading**:
it is a real English word, it is short, and it has an edge that suits a tool whose
main verb is *refuse*.

The explanation is one line and it never grows:

> **Deux is French for two — UX and UI.**

Three seconds. It is a hook, not a lecture.

**The bar test.** Somebody says "I use DeuxUI". The follow-up is *"what's that?"* and
the answer is *"French for two — it's a design rules engine for AI agents."* Done,
in five seconds. If that does not land, the tagline needs work, not the name.

## Voice

Direct, declarative, no fluff. State the number, then what follows from it.

> DeuxUI enforces 235 design rules. Your agent doesn't guess. It follows.

Rules for the voice, and they are the same rules the reports follow:

- **Name the number.** "235 rules", "184 static checks", "1.98:1", "320px". A claim
  with a number can be checked; a claim without one is atmosphere.
- **Say NOT_RUN when nothing ran.** The voice never rounds an unknown up to a pass.
  This is the product's whole thesis and the copy does not get an exemption from it.
- **Declarative, not aspirational.** "It refuses production UI edits until somebody
  has accepted a prototype" — not "helps you ship with confidence".
- **No superlatives about ourselves.** Not "the most advanced". The matrix is the
  argument; an adjective in front of it weakens it.
- **Second person for instructions, third for behaviour.** "Run the static tier."
  "It reports NOT_RUN."

## The mark

The **2** is the visual anchor: two disciplines, and a version marker, in one glyph.
Geometric, drawn from the same hairline the depth metaphor uses, on the off-white
ground with the single accent.

```
assets/brand/mark.svg        the 2, square, for an icon or avatar
assets/brand/wordmark.svg    DeuxUI set as one lockup
```

Both are flat SVG with no gradient and no filter, in two colours plus the ground,
and both stay legible at 16px and in forced-colors mode — a mark built from a
gradient is a mark that vanishes when the operating system takes the palette away,
which is the failure `R-FORCED-COLORS` exists to catch.

## Precision, not playfulness

A rules engine, not a creative studio. What that rules out, concretely:

| Not this | Because |
|---|---|
| A multi-hue gradient | The loudest tell that a thing was generated, and catching that tell is the product |
| Soft shadows and floating cards | The depth metaphor is `border`. A hairline also survives forced-colors mode; a shadow is dropped entirely |
| Two display faces | One grotesque held at both ends of the ladder reads as more precise than a display face doing personality over a body face doing work |
| Emoji in headings or buttons | `S-SLOP-EMOJI`. We check for it |
| Green or red as the brand accent | Both already mean something on every page this skill serves: green is a PASS, red is a FAIL. An accent sharing a hue with a verdict makes the verdict decorative |
| "Effortless", "seamless", "magical" | The tool's value is that it is *not* effortless — it refuses things |

The accent is **#1f5eff**, one electric blue, and nothing else on the page is
chromatic. The ground is off-white paper at **#f7f6f3**; dark mode is *composed*,
never inverted — a real dark theme reduces contrast **and** saturation, and inversion
causes glare.

## Where the brand applies, and where it must not

The brand dresses **DeuxUI's own chrome**: the decision page, the review page, the
prototype shell's frame, the reports.

It must never theme the thing being reviewed. A reviewer comparing two variants has
to know instantly which pixels are the tool and which are the product, and a tool
wearing the product's colours makes that impossible. So the review page's own frame
comes from this contract and the framed variants keep theirs — which is also why the
prototype generator reads the *project's* contract and the review chrome reads this
one.

## Adjudicated by

The same detectors as anything else: `S-CONTRACT-COLOR` · `S-CONTRACT-FAMILY` ·
`S-CONTRACT-RAMP` · `S-CONTRACT-RADIUS` · `S-CONTRACT-DEPTH-METAPHOR` · `S-CONTRACT-ELEVATION`
· `S-CONTRACT-MOTION` · `S-TOKEN-HEX` · `S-CONTRAST-PAIR` · `S-SLOP-*`.

`selftest.py` renders this skill's own served pages and runs those checks against
this contract. A brand claim nobody measured is the same shape as a PASS on a check
that never ran.
