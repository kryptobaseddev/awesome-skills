#!/usr/bin/env python3
"""Find where this project declares a Content-Security-Policy, and what it forbids.

The live tools inject an overlay: `ux_select.py` to let somebody point at an element,
`ux_live.py show` to put variants in place. An overlay's `<style>` element is inline
style whatever created it, so under `style-src 'self'` it appends successfully and
renders with nothing applied -- and the browser logs that refusal to the page's own
console, not to the terminal the operator is watching.

`cdp.style_policy` already measures that on the live page, which is the authoritative
answer. What it cannot do is say WHERE the policy came from, and "your overlay will not
be styled" is not actionable without a filename. A policy can be set in half a dozen
places depending on the stack, and a person who did not write it has no idea which.

So this scans for the declaration. It reports what it finds and never edits anything:
loosening a security policy is the project's decision, made in a file they own, for
their dev configuration only.

    csp.py [PATH] [--json]

Exit: 0 always. A project with no policy is a real answer, not a failure -- and a
policy that permits inline style is a different real answer from one that forbids it.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

SKIP = {"node_modules", ".git", "dist", "build", ".next", ".svelte-kit", "out",
        "coverage", ".venv", "venv", "__pycache__", ".turbo", ".cache", ".deuxui",
        "target", "Pods", ".gradle", ".output", ".nuxt"}

# Where a policy is declared, per stack. The name is what gets reported, so it has to
# tell somebody who did not write the file what they are looking at.
WHERE = [
    (re.compile(r"^next\.config\.(js|mjs|cjs|ts)$"), "Next.js config"),
    (re.compile(r"^middleware\.(js|ts)$"), "Next.js middleware"),
    (re.compile(r"^proxy\.(js|ts)$"), "Next.js proxy"),
    (re.compile(r"^nuxt\.config\.(js|mjs|ts)$"), "Nuxt config"),
    (re.compile(r"^svelte\.config\.(js|mjs)$"), "SvelteKit config"),
    (re.compile(r"^astro\.config\.(js|mjs|ts)$"), "Astro config"),
    (re.compile(r"^vite\.config\.(js|mjs|ts)$"), "Vite dev-server headers"),
    (re.compile(r"^vercel\.json$"), "Vercel headers"),
    (re.compile(r"^netlify\.toml$"), "Netlify headers"),
    (re.compile(r"^_headers$"), "static host headers"),
    (re.compile(r"^nginx\.conf$|\.nginx$"), "nginx config"),
    (re.compile(r"^Caddyfile$"), "Caddy config"),
]
SOURCE_EXT = {".html", ".htm", ".tsx", ".jsx", ".ts", ".js", ".svelte", ".vue",
              ".astro", ".ejs", ".hbs", ".php"}

_HEADER = re.compile(r"content-security-policy(?:-report-only)?", re.I)
_META = re.compile(r"""<meta\s[^>]*http-equiv\s*=\s*["']?\s*content-security-policy"""
                   r"""(?:-report-only)?""", re.I)
# The directive and its value, from anywhere on the line or the two after it.
# The value runs to the directive separator. Single quotes are NOT a terminator --
# a CSP value is mostly single-quoted keywords (`'self'`, `'unsafe-inline'`,
# `'nonce-...'`), and excluding them made every value come back as `' '`: the scanner
# stopped at the first character of the first keyword and then reported that it could
# not read the policy.
_DIRECTIVE = re.compile(r"\b(default-src|style-src|style-src-elem|style-src-attr|"
                        r"script-src|script-src-elem)\b([^;\n\"`)]*)", re.I)


def _inline_ok(value: str) -> bool | None:
    """Does this directive value permit inline style/script? None when it cannot be told."""
    v = value.lower()
    if "'unsafe-inline'" in v:
        # A nonce or hash beside 'unsafe-inline' makes modern browsers IGNORE it.
        if "'nonce-" in v or "'sha256-" in v or "'sha384-" in v or "'sha512-" in v:
            return False
        return True
    if "'nonce-" in v or "'sha" in v:
        return False
    if v.strip() in ("", "*"):
        return None
    return False


