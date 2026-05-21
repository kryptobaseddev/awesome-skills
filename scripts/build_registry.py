#!/usr/bin/env python3
"""Awesome Skills — registry + README builder.

Walks `skills/` at the repo root, reads each SKILL.md's frontmatter,
resolves a category for every skill, and produces:

  1. registry.json   — machine-readable list keyed by category
  2. README.md       — replaces the content between
                        <!-- SKILLS-START --> ... <!-- SKILLS-END -->
                        markers with an auto-generated categorized table

Category resolution order:
  1. Explicit override:  metadata.category in SKILL.md frontmatter
  2. Rule-based match:   first matching category in
                         skills/skill-validator/config/categories.yml
  3. Fallback:           the `fallback` block in that file

Run manually:
    python scripts/build_registry.py
    python scripts/build_registry.py --dry-run         # show changes only
    python scripts/build_registry.py --check           # exit 1 if README/registry stale

Designed to be safe to run repeatedly — idempotent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
README_PATH = REPO_ROOT / "README.md"
REGISTRY_PATH = REPO_ROOT / "registry.json"
CATEGORIES_PATH = SKILLS_DIR / "skill-validator" / "config" / "categories.yml"

SKILLS_START = "<!-- SKILLS-START -->"
SKILLS_END = "<!-- SKILLS-END -->"


def parse_skill_frontmatter(skill_md: Path) -> dict:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def load_categories() -> dict:
    if not CATEGORIES_PATH.exists():
        return {"categories": [], "fallback": {"name": "Other", "icon": "📦", "slug": "other"}}
    data = yaml.safe_load(CATEGORIES_PATH.read_text(encoding="utf-8")) or {}
    return data


def _haystack(name: str, frontmatter: dict) -> str:
    parts = [name, frontmatter.get("description", "") or ""]
    md = frontmatter.get("metadata") or {}
    if isinstance(md, dict):
        for k in ("tags", "related", "keywords"):
            v = md.get(k)
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(x) for x in v)
    return " ".join(parts).lower()


def _explicit_category(frontmatter: dict) -> str | None:
    md = frontmatter.get("metadata") or {}
    if isinstance(md, dict):
        cat = md.get("category")
        if isinstance(cat, str) and cat.strip():
            return cat.strip().lower()
    # top-level `category:` (some skills may use this)
    cat = frontmatter.get("category")
    if isinstance(cat, str) and cat.strip():
        return cat.strip().lower()
    return None


def _word_in(text: str, word: str) -> bool:
    """Word-boundary substring search — `orm` matches 'orm' but not 'platform'."""
    return re.search(r"(?:^|[^a-z0-9])" + re.escape(word.lower()) + r"(?:[^a-z0-9]|$)", text) is not None


def _match_category(name: str, frontmatter: dict, categories_doc: dict) -> dict:
    """Resolve a category dict for the skill (always returns one).

    Match precedence within a single category:
      1. tags overlap   (most specific — explicit author intent)
      2. name_contains  (substring in the skill's own name)
      3. keywords       (word-boundary match in name+description+tags)
    """
    explicit = _explicit_category(frontmatter)
    if explicit:
        for cat in categories_doc.get("categories", []):
            if cat.get("slug") == explicit or cat.get("name", "").lower() == explicit:
                return cat
    haystack = _haystack(name, frontmatter)
    skill_tags = []
    md = frontmatter.get("metadata") or {}
    if isinstance(md, dict):
        t = md.get("tags")
        if isinstance(t, str):
            skill_tags = [s.strip().lower() for s in t.split(",") if s.strip()]
        elif isinstance(t, list):
            skill_tags = [str(x).strip().lower() for x in t]
    name_lower = name.lower()

    for cat in categories_doc.get("categories", []):
        match = cat.get("match", {}) or {}
        # 1. tags — exact-match against author-declared tags
        cat_tags = [t.lower() for t in match.get("tags", [])]
        if any(t in skill_tags for t in cat_tags):
            return cat
        # 2. name_contains — substring in skill name
        name_contains = [n.lower() for n in match.get("name_contains", [])]
        if any(n in name_lower for n in name_contains):
            return cat
        # 3. keywords — word-boundary match in haystack
        keywords = [k.lower() for k in match.get("keywords", [])]
        if any(_word_in(haystack, k) for k in keywords):
            return cat

    return categories_doc.get("fallback", {"name": "Other", "icon": "📦", "slug": "other"})


def discover_skills() -> list[dict]:
    """Scan SKILLS_DIR and return enriched skill records."""
    cats = load_categories()
    skills: list[dict] = []
    if not SKILLS_DIR.is_dir():
        return skills
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        fm = parse_skill_frontmatter(skill_md)
        name = fm.get("name") or entry.name
        description = fm.get("description") or ""
        category = _match_category(name, fm, cats)
        skills.append({
            "name": name,
            "directory": entry.name,
            "path": f"skills/{entry.name}",
            "description": description.strip(),
            "category": {
                "slug": category.get("slug", "other"),
                "name": category.get("name", "Other"),
                "icon": category.get("icon", "📦"),
            },
            "metadata": fm.get("metadata") or {},
        })
    return skills


def build_registry(skills: list[dict]) -> dict:
    by_category: dict[str, dict] = {}
    for s in skills:
        slug = s["category"]["slug"]
        by_category.setdefault(slug, {
            "slug": slug,
            "name": s["category"]["name"],
            "icon": s["category"]["icon"],
            "skills": [],
        })["skills"].append({
            "name": s["name"],
            "path": s["path"],
            "description": s["description"],
            "metadata": s["metadata"],
        })
    # Preserve the categories.yml order
    cats_doc = load_categories()
    order: list[str] = [c.get("slug", "") for c in cats_doc.get("categories", [])]
    order.append(cats_doc.get("fallback", {}).get("slug", "other"))
    sorted_categories = [by_category[s] for s in order if s in by_category]
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_skills": len(skills),
        "total_categories": len(sorted_categories),
        "categories": sorted_categories,
    }


def render_skills_section(registry: dict) -> str:
    lines = []
    lines.append(SKILLS_START)
    lines.append("")
    lines.append(
        f"_{registry['total_skills']} skills across {registry['total_categories']} categories — "
        f"auto-generated from `skills/*/SKILL.md`. Last updated: {registry['generated_at']}._"
    )
    lines.append("")
    for cat in registry["categories"]:
        lines.append(f"### {cat['icon']} {cat['name']}")
        lines.append("")
        lines.append("| Skill | Description |")
        lines.append("|---|---|")
        for s in sorted(cat["skills"], key=lambda x: x["name"]):
            desc = s["description"].replace("\n", " ").replace("|", "\\|")
            if len(desc) > 200:
                desc = desc[:197] + "…"
            lines.append(f"| [`{s['name']}`]({s['path']}/) | {desc} |")
        lines.append("")
    lines.append(SKILLS_END)
    return "\n".join(lines)


def update_readme(registry: dict, *, dry_run: bool = False) -> tuple[bool, str]:
    """Replace the SKILLS-START/SKILLS-END block in README.md. Returns
    (changed, new_text)."""
    if not README_PATH.exists():
        raise FileNotFoundError(
            f"README.md not found at {README_PATH}. Create one with "
            f"'{SKILLS_START}' and '{SKILLS_END}' markers first."
        )
    text = README_PATH.read_text(encoding="utf-8")
    new_block = render_skills_section(registry)
    pattern = re.compile(
        re.escape(SKILLS_START) + r".*?" + re.escape(SKILLS_END),
        re.DOTALL,
    )
    if pattern.search(text):
        new_text = pattern.sub(new_block, text)
    else:
        # Marker block missing — append at end
        new_text = text.rstrip() + "\n\n" + new_block + "\n"
    changed = new_text != text
    if changed and not dry_run:
        README_PATH.write_text(new_text, encoding="utf-8")
    return changed, new_text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="show changes without writing files")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if README or registry would change")
    ap.add_argument("--json", action="store_true",
                    help="print the registry JSON to stdout")
    args = ap.parse_args()

    skills = discover_skills()
    if not skills:
        print(f"error: no skills with SKILL.md found under {SKILLS_DIR}", file=sys.stderr)
        return 1
    registry = build_registry(skills)

    # README
    readme_changed, new_readme = update_readme(registry, dry_run=args.dry_run or args.check)

    # registry.json
    new_registry_text = json.dumps(registry, indent=2) + "\n"
    existing_registry = REGISTRY_PATH.read_text(encoding="utf-8") if REGISTRY_PATH.exists() else ""
    registry_changed = (new_registry_text != existing_registry)
    if registry_changed and not (args.dry_run or args.check):
        REGISTRY_PATH.write_text(new_registry_text, encoding="utf-8")

    if args.json:
        sys.stdout.write(new_registry_text)
        return 0

    print(f"discovered {len(skills)} skill(s) across {registry['total_categories']} categor(ies)")
    for cat in registry["categories"]:
        print(f"  {cat['icon']} {cat['name']}: {len(cat['skills'])}")
    print()
    if args.check:
        if readme_changed or registry_changed:
            print("FAIL: README.md and/or registry.json are out of date — run "
                  "`python scripts/build_registry.py` to refresh.", file=sys.stderr)
            return 1
        print("OK: README.md and registry.json are up to date.")
        return 0
    if args.dry_run:
        if readme_changed:
            print("README.md would be updated.")
        if registry_changed:
            print("registry.json would be updated.")
        if not (readme_changed or registry_changed):
            print("No changes needed.")
        return 0
    if readme_changed:
        print(f"wrote {README_PATH.relative_to(REPO_ROOT)}")
    if registry_changed:
        print(f"wrote {REGISTRY_PATH.relative_to(REPO_ROOT)}")
    if not (readme_changed or registry_changed):
        print("No changes — README.md and registry.json already up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
