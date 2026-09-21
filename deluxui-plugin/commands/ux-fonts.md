---
description: Check that every typeface the product declares is one it can actually render, and whether the families it pairs carry different jobs.
argument-hint: "[path]"
---

Invoke the `deluxui` skill.

```bash
python3 scripts/fontindex.py ${1:-.}
python3 scripts/fontindex.py ${1:-.} --check     # exit 2 when a declared face is missing
```

The failure this catches is silent by construction: the contract names a face, the
scale and leading are tuned for it, the CSS asks for it, and nothing in the
repository provides it. The browser falls back without a warning and every
downstream judgement about the type is a judgement about a typeface nobody chose.

It looks for all five ways a face legitimately arrives — an `@font-face` rule, an
`@fontsource` package (imported *or* in the manifest), `next/font`, a font file in
the tree, and a Google Fonts request — and it matches across spellings, so `Söhne`
in the contract resolves to `sohne-web-buch.woff2` on disk.

One thing it refuses to do: treat the faces installed on **this** machine as
evidence that a visitor has them. A build host's font list describes the build
host. Host faces are reported separately and labelled as what they are.

It also reads the pairing:

```bash
python3 scripts/fontindex.py --pair "Fraunces" "Inter"
```

Two families of the same class read as one family rendered inconsistently. Either
take the contrast, or drop to one family and carry the hierarchy on weight and
size — which is cheaper and usually better. See `references/craft/type.md`.
