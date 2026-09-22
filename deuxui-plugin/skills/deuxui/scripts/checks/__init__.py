"""Check registry for the static tier.

Every check declares the detector ID it implements. scripts/lint_rules.py
refuses to pass if a detector is declared in references/rules/detectors.yaml
but not implemented here, or implemented here but not declared there. That
symmetry is what stops the report claiming coverage that does not exist.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ALL: dict[str, "Check"] = {}


@dataclass
class Finding:
    detector: str
    file: str
    line: int
    snippet: str
    fix: str
    confidence: str = "medium"


@dataclass
class Project:
    root: Path
    # Merged thresholds: references/rules/thresholds.yaml with the project's
    # overridable values applied. Checks read their numbers from here so a
    # project override actually reaches them.
    th: dict = field(default_factory=dict)
    threshold_overrides_refused: list = field(default_factory=list)
    # The declared visual contract (.deuxui/design.contract.yaml), with every
    # UNKNOWN stripped. Empty means nothing was declared, and the conformance
    # checks report NOT_RUN rather than PASS -- an undeclared system cannot be
    # conformed to, and saying otherwise would be the contract laundering its own
    # blanks into evidence.
    contract: dict = field(default_factory=dict)

    def num(self, group: str, key: str, default=None):
        """A threshold value, falling back to the literal the check was written
        with. Written as an accessor rather than direct indexing so a check still
        works when Project is constructed bare, as the fixtures do."""
        v = (self.th.get(group) or {}).get(key)
        return default if v is None else v
    deps: set = field(default_factory=set)
    has_tailwind: bool = False
    token_sources: list = field(default_factory=list)
    has_i18n: bool = False
    inventory: dict = field(default_factory=dict)   # component name -> path
    config: dict = field(default_factory=dict)
    css_text: str = ""
    cssvars: dict = field(default_factory=dict)   # --custom-property -> raw value
    has_container_queries: bool = False
    # Platforms this project actually ships to, measured from the tree rather
    # than declared: an ios/ or android/ directory, an Xcode or Gradle project,
    # a pubspec, or a react-native / expo dependency. The platform rule families
    # gate on this, so a web-only project reports them NOT_APPLICABLE instead of
    # carrying forty rows nobody can act on.
    platforms: set = field(default_factory=set)
    tailwind_major: int = 0    # 3 or 4; utilities changed meaning between them


@dataclass
class FileCtx:
    path: Path
    rel: str
    text: str
    ext: str
    tags: list = field(default_factory=list)
    surface: str = "ui"      # "ui" | "video" | "canvas3d" -- different rules apply
    css: str = ""            # CSS belonging to this file: the whole thing for a
                             # stylesheet, or its <style> blocks and styled
                             # template literals. Checks that read CSS rules must
                             # use this, or they silently skip every component
                             # that styles itself inline -- which is most of them.


@dataclass
class Check:
    id: str
    fn: Callable
    scope: str = "file"          # "file" | "project"
    exts: tuple = ()             # empty means all scanned extensions
    requires: Callable | None = None   # (Project) -> bool; False => NOT_RUN
    surfaces: tuple = ("ui",)          # which kind of surface this check is about


def check(detector_id, scope="file", exts=(), requires=None, surfaces=("ui",)):
    def deco(fn):
        ALL[detector_id] = Check(detector_id, fn, scope, exts, requires, surfaces)
        return fn
    return deco


def finding(detector, f, line, snippet, fix, confidence="medium"):
    snippet = " ".join(str(snippet).split())[:160]
    return Finding(detector, f.rel if hasattr(f, "rel") else str(f), line, snippet, fix, confidence)


# Importing the modules is what populates ALL.
from . import (a11y, forms, states, responsive, visual, content, designsystem,  # noqa: E402,F401
               ecosystem, safety, commitment, typography, craft, craftfloor, contract,  # noqa: E402,F401
               components, behavior, presentation, platform)  # noqa: E402,F401
