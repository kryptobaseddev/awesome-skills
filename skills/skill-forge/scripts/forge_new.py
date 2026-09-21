#!/usr/bin/env python3
"""Scaffold a skill that passes the gate on its first run.

Nothing in this repository creates a skill from nothing -- plugin-creator
scaffolds plugins, skill-validator checks, skill-evaluator measures, and the
globally-installed skill-creator writes files ad hoc. So every skill here was
hand-authored, and every author rediscovered the same constraints: the exact
name pattern, which category slugs are real, that an unrecognised slug fails
silently, that the depth rule counts references/*.md non-recursively, and that
core.fileMode=false means a chmod never reaches git.

This bakes all of that in. The output is a working skill, not a stub: run
forge_check.py on it immediately and it reports zero blocking issues.

    forge_new.py <name> --purpose "one line" --category <slug> [--scripts] [--force]

Exit: 0 created and verified, 1 created with problems, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def repo_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "registry.json").exists() and (cand / "skills").is_dir():
            return cand
    return start


def known_slugs(root: Path) -> list[str]:
    cfg = root / "skills" / "skill-validator" / "config" / "categories.yml"
    if not cfg.exists():
        return []
    data = yaml.safe_load(cfg.read_text())
    return sorted({c.get("slug") for c in data.get("categories", []) if c.get("slug")})


def build_description(name: str, purpose: str, triggers: list[str],
                      boundary: str, casual: list[str]) -> str:
    """The shape that actually triggers: what it is, when to use it, what it is
    NOT for, and the casual phrasings. Agents undertrigger; the last clause is
    the counterweight, and the boundary is what stops it poaching neighbours."""
    parts = [purpose.rstrip(".") + "."]
    if triggers:
        parts.append("Use when " + ", ".join(t.rstrip(".") for t in triggers) + ".")
    if boundary:
        parts.append("Not for " + boundary.rstrip(".") + ".")
    if casual:
        parts.append("Use even if the user only says "
                     + " or ".join(f"'{c}'" for c in casual) + ".")
    d = " ".join(parts).replace("<", "").replace(">", "")
    return re.sub(r"\s+", " ", d).strip()


BODY = """# {name} — {purpose_short}

Two or three paragraphs belong here: the problem this addresses, why the
obvious approach fails, and what this does instead. Do not restate the
description — an agent that reached this page has already read it.

## The loop

```
<the ordered steps, as a compact diagram or numbered list>
```

Each step should exist because skipping it causes a specific, nameable failure.
If you cannot name the failure, the step is ceremony and should go.

## Facts that prevent broken work

Each row is a real failure someone hit, not a generality. This is the highest
value section in the file; fill it from experience rather than imagination.

| Fact | Consequence |
|---|---|
| **The surprising thing.** | What breaks for someone who does not know it. |
| **The second surprising thing.** | What it costs when it goes wrong. |

## Orient

What to read or run before changing anything. Reading the project first is what
separates a change from a rewrite.

## Where to go next

Each reference is self-contained. Read the one you need, not all of them.

| Task | Reference |
|---|---|
| The deeper explanation of the first area | `references/getting-started.md` |
| The second area | `references/reference-two.md` |
| The third area | `references/reference-three.md` |

## Common mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | The thing everyone does first | What to do instead |

## Resources

- https://agentskills.io/specification.md
"""

REF_STUB = """# {title}

Self-contained depth for one area. An agent reads this file alone, so repeat
whatever context it needs rather than assuming the body is still in view.

## What this covers

Replace this section with the real material. Until it has content, this file is
scaffolding — the skill will validate, but it will not help anyone.

## Why it matters

Explain the reasoning, not just the rule. A reader who understands why will
generalise to cases you did not enumerate; one given a bare instruction cannot.
"""

SELFTEST = '''#!/usr/bin/env python3
"""Prove this skill's checks fire on bad input and stay quiet on good input.