def scan(root: Path | None = None, limit: int = 6000) -> dict:
    """Every place a policy is declared, and what each one says about inline style."""
    root = root or Path.cwd()
    found, n = [], 0
    for p in sorted(root.rglob("*")):
        if n >= limit:
            break
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP for part in rel.parts):
            continue
        name, kind = p.name, None
        for pat, label in WHERE:
            if pat.match(name):
                kind = label
                break
        if kind is None and p.suffix.lower() not in SOURCE_EXT:
            continue
        n += 1
        try:
            body = p.read_text(errors="replace")
        except OSError:
            continue
        if not _HEADER.search(body):
            continue
        lines = body.splitlines()
        at = next((i for i, ln in enumerate(lines) if _HEADER.search(ln)), None)
        if at is None:
            continue
        # Directives are collected from the WHOLE file, not from a window after the
        # header mention. The first version scanned forward and reported "nothing
        # readable" on the commonest shape there is -- a Next.js config that builds the
        # policy in a `const csp = ` template literal ABOVE the `headers()` call that
        # sets it. The directives were ten lines in the wrong direction.
        vals: dict[str, set] = {}
        for m in _DIRECTIVE.finditer(body):
            vals.setdefault(m.group(1).lower(), set()).add(m.group(2).strip())
        dirs = {k: sorted(v)[0] for k, v in vals.items()}
        # A file can carry an enforcing policy and a report-only one, or a dev policy
        # and a production policy. Merging them would answer confidently about a policy
        # that is not the one in force.
        ambiguous = sorted(k for k, v in vals.items() if len(v) > 1)
        found.append({
            "file": str(rel), "line": at + 1,
            "kind": kind or ("meta tag" if _META.search(body) else "source"),
            "delivery": "meta tag" if _META.search(lines[at]) else "header",
            "directives": dirs,
            "ambiguous": ambiguous,
            "style_inline_allowed": (None if ambiguous and
                                     any(k in ambiguous for k in
                                         ("style-src-elem", "style-src", "default-src"))
                                     else _style_verdict(dirs)),
        })
    return {"root": str(root), "policies": found,
            "any": bool(found),
            "blocks_overlay": any(f["style_inline_allowed"] is False for f in found)}


def _style_verdict(dirs: dict) -> bool | None:
    """Whether an injected `<style>` would apply, from the most specific directive set.

    `style-src-elem` beats `style-src`, which beats `default-src` -- checking them in
    the wrong order reports the wrong answer on any policy that sets more than one."""
    for key in ("style-src-elem", "style-src", "default-src"):
        if key in dirs:
            return _inline_ok(dirs[key])
    return None


def advice(r: dict) -> str:
    """One paragraph a person can act on, or a plain statement that there is nothing to do."""
    if not r["any"]:
        return ("No Content-Security-Policy is declared anywhere in this project, so "
                "nothing here will block an injected overlay.")
    lines = []
    for f in r["policies"]:
        v = f["style_inline_allowed"]
        says = ("permits inline style" if v is True else
                "FORBIDS inline style" if v is False else
                f"declares {', '.join(f['ambiguous'])} more than once, with different "
                f"values, so which policy is in force cannot be read here"
                if f.get("ambiguous") else
                "says nothing this can read about inline style")
        lines.append(f"  {f['file']}:{f['line']}  ({f['kind']}, {f['delivery']}) {says}")
        if f["directives"]:
            lines.append("      " + "; ".join(
                f"{k} {v}" for k, v in sorted(f["directives"].items()) if v))
    tail = ("\n\nAt least one policy forbids inline style, so `ux_select.py` and "
            "`ux_live.py show` will refuse rather than draw an unstyled overlay. "
            "Nothing here changes that for you: add `'unsafe-inline'` to `style-src` in "
            "your DEV configuration only if you want the overlay, or review through "
            "`ux_review.py serve`, which proxies the page and does not inherit its "
            "policy." if r["blocks_overlay"] else
            "\n\nNothing found here forbids inline style, so the overlay should render. "
            "`cdp.style_policy` measures it on the live page, which is the answer that "
            "counts -- a policy can also arrive from a CDN or a reverse proxy that no "
            "file in this repo mentions.")
    return "\n".join(lines) + tail


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = scan(Path(a.path))
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    sys.stderr.write(f"\n{advice(r)}\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
