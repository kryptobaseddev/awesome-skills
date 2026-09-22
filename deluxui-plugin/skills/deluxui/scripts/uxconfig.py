#!/usr/bin/env python3
"""The one place `.deluxui/ux.config.yaml` is read.

Every key this module exposes changes behaviour somewhere. That is the point of
it existing: a config key that is parsed, validated and then ignored is worse
than no key at all, because it tells someone they have configured something when
they have not. Each accessor below has a caller that acts on it, and
`selftest.py` asserts as much with positive controls.

Precedence is explicit-beats-implicit: a command-line flag overrides the file,
the file overrides `references/rules/thresholds.yaml`.

  python3 uxconfig.py --get app.dev_url [--config PATH] [--start DIR]

is the shell entry point, so `ux_browser.sh` reads the same file by the same
rules rather than growing a second parser.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
import yaml

REL = Path(".deluxui") / "ux.config.yaml"
THRESHOLDS = Path(__file__).resolve().parent.parent / "references" / "rules" / "thresholds.yaml"


def find(start: Path | None = None, explicit: str | None = None) -> Path | None:
    """Nearest .deluxui/ux.config.yaml at or above `start`."""
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    d = (start or Path.cwd()).resolve()
    if d.is_file():
        d = d.parent
    while True:
        if (d / REL).exists():
            return d / REL
        if d == d.parent:
            return None
        d = d.parent


def load(start: Path | None = None, explicit: str | None = None) -> dict:
    p = find(start, explicit)
    if not p:
        return {}
    try:
        cfg = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"deluxui: {p} is not valid YAML ({e}); ignoring it.\n")
        return {}
    if not isinstance(cfg, dict):
        sys.stderr.write(f"deluxui: {p} must be a mapping; ignoring it.\n")
        return {}
    cfg["_path"] = str(p)
    return cfg


# ------------------------------------------------------------------ thresholds
def thresholds(cfg: dict) -> tuple[dict, list[str]]:
    """Merged thresholds, plus the overrides that were refused.

    A STANDARD-derived value is not overridable. Refusing the override is the
    whole safeguard: if a project could lower the contrast minimum in config,
    every downstream PASS would be meaningless. A deviation is an exception
    record against a named rule, which is auditable -- not a number in a file."""
    import rulepack
    th = rulepack.load()[2]
    refused = []
    for group, vals in (cfg.get("thresholds") or {}).items():
        block = th.get(group)
        if block is None:
            refused.append(f"thresholds.{group}: no such threshold group")
            continue
        if not isinstance(vals, dict):
            refused.append(f"thresholds.{group}: expected a mapping of values")
            continue
        allowed = block.get("overridable")
        for k, v in vals.items():
            if k not in block:
                refused.append(f"thresholds.{group}.{k}: no such value")
            elif allowed is False:
                refused.append(f"thresholds.{group}.{k}: comes from a standard and "
                               "cannot be overridden; record an exception instead")
            elif isinstance(allowed, list) and k not in allowed:
                refused.append(f"thresholds.{group}.{k}: not overridable "
                               f"(this group allows {', '.join(allowed)})")
            else:
                block[k] = v
    return th, refused


# -------------------------------------------------------------------- the rest
def disabled(cfg: dict) -> set[str]:
    """Detector IDs the project has switched off. The rules they cover report
    NOT_RUN -- never PASS, which would be the config silencing a real finding."""
    v = cfg.get("disabled_checks") or []
    return set(v) if isinstance(v, (list, set, tuple)) else set()


def features(cfg: dict, extra=()) -> list[str]:
    """Declared product features, from config and --feature together. Rules
    gated on an undeclared feature report NOT_APPLICABLE."""
    v = cfg.get("features") or []
    got = list(v) if isinstance(v, (list, tuple)) else []
    for f in extra or ():
        if f not in got:
            got.append(f)
    return got


def excludes(cfg: dict) -> list[str]:
    """Extra path fragments to skip, beyond the built-in SKIP_DIRS."""
    v = cfg.get("exclude") or []
    return [str(x) for x in v] if isinstance(v, (list, tuple)) else []


def app(cfg: dict) -> dict:
    """Runtime-tier defaults. argv overrides each of these."""
    a = cfg.get("app") or {}
    if not isinstance(a, dict):
        return {}
    return {k: a.get(k) for k in ("dev_url", "routes", "api_pattern", "viewports")
            if a.get(k) is not None}


def get(cfg: dict, dotted: str):
    """`app.dev_url` -> value, for the shell entry point."""
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--get", metavar="DOTTED", help="print one value, empty if unset")
    ap.add_argument("--config", help="explicit config path")
    ap.add_argument("--start", help="directory to search upward from")
    ap.add_argument("--json", action="store_true", help="print the whole resolved config")
    a = ap.parse_args(argv)
    cfg = load(Path(a.start) if a.start else None, a.config)
    if a.json:
        th, refused = thresholds(cfg)
        print(json.dumps({"path": cfg.get("_path"), "features": features(cfg),
                          "disabled_checks": sorted(disabled(cfg)),
                          "exclude": excludes(cfg), "app": app(cfg),
                          "thresholds": th, "refused_overrides": refused}, indent=1))
        return 0
    if a.get:
        v = get(cfg, a.get)
        if v is None:
            return 0
        if isinstance(v, (list, tuple)):
            print(",".join(str(x) for x in v))
        else:
            print(v)
        return 0
    ap.print_help()
    return 1


CONTRACT_REL = Path(".deluxui") / "design.contract.yaml"


def find_contract(start: Path | None = None, explicit: str | None = None) -> Path | None:
    if explicit:
        q = Path(explicit)
        return q if q.exists() else None
    d = (start or Path.cwd()).resolve()
    if d.is_file():
        d = d.parent
    while True:
        if (d / CONTRACT_REL).exists():
            return d / CONTRACT_REL
        if d == d.parent:
            return None
        d = d.parent


def contract(start: Path | None = None, explicit: str | None = None) -> dict:
    """The declared visual commitments, or {}.

    Anything still `UNKNOWN` is stripped, so a half-filled contract checks only
    what it actually declares. A detector with nothing to compare against reports
    NOT_RUN -- never PASS, which would be the contract laundering its own blanks
    into evidence."""
    q = find_contract(start, explicit)
    if not q:
        return {}
    try:
        doc = yaml.safe_load(q.read_text()) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"deluxui: {q} is not valid YAML ({e}); ignoring it.\n")
        return {}
    if not isinstance(doc, dict):
        return {}

    out = clean_contract(doc)
    out["_path"] = str(q)
    return out


def clean_contract(doc: dict) -> dict:
    """Strip every `UNKNOWN` and empty branch from a contract document.

    Public because the identity of a contract is the identity of its DECLARED
    subset, and anything that needs to compute that -- the ledger archiving a
    version, a reader resolving an old `contract_sha` -- has to clean it exactly
    the way the loader does. A second copy of these four lines somewhere else is a
    ledger that silently stops matching the decisions it is supposed to explain."""

    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()
                    if x is not None and x != "UNKNOWN" and clean(x) != {}}
        if isinstance(v, list):
            return [x for x in v if x != "UNKNOWN"]
        return v

    return clean(doc if isinstance(doc, dict) else {})


if __name__ == "__main__":
    sys.exit(main())
