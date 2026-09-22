---
description: Move a design to a different context — viewport class, input mode, density, locale or theme. Adaptation is not scaling.
argument-hint: "<the target> <the context: mobile, tablet, touch, RTL, dark, print>"
---

Target: $ARGUMENTS

Invoke the `deuxui` skill and follow `references/ops/adapt.md`. For phone-to-tablet
or platform-to-platform work on native code, read
`references/ops/adapt-native.md` instead.

Assess before changing: what did this design assume? Mouse and hover
(`S-HOVER-ONLY`)? A wide viewport (`S-RESP-FIXEDPX`)? English, one text direction,
short words (`S-CONTENT-I18N`, `S-CONTENT-FORMAT`)? One theme? Each assumption is a
rule in this tool, and the adaptation is the work of removing it.

Then measure, in the browser, in the target context: `R-REFLOW` at the narrow
widths, `R-TARGET-COARSE` for touch, `R-ZOOM` at 200%, `R-TEXTSPACING` with the
user's own overrides applied, `R-ORIENTATION` in both, `R-CONTRAST` again in the
new theme. A layout that "looks fine on mobile" in a resized desktop window has
not been adapted; it has been squeezed.