A check that cannot fail its own negative case is a comment, not a check. Fill
this in as soon as scripts/ does anything real.
"""
import sys


def main() -> int:
    failures = []
    # Assert each check fires on a known-bad fixture and is silent on a good one.
    print("SELFTEST", "PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("name", nargs="?")
    ap.add_argument("--purpose", help="one line: what it does")
    ap.add_argument("--category", help="a real slug (see --list-categories)")
    ap.add_argument("--trigger", action="append", default=[],
                    help="a 'use when' situation (repeatable)")
    ap.add_argument("--boundary", default="",
                    help="what this is NOT for -- stops it poaching neighbours")
    ap.add_argument("--casual", action="append", default=[],
                    help="a casual phrasing that should still trigger it (repeatable)")
    ap.add_argument("--author", default="github.com/kryptobaseddev")
    ap.add_argument("--scripts", action="store_true", help="also scaffold scripts/ + selftest")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list-categories", action="store_true")
    a = ap.parse_args()

    root = repo_root(HERE)
    slugs = known_slugs(root)
    if a.list_categories:
        print("\n".join(slugs))
        return 0
    missing = [f"--{k}" for k in ("purpose", "category") if not getattr(a, k)]
    if not a.name:
        missing.insert(0, "name")
    if missing:
        print("required: " + ", ".join(missing), file=sys.stderr)
        return 2

    if not NAME_RE.match(a.name) or len(a.name) > 64 or "--" in a.name:
        print(f"invalid name {a.name!r}: must match {NAME_RE.pattern}, "
              "no consecutive hyphens, at most 64 chars", file=sys.stderr)
        return 2
    if slugs and a.category not in slugs:
        print(f"unknown category {a.category!r}. An unrecognised slug does NOT error -- "
              "it silently falls through to rule matching. Known slugs:\n  "
              + "\n  ".join(slugs), file=sys.stderr)
        return 2

    dest = root / "skills" / a.name
    if dest.exists() and not a.force:
        print(f"{dest} already exists (use --force)", file=sys.stderr)
        return 2

    desc = build_description(a.name, a.purpose, a.trigger, a.boundary, a.casual)
    if len(desc) < 50:
        print("description came out under 50 chars; give more --trigger/--casual detail",
              file=sys.stderr)
        return 2
    if len(desc) > 1024:
        print(f"description is {len(desc)} chars, over the 1024 hard limit; shorten "
              "--purpose or drop a trigger", file=sys.stderr)
        return 2

    (dest / "references").mkdir(parents=True, exist_ok=True)
    (dest / "evals").mkdir(exist_ok=True)

    fm = {
        "name": a.name,
        "description": desc,
        "license": "MIT",
        "metadata": {
            "author": a.author,
            "version": "1.0.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": a.category,
        },
        "allowed-tools": "Bash Read Write Edit Glob Grep",
    }
    # description must be a quoted single-line scalar; a folded one WARNs
    fm_text = (f"name: {a.name}\n"
               f"description: {json.dumps(desc)}\n"
               f"license: MIT\n"
               f"metadata:\n"
               f"  author: {a.author}\n"
               f'  version: "1.0.0"\n'
               f'  last_updated: "{fm["metadata"]["last_updated"]}"\n'
               f"  category: {a.category}\n"
               f"allowed-tools: Bash Read Write Edit Glob Grep\n")
    body = BODY.format(name=a.name, purpose_short=a.purpose.rstrip(".").lower())
    (dest / "SKILL.md").write_text(f"---\n{fm_text}---\n\n{body}")

    # three TOP-LEVEL reference files: the depth rule is non-recursive
    for fn, title in (("getting-started.md", "Getting started"),
                      ("reference-two.md", "The second area"),
                      ("reference-three.md", "The third area")):
        (dest / "references" / fn).write_text(REF_STUB.format(title=title))

    (dest / "evals" / "trigger_queries.json").write_text(json.dumps([
        {"query": f"a realistic prompt naming files and a stack that needs {a.name}",
         "should_trigger": True},
        {"query": f"a casual, lowercase phrasing of the same need", "should_trigger": True},
        {"query": "a third phrasing, formal this time, from someone who knows the domain",
         "should_trigger": True},
        # Negatives carry more information than positives: they are what stop a
        # skill poaching its neighbours. Make every one a genuine near-miss --
        # an obviously-irrelevant negative tests nothing at all.
        {"query": "a near-miss that shares vocabulary but needs a different skill",
         "should_trigger": False},
        {"query": "a second near-miss from an adjacent domain", "should_trigger": False},
        {"query": "a third near-miss a naive keyword match would catch",
         "should_trigger": False},
        {"query": "a request an adjacent skill in this repo should own instead",
         "should_trigger": False},
        {"query": "a request that mentions the same tool but is really a backend task",
         "should_trigger": False},
    ], indent=2) + "\n")
    (dest / "evals" / "evals.json").write_text(json.dumps({
        "skill_name": a.name,
        "description": f"Output evals for {a.name}. Use with skill-evaluator.",
        "evals": [],
    }, indent=2) + "\n")

    chmod_hint = []
    if a.scripts:
        (dest / "scripts").mkdir(exist_ok=True)
        (dest / "scripts" / "selftest.py").write_text(SELFTEST)
        (dest / "scripts" / "selftest.py").chmod(0o755)
        chmod_hint.append(f"skills/{a.name}/scripts/selftest.py")

    rel = dest.relative_to(root)
    print(f"created {rel}")
    print(f"  description  {len(desc)}/1024 chars")
    print(f"  category     {a.category} (explicit, so rule order cannot move it)")
    print(f"  references   3 top-level .md files (the depth rule is non-recursive)")
    print(f"  evals        trigger_queries.json + evals.json")
    print("\nnext:")
    print(f"  1. write the body of skills/{a.name}/SKILL.md and its references")
    print(f"  2. python3 scripts/build_registry.py          # README + registry are generated")
    if chmod_hint:
        print(f"  3. git add -A {rel} && git update-index --chmod=+x "
              + " ".join(chmod_hint))
        print("     (core.fileMode=false -- a local chmod never reaches git)")

    gate = subprocess.run([sys.executable, str(HERE / "forge_check.py"), str(dest)],
                          capture_output=True, text=True)
    print("\n" + gate.stdout.strip())
    blocking = [l for l in gate.stdout.splitlines() if l.startswith(" FAIL")]
    # a freshly scaffolded skill makes the generated files stale by definition
    real = [l for l in blocking if "generated files" not in l]
    return 0 if not real else 1


if __name__ == "__main__":
    sys.exit(main())
