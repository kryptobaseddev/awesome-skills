#!/usr/bin/env python3
"""Skill Validator config loader.

Loads the validator's effective configuration by walking the override
precedence chain and deep-merging user overrides onto the bundled defaults.

Precedence (highest wins):
    1. CLI flag             — explicit path passed to load_config()
    2. Skill-local override — <skill-dir>/.skill-validator.yml
    3. Project-level        — <project-root>/skill-validator.config.yml
    4. Bundled default      — <skill-validator>/config/default.yml

Project root is detected by walking up from the skill directory until a
.git, package.json, or pyproject.toml is found — or by stopping at $HOME.

The merge is recursive: a user override that sets `body.warn_lines: 600`
only changes that key; all sibling keys inherit from default.

The loader returns a plain dict; downstream code uses `cfg_get(cfg, dotted.path, default)`
to read keys without crashing on missing intermediate dicts.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:
    print("error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    raise


BUNDLED_DEFAULT = Path(__file__).resolve().parent.parent / "config" / "default.yml"
PROJECT_OVERRIDE_NAMES = ("skill-validator.config.yml", "skill-validator.config.yaml")
SKILL_OVERRIDE_NAMES = (".skill-validator.yml", ".skill-validator.yaml")


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise RuntimeError(f"YAML parse error in {path}: {e}") from e
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Lists are REPLACED, not merged —
    so a user that sets `frontmatter.required: [name]` gets exactly that
    list, not the union with default."""
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


_PROJECT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "skill-validator.config.yml",
    "skill-validator.config.yaml",
)


def _find_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    home = Path.home().resolve()
    for _ in range(10):
        if cur == home:
            return None
        if any((cur / m).exists() for m in _PROJECT_MARKERS):
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def _find_project_override(start: Path) -> Path | None:
    root = _find_project_root(start)
    if root is None:
        return None
    for name in PROJECT_OVERRIDE_NAMES:
        cand = root / name
        if cand.exists():
            return cand
    return None


def _find_skill_override(skill_dir: Path) -> Path | None:
    for name in SKILL_OVERRIDE_NAMES:
        cand = skill_dir / name
        if cand.exists():
            return cand
    return None


def load_config(*, skill_dir: Path | None = None, cli_path: str | None = None) -> dict:
    """Resolve effective config for a validation run.

    Args:
        skill_dir: the skill being validated (used to find skill-local and
                   project-level overrides). Pass None for repo-wide use.
        cli_path:  --config CLI override.

    Returns:
        Fully-merged config dict.
    """
    if not BUNDLED_DEFAULT.exists():
        raise FileNotFoundError(
            f"Bundled default config missing at {BUNDLED_DEFAULT}. "
            "skill-validator installation is incomplete."
        )
    cfg = _read_yaml(BUNDLED_DEFAULT)

    if skill_dir is not None:
        # Project override
        proj_path = _find_project_override(skill_dir)
        if proj_path is not None:
            cfg = _deep_merge(cfg, _read_yaml(proj_path))
        # Skill-local override
        skill_path = _find_skill_override(skill_dir)
        if skill_path is not None:
            cfg = _deep_merge(cfg, _read_yaml(skill_path))

    if cli_path:
        cli_p = Path(cli_path).expanduser().resolve()
        if not cli_p.exists():
            raise FileNotFoundError(f"--config file not found: {cli_p}")
        cfg = _deep_merge(cfg, _read_yaml(cli_p))

    return cfg


def cfg_get(cfg: dict, dotted: str, default: Any = None) -> Any:
    """Safely fetch `cfg['a']['b']['c']` via `cfg_get(cfg, 'a.b.c', default)`."""
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def cfg_severity(cfg: dict, dotted: str, default: str = "warn") -> str:
    """Resolve the severity for a rule. The rule's value can be:
      - a bare string like 'warn' / 'error' / 'off'
      - a dict with a 'severity' key
      - missing entirely (uses `default`)
    """
    node = cfg_get(cfg, dotted)
    if node is None:
        return default
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        sev = node.get("severity")
        if isinstance(sev, str):
            return sev
        return default
    return default


def cfg_enabled(cfg: dict, group: str, default: bool = True) -> bool:
    """A tier group is enabled unless explicitly `enabled: false`."""
    node = cfg_get(cfg, group)
    if not isinstance(node, dict):
        return default
    return node.get("enabled", default) is not False


def add_config_args(parser: argparse.ArgumentParser) -> None:
    """Attach the standard --config / --print-config flags."""
    parser.add_argument(
        "--config", default=None,
        help="path to a config YAML that overrides bundled default + project + skill-local",
    )
    parser.add_argument(
        "--print-config", action="store_true",
        help="print the fully-merged effective config and exit",
    )


def maybe_print_config(args: argparse.Namespace, cfg: dict) -> bool:
    """If --print-config was passed, print and return True. Caller exits."""
    if getattr(args, "print_config", False):
        yaml.safe_dump(cfg, sys.stdout, sort_keys=False, default_flow_style=False)
        return True
    return False


if __name__ == "__main__":
    # When invoked directly: print effective config for the cwd
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", default=None, help="skill directory (for skill-local override)")
    add_config_args(ap)
    args = ap.parse_args()
    skill_dir = Path(args.skill).resolve() if args.skill else Path.cwd()
    cfg = load_config(skill_dir=skill_dir, cli_path=args.config)
    yaml.safe_dump(cfg, sys.stdout, sort_keys=False, default_flow_style=False)
