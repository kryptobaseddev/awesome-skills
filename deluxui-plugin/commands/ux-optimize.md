---
description: Fix perceived and measured performance — jank, layout shift, slow feedback.
argument-hint: "[url or route]"
---

Run the deluxui `optimize` workflow on $ARGUMENTS.

Invoke the `deluxui` skill, then follow its `optimize` workflow
(`references/workflows/optimize.md`).

Measure before changing anything — `ux_browser.sh` reports LCP, CLS, INP, TTFB and FCP
from `vitals`. Perceived speed and measured speed are different problems with different
fixes; say which one you are solving.
