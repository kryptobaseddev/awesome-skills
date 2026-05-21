"""Shared helpers for the skill-evaluator scripts.

Kept dependency-free (stdlib only) so scripts can import it without invoking uv
or pip. Scripts that need third-party deps declare them via PEP-723 inline
metadata at the top of the file.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("SKILL_EVAL_MODEL", "claude-opus-4-7")
DEFAULT_FAST_MODEL = os.environ.get("SKILL_EVAL_FAST_MODEL", "claude-sonnet-4-6")


# -- skill parsing -----------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
DESCRIPTION_RE = re.compile(
    r"^description:\s*(>?\s*\n(?:[ \t]+.+\n?)+|.+?)(?=^\w|^---|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class ParsedSkill:
    path: Path
    name: str
    description: str
    body: str
    frontmatter_raw: str
    sections: dict[str, str] = field(default_factory=dict)
    referenced_files: list[str] = field(default_factory=list)
    has_scripts: bool = False
    has_references: bool = False
    has_assets: bool = False

    @property
    def fingerprint(self) -> str:
        h = hashlib.sha256()
        h.update(self.frontmatter_raw.encode())
        h.update(self.body.encode())
        return h.hexdigest()[:16]


def parse_skill(skill_path: str | Path) -> ParsedSkill:
    skill_path = Path(skill_path).expanduser().resolve()
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_md}")
    raw = skill_md.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(raw)
    if not m:
        raise ValueError(f"SKILL.md at {skill_md} has no YAML frontmatter")
    fm, body = m.group(1), m.group(2)
    name_m = NAME_RE.search(fm)
    desc_m = DESCRIPTION_RE.search(fm)
    name = (name_m.group(1).strip() if name_m else skill_path.name).strip().strip('"').strip("'")
    description = _clean_description(desc_m.group(1) if desc_m else "")
    sections = _split_sections(body)
    referenced = _find_referenced_files(body, skill_path)
    return ParsedSkill(
        path=skill_path,
        name=name,
        description=description,
        body=body,
        frontmatter_raw=fm,
        sections=sections,
        referenced_files=referenced,
        has_scripts=(skill_path / "scripts").is_dir(),
        has_references=(skill_path / "references").is_dir(),
        has_assets=(skill_path / "assets").is_dir(),
    )


def _clean_description(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith(">"):
        # YAML folded scalar — drop the marker and collapse whitespace
        raw = raw[1:].strip()
    # Collapse runs of whitespace including newlines
    return re.sub(r"\s+", " ", raw).strip().strip('"').strip("'")


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading = "_preamble"
    current: list[str] = []
    for line in body.splitlines():
        h = re.match(r"^(#{1,6})\s+(.+)$", line)
        if h:
            if current:
                sections[current_heading] = "\n".join(current).strip()
            current_heading = h.group(2).strip().lower()
            current = []
        else:
            current.append(line)
    if current:
        sections[current_heading] = "\n".join(current).strip()
    return sections


def _find_referenced_files(body: str, skill_path: Path) -> list[str]:
    pattern = re.compile(r"(?:references|scripts|assets)/[A-Za-z0-9_./\-]+")
    out: set[str] = set()
    for m in pattern.finditer(body):
        rel = m.group(0)
        if (skill_path / rel).exists():
            out.add(rel)
    return sorted(out)


# -- workspace layout --------------------------------------------------------


def workspace_for(skill_path: Path, override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    parent = skill_path.parent
    return parent / f"{skill_path.name}-workspace"


def iteration_dir(workspace: Path, iteration: int) -> Path:
    return workspace / f"iteration-{iteration}"


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen]).strip("-") or "case"


# -- I/O helpers -------------------------------------------------------------


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# -- statistics --------------------------------------------------------------


def mean_stddev(xs: Iterable[float]) -> dict[str, float]:
    xs = list(xs)
    if not xs:
        return {"mean": 0.0, "stddev": 0.0, "n": 0}
    if len(xs) == 1:
        return {"mean": float(xs[0]), "stddev": 0.0, "n": 1}
    return {
        "mean": float(statistics.fmean(xs)),
        "stddev": float(statistics.pstdev(xs)),
        "n": len(xs),
    }


# -- Anthropic API -----------------------------------------------------------


class LLMUnavailable(RuntimeError):
    pass


def have_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def have_claude_cli() -> bool:
    return subprocess.run(
        ["which", "claude"], capture_output=True, text=True
    ).returncode == 0


def call_anthropic(
    *,
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 4096,
    response_format: str = "text",
) -> dict[str, Any]:
    """Call the Anthropic API. Returns {'text': str, 'usage': {...}}.

    Raises LLMUnavailable if neither ANTHROPIC_API_KEY nor claude CLI is set.
    Prefer this over `claude -p` for deterministic eval grading.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback to claude CLI if available
        if have_claude_cli():
            return _claude_cli_call(system=system, user=user, model=model)
        raise LLMUnavailable(
            "Set ANTHROPIC_API_KEY or install the `claude` CLI to enable LLM calls."
        )

    payload = {
        "model": model or DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise LLMUnavailable(f"Anthropic API error {e.code}: {body}") from e
    duration_ms = int((time.time() - started) * 1000)
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    usage = data.get("usage", {})
    return {
        "text": text,
        "usage": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "duration_ms": duration_ms,
        },
    }


def _claude_cli_call(*, system: str, user: str, model: str | None = None) -> dict[str, Any]:
    cmd = ["claude", "-p", "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    full_prompt = f"<system>\n{system}\n</system>\n\n{user}"
    started = time.time()
    proc = subprocess.run(
        cmd, input=full_prompt, capture_output=True, text=True, timeout=300
    )
    duration_ms = int((time.time() - started) * 1000)
    if proc.returncode != 0:
        raise LLMUnavailable(f"claude CLI failed: {proc.stderr[:500]}")
    try:
        data = json.loads(proc.stdout)
        text = data.get("result", proc.stdout)
        usage = data.get("usage", {})
    except json.JSONDecodeError:
        text = proc.stdout
        usage = {}
    return {
        "text": text,
        "usage": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "duration_ms": duration_ms,
        },
    }


def extract_json_block(text: str) -> Any:
    """Extract the first ```json ... ``` block, or fall back to first {...} or [...]."""
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Try a top-level object or array
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start < 0:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : i + 1])
    raise ValueError("No JSON block found in LLM response")


# -- error helpers -----------------------------------------------------------


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)
