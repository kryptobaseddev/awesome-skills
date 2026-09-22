#!/usr/bin/env python3
"""The rule pack, loaded once and cached.

Parsing registry.yaml + detectors.yaml + thresholds.yaml costs ~128ms, and it is
paid on every invocation -- including every PostToolUse hook fire on every file
the agent writes. Re-serialised as JSON the same data parses in ~1ms, so the pack
is cached outside the skill directory and keyed by the source files' size and
mtime. Stale or unreadable cache just falls back to parsing the YAML, so the
cache can never be the reason a rule goes missing.

Deliberately NOT cached inside the skill: a plugin install copies the working
tree verbatim, and a committed cache would ship stale to consumers and be one
more generated artifact to keep honest.
"""
from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

RULES = Path(__file__).resolve().parent.parent / "references" / "rules"
FILES = ("registry.yaml", "detectors.yaml", "thresholds.yaml")
CACHE_VERSION = 1


def _stamp() -> str | None:
    """Identity of the current sources: path, size and mtime of each file."""
    parts = [str(CACHE_VERSION)]
    for name in FILES:
        p = RULES / name
        try:
            st = p.stat()
        except OSError:
            return None
        parts.append(f"{name}:{st.st_size}:{st.st_mtime_ns}")
    return "|".join(parts)


def _cache_path() -> Path:
    key = hashlib.sha256(str(RULES).encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"deuxui-rulepack-{key}.json"


def load() -> tuple[dict, dict, dict]:
    """(registry, detectors_document, thresholds). Detectors is the whole
    document, so callers keep reading `["detectors"]` and `["engines"]`."""
    stamp = _stamp()
    cache = _cache_path()
    if stamp:
        try:
            blob = json.loads(cache.read_text())
            if blob.get("stamp") == stamp:
                return blob["registry"], blob["detectors"], blob["thresholds"]
        except (OSError, ValueError, KeyError):
            pass

    import yaml                              # only needed on a cache miss
    reg = yaml.safe_load((RULES / "registry.yaml").read_text())
    det = yaml.safe_load((RULES / "detectors.yaml").read_text())
    th = yaml.safe_load((RULES / "thresholds.yaml").read_text())

    if stamp:
        try:
            tmp = cache.with_suffix(".%d.tmp" % os.getpid())
            tmp.write_text(json.dumps({"stamp": stamp, "registry": reg,
                                       "detectors": det, "thresholds": th}))
            os.replace(tmp, cache)           # atomic; concurrent runs cannot tear it
        except OSError:
            pass                             # read-only tmp is not an error
    return reg, det, th


def thresholds_only() -> dict:
    return load()[2]


if __name__ == "__main__":
    import time
    t = time.time(); load(); cold = time.time() - t
    t = time.time(); load(); warm = time.time() - t
    print(f"cache: {_cache_path()}")
    print(f"first load {cold*1000:.0f} ms   cached load {warm*1000:.0f} ms")
