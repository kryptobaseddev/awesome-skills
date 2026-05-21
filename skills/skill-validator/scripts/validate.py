#!/usr/bin/env python3
"""Skill Validator — full compliance gauntlet, config-driven.

Validates a skill directory against the agentskills.io specification plus
any project- or skill-local rule overrides. Every threshold, regex, and
field list is loaded from `config/default.yml` (and overrides). See
`config/README.md` for the override precedence and rule catalogue.

Usage:
    validate.py <skill-directory>
    validate.py <skill-directory> --config /path/to/rules.yml
    validate.py <skill-directory> --manifest path/to/manifest.json
    validate.py <skill-directory> --json
    validate.py <skill-directory> --print-config

Exit codes:
    0 — PASS (no errors)
    1 — FAIL (one or more errors)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import (  # noqa: E402
    add_config_args,
    cfg_enabled,
    cfg_get,
    cfg_severity,
    load_config,
    maybe_print_config,
)


class Report:
    def __init__(self) -> None:
        self.results: list[tuple[int, str, str]] = []
        self.errors = 0
        self.warnings = 0

    def emit(self, tier: int, severity: str, msg: str) -> None:
        sev = severity.upper()
        if sev == "OFF":
            return
        if sev == "ERROR":
            self.errors += 1
        elif sev == "WARN":
            self.warnings += 1
        self.results.append((tier, sev, msg))

    def error(self, tier: int, msg: str) -> None:
        self.emit(tier, "ERROR", msg)

    def warn(self, tier: int, msg: str) -> None:
        self.emit(tier, "WARN", msg)

    def ok(self, tier: int, msg: str) -> None:
        self.emit(tier, "OK", msg)

    def has_error_matching(self, tier: int, substring: str) -> bool:
        return any(t == tier and s == "ERROR" and substring in m for t, s, m in self.results)


def validate_skill(skill_path: Path, cfg: dict, *, manifest_path: str | None = None,
                   dispatch_config_path: str | None = None,
                   provider_map_path: str | None = None) -> Report:
    skill_dir = Path(skill_path).resolve()
    skill_name = skill_dir.name
    r = Report()

    # ── Tier 1: Structure ──
    tier = 1
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        r.error(tier, "SKILL.md does not exist")
        return r
    r.ok(tier, "SKILL.md exists")

    raw_content = skill_md.read_text(encoding="utf-8")
    if not raw_content.startswith("---"):
        r.error(tier, "SKILL.md does not start with '---' (no frontmatter block)")
        return r
    r.ok(tier, "Content starts with '---'")

    fm_match = re.match(r"^---\n(.*?)\n---", raw_content, re.DOTALL)
    if not fm_match:
        r.error(tier, "Could not extract frontmatter (missing closing '---')")
        return r
    r.ok(tier, "Frontmatter block extracted")

    raw_fm = fm_match.group(1)
    try:
        frontmatter = yaml.safe_load(raw_fm)
    except yaml.YAMLError as e:
        r.error(tier, f"Frontmatter is not valid YAML: {e}")
        return r
    r.ok(tier, "Frontmatter is valid YAML")

    if not isinstance(frontmatter, dict):
        r.error(tier, "Frontmatter is not a dictionary (key: value pairs expected)")
        return r
    r.ok(tier, "Frontmatter is a dict")

    allowed_fields = set(cfg_get(cfg, "frontmatter.allowed", []) or [])
    required_fields = set(cfg_get(cfg, "frontmatter.required", []) or [])
    forbidden_fields = set(cfg_get(cfg, "frontmatter.forbidden", []) or [])
    unknown_severity = cfg_get(cfg, "frontmatter.unknown_severity", "warn")

    present_fields = set(frontmatter.keys())
    for f in sorted(forbidden_fields & present_fields):
        r.error(tier, f"Field '{f}' is forbidden at SKILL.md top level — move to manifest or metadata")
    for f in sorted(required_fields - present_fields):
        r.error(tier, f"Required field '{f}' is missing from frontmatter")
    unknown_fields = present_fields - allowed_fields - forbidden_fields
    if unknown_fields and unknown_severity.upper() != "OFF":
        for f in sorted(unknown_fields):
            r.emit(tier, unknown_severity, f"Unknown frontmatter field '{f}' (not in `frontmatter.allowed`)")
    if not (forbidden_fields & present_fields):
        r.ok(tier, "No forbidden fields in frontmatter")

    # ── Tier 2 ──
    tier = 2
    if cfg_enabled(cfg, "name"):
        _validate_name(r, tier, frontmatter, skill_name, cfg)
    if cfg_enabled(cfg, "description"):
        _validate_description(r, tier, frontmatter, raw_fm, cfg)
    if cfg_enabled(cfg, "compatibility"):
        _validate_compatibility(r, tier, frontmatter, cfg)
    if cfg_enabled(cfg, "metadata"):
        _validate_metadata(r, tier, frontmatter, cfg)
    if cfg_enabled(cfg, "booleans"):
        _validate_booleans(r, tier, frontmatter, cfg)
    if cfg_enabled(cfg, "allowed_tools"):
        at = frontmatter.get("allowed-tools")
        types = cfg_get(cfg, "allowed_tools.types", ["string", "list"])
        if at is not None:
            ok = (isinstance(at, str) and "string" in types) or (isinstance(at, list) and "list" in types)
            if not ok:
                r.error(tier, f"'allowed-tools' must be one of {types} (got {type(at).__name__})")
    if cfg_enabled(cfg, "argument_hint"):
        ah = frontmatter.get("argument-hint")
        max_len = cfg_get(cfg, "argument_hint.max_length", 100)
        if ah is not None:
            if not isinstance(ah, str):
                r.error(tier, "'argument-hint' must be a string")
            elif len(ah) > max_len:
                r.error(tier, f"'argument-hint' exceeds {max_len} characters (got: {len(ah)})")
    if cfg_enabled(cfg, "context"):
        ctx = frontmatter.get("context")
        if ctx is not None:
            allowed_values = cfg_get(cfg, "context.allowed_values", ["fork"])
            if ctx not in allowed_values:
                r.error(tier, f"'context' must be one of {allowed_values} (got: '{ctx}')")
            else:
                pair = cfg_get(cfg, "context.pair_with", "agent")
                pair_sev = cfg_get(cfg, "context.pair_severity", "warn")
                if pair and pair not in frontmatter and pair_sev.upper() != "OFF":
                    r.emit(tier, pair_sev, f"'context' is '{ctx}' but '{pair}' is not set")
                r.ok(tier, "'context' is valid")
    for field, expected in (("model", str), ("agent", str), ("hooks", dict)):
        val = frontmatter.get(field)
        if val is not None and not isinstance(val, expected):
            r.error(tier, f"'{field}' must be a {expected.__name__}")

    # ── Tier 3 ──
    if cfg_enabled(cfg, "body"):
        _validate_body(r, raw_content, skill_dir, cfg)

    # ── Tier 4 ──
    mf_path = manifest_path or cfg_get(cfg, "manifest.path")
    if mf_path or cfg_enabled(cfg, "manifest", default=False):
        _validate_manifest(r, frontmatter, skill_name, mf_path, dispatch_config_path, cfg)

    # ── Tier 5 ──
    pm_path = provider_map_path or cfg_get(cfg, "provider_compatibility.provider_map_path")
    if pm_path or cfg_enabled(cfg, "provider_compatibility", default=False):
        _validate_provider_map(r, skill_name, pm_path)

    return r


def _validate_name(r: Report, tier: int, fm: dict, skill_name: str, cfg: dict) -> None:
    name = fm.get("name")
    if not isinstance(name, str):
        if name is None:
            return
        r.error(tier, "'name' must be a string")
        return
    pattern = cfg_get(cfg, "name.pattern", r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
    if not re.match(pattern, name):
        r.error(tier, f"'name' must match {pattern} (got: '{name}')")
    if cfg_get(cfg, "name.reject_consecutive_hyphens", True) and "--" in name:
        r.error(tier, "'name' must not contain consecutive hyphens")
    max_len = cfg_get(cfg, "name.max_length", 64)
    if len(name) > max_len:
        r.error(tier, f"'name' exceeds {max_len} characters (got: {len(name)})")
    if name.startswith("-") or name.endswith("-"):
        r.error(tier, "'name' must not start or end with a hyphen")
    match_sev = cfg_severity(cfg, "name.must_match_directory", default="warn")
    if name != skill_name and match_sev.upper() != "OFF":
        r.emit(tier, match_sev, f"'name' field ('{name}') does not match directory name ('{skill_name}')")
    if not r.has_error_matching(tier, "'name'"):
        r.ok(tier, "'name' is valid")


def _validate_description(r: Report, tier: int, fm: dict, raw_fm: str, cfg: dict) -> None:
    desc = fm.get("description")
    if not isinstance(desc, str):
        if desc is None:
            return
        r.error(tier, "'description' must be a string")
        return
    for ch in cfg_get(cfg, "description.forbid_chars", []):
        if ch in desc:
            r.error(tier, f"'description' must not contain '{ch}' character(s)")
            break
    max_node = cfg_get(cfg, "description.max_length", {})
    max_v = max_node.get("value", 1024) if isinstance(max_node, dict) else max_node
    max_sev = max_node.get("severity", "error") if isinstance(max_node, dict) else "error"
    if len(desc) > max_v:
        r.emit(tier, max_sev, f"'description' exceeds {max_v} characters (got: {len(desc)})")
    min_node = cfg_get(cfg, "description.min_length", {})
    min_v = min_node.get("value", 50) if isinstance(min_node, dict) else min_node
    min_sev = min_node.get("severity", "warn") if isinstance(min_node, dict) else "warn"
    if len(desc) < min_v:
        r.emit(tier, min_sev, f"'description' is shorter than {min_v} characters (got: {len(desc)})")
    trig_node = cfg_get(cfg, "description.must_contain_trigger", {})
    if isinstance(trig_node, dict):
        trig_words = trig_node.get("trigger_words", ["when", "use when", "use for"])
        trig_sev = trig_node.get("severity", "warn")
        if trig_sev.upper() != "OFF" and not any(w in desc.lower() for w in trig_words):
            r.emit(tier, trig_sev, f"'description' should contain a trigger indicator (one of {trig_words})")
    fp_node = cfg_get(cfg, "description.not_first_person", {})
    if isinstance(fp_node, dict):
        fp_sev = fp_node.get("severity", "warn")
        if fp_sev.upper() != "OFF" and desc.startswith("I "):
            r.emit(tier, fp_sev, "'description' should not start with 'I ' (use third person)")
    ml_node = cfg_get(cfg, "description.reject_yaml_multiline", {})
    if isinstance(ml_node, dict):
        ml_sev = ml_node.get("severity", "warn")
        if ml_sev.upper() != "OFF" and ("description: >" in raw_fm or "description: |" in raw_fm):
            r.emit(tier, ml_sev, "'description' uses YAML multiline syntax (> or |) which can cause unexpected whitespace")
    if not r.has_error_matching(tier, "'description'"):
        r.ok(tier, "'description' is valid")


def _validate_compatibility(r: Report, tier: int, fm: dict, cfg: dict) -> None:
    val = fm.get("compatibility")
    if val is None:
        return
    expected_type = cfg_get(cfg, "compatibility.type", "string")
    sev = cfg_get(cfg, "compatibility.severity", "error")
    if expected_type == "string" and not isinstance(val, str):
        r.emit(tier, sev, "'compatibility' must be a string (per agentskills.io spec)")
        return
    max_len = cfg_get(cfg, "compatibility.max_length", 500)
    if isinstance(val, str) and len(val) > max_len:
        r.emit(tier, sev, f"'compatibility' exceeds {max_len} characters (got: {len(val)})")
        return
    r.ok(tier, "'compatibility' is valid")


def _validate_metadata(r: Report, tier: int, fm: dict, cfg: dict) -> None:
    md = fm.get("metadata")
    if md is None:
        return
    if not isinstance(md, dict):
        r.error(tier, "'metadata' must be a dict (map from string keys to string values)")
        return
    keys_sev = cfg_severity(cfg, "metadata.keys_must_be_strings", default="error")
    non_string_keys = [k for k in md if not isinstance(k, str)]
    if non_string_keys and keys_sev.upper() != "OFF":
        r.emit(tier, keys_sev, f"'metadata' keys must be strings (got: {non_string_keys[:3]})")
    vals_sev = cfg_severity(cfg, "metadata.values_must_be_strings", default="warn")
    non_string_vals = [k for k, v in md.items() if not isinstance(v, str)]
    if non_string_vals and vals_sev.upper() != "OFF":
        r.emit(tier, vals_sev,
               f"'metadata' values should be strings (non-string: {non_string_vals[:3]}); "
               f'quote numeric versions: "1.0" not 1.0')
    rec = cfg_get(cfg, "metadata.recommended_keys", {})
    if isinstance(rec, dict):
        rec_keys = set(rec.get("keys", []))
        rec_sev = rec.get("severity", "warn")
        present_rec = rec_keys & set(md.keys())
        if rec_keys and not present_rec and rec_sev.upper() != "OFF":
            r.emit(tier, rec_sev,
                   f"'metadata' present but contains none of the recommended keys "
                   f"({', '.join(sorted(rec_keys))}); consider adding for traceability")
        elif present_rec:
            r.ok(tier, f"'metadata' has recommended key(s): {', '.join(sorted(present_rec))}")
    ts_keys = cfg_get(cfg, "metadata.timestamp_keys", [])
    ts_pattern = cfg_get(cfg, "metadata.timestamp_pattern")
    ts_example = cfg_get(cfg, "metadata.timestamp_example", "")
    ts_sev = cfg_get(cfg, "metadata.timestamp_severity", "warn")
    if ts_pattern and ts_sev.upper() != "OFF":
        ts_re = re.compile(ts_pattern)
        for k in ts_keys:
            v = md.get(k)
            if v is None or not isinstance(v, str):
                continue
            if not ts_re.match(v):
                r.emit(tier, ts_sev,
                       f"'metadata.{k}' should match {ts_pattern} (got: {v!r}); use {ts_example!r}")
            else:
                r.ok(tier, f"'metadata.{k}' has valid timestamp format")
    custom_patterns = cfg_get(cfg, "metadata.patterns", {}) or {}
    for key, pattern in custom_patterns.items():
        v = md.get(key)
        if v is None or not isinstance(v, str):
            continue
        try:
            if not re.match(pattern, v):
                r.warn(tier, f"'metadata.{key}' should match {pattern} (got: {v!r})")
        except re.error as e:
            r.warn(tier, f"invalid regex in metadata.patterns.{key}: {e}")


def _validate_booleans(r: Report, tier: int, fm: dict, cfg: dict) -> None:
    for f in cfg_get(cfg, "booleans.fields", []):
        v = fm.get(f)
        if v is not None and not isinstance(v, bool):
            r.error(tier, f"'{f}' must be a boolean")
    for pair_spec in cfg_get(cfg, "booleans.contradictory_pairs", []) or []:
        if not isinstance(pair_spec, list):
            continue
        all_match = True
        details = []
        for clause in pair_spec:
            if not isinstance(clause, dict):
                all_match = False
                break
            for k, expected in clause.items():
                if fm.get(k) is not expected:
                    all_match = False
                    break
                details.append(f"{k}={expected}")
        if all_match:
            r.error(tier, f"Contradictory frontmatter: {' AND '.join(details)} (skill cannot be invoked)")


def _validate_body(r: Report, raw_content: str, skill_dir: Path, cfg: dict) -> None:
    tier = 3
    parts = raw_content.split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else ""
    if not body:
        r.warn(tier, "Body is empty (no content after frontmatter)")
        return
    r.ok(tier, "Body is present")
    body_lines = body.split("\n")
    line_count = len(body_lines)
    error_lines = cfg_get(cfg, "body.error_lines", 600)
    warn_lines = cfg_get(cfg, "body.warn_lines", 500)
    if line_count >= error_lines:
        r.error(tier, f"Body is too long: {line_count} lines (hard cap {error_lines})")
    elif line_count >= warn_lines:
        r.warn(tier, f"Body exceeds spec recommendation: {line_count} lines (keep under {warn_lines})")
    else:
        r.ok(tier, f"Body length OK ({line_count} lines)")
    placeholder_sev = cfg_get(cfg, "body.placeholder_severity", "warn")
    if placeholder_sev.upper() != "OFF":
        # Strip fenced blocks AND inline code spans — documentation that
        # mentions placeholder tokens in code formatting is not a placeholder.
        scan_text = re.sub(r"```[\s\S]*?```", "", body)
        scan_text = re.sub(r"`[^`\n]+`", "", scan_text)
        for pattern in cfg_get(cfg, "body.placeholder_patterns", []):
            matches = re.findall(pattern, scan_text)
            if matches:
                label = re.sub(r"[\\(?\[\])]", "", pattern).strip("\\b")
                r.emit(tier, placeholder_sev, f"Placeholder text found: '{label}' ({len(matches)} occurrence(s))")
    no_section_threshold = cfg_get(cfg, "body.warn_no_sections_above_lines", 200)
    if line_count > no_section_threshold:
        section_headers = re.findall(r"^## ", body, re.MULTILINE)
        if not section_headers:
            r.warn(tier, f"Body exceeds {no_section_threshold} lines but has no '## ' section headers")
        else:
            r.ok(tier, f"Body has {len(section_headers)} section header(s)")
    if cfg_get(cfg, "body.validate_file_references", True):
        ref_sev = cfg_get(cfg, "body.file_reference_severity", "warn")
        if ref_sev.upper() != "OFF":
            # Strip fenced blocks AND inline code spans. Docs that mention
            # paths in code formatting (`config/foo.json`) are illustrative
            # — not live references the validator should resolve.
            scan_body = re.sub(r"```[\s\S]*?```", "", body)
            scan_body = re.sub(r"`[^`\n]+`", "", scan_body)
            refs = re.findall(r"(?:references|scripts|config|assets)/[\w./-]+", scan_body)
            seen: set[str] = set()
            for ref in refs:
                if ref in seen:
                    continue
                seen.add(ref)
                escaped = re.escape(ref)
                if re.search(r"[/$]" + escaped, scan_body):
                    continue
                ref_line = next((l for l in scan_body.split("\n") if ref in l), "")
                if re.search(r"\b(examples?|e\.g\.|such as|like `|would be|illustrat)\b", ref_line, re.IGNORECASE):
                    continue
                if not (skill_dir / ref).exists():
                    r.emit(tier, ref_sev, f"Referenced file does not exist: {ref}")


def _validate_manifest(r: Report, fm: dict, skill_name: str, manifest_path: str | None,
                       dispatch_config_path: str | None, cfg: dict) -> None:
    tier = 4
    if not manifest_path:
        return
    mf = Path(manifest_path).expanduser().resolve()
    if not mf.exists():
        r.error(tier, f"Manifest file not found: {manifest_path}")
        return
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.error(tier, f"Manifest is not valid JSON: {e}")
        return
    name = fm.get("name", skill_name)
    skills = data.get("skills", [])
    match = next((s for s in skills if s.get("name") == name), None)
    if not match:
        r.warn(tier, f"Skill '{name}' not found in manifest.json skills[]")
        return
    r.ok(tier, f"Skill '{name}' found in manifest.json")
    for f in cfg_get(cfg, "manifest.required_entry_fields", ["name", "description", "path", "status"]):
        if f not in match:
            r.warn(tier, f"Manifest entry missing required field: '{f}'")
    if dispatch_config_path:
        dc = Path(dispatch_config_path).expanduser().resolve()
        if not dc.exists():
            r.error(tier, f"Dispatch config file not found: {dispatch_config_path}")
            return
        try:
            dcd = json.loads(dc.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            r.error(tier, f"Dispatch config is not valid JSON: {e}")
            return
        if name not in dcd.get("skill_overrides", {}):
            r.warn(tier, f"Skill '{name}' not found in dispatch-config.json skill_overrides")
        else:
            r.ok(tier, f"Skill '{name}' found in dispatch-config.json")


def _validate_provider_map(r: Report, skill_name: str, provider_map_path: str | None) -> None:
    tier = 5
    if not provider_map_path:
        return
    pm = Path(provider_map_path).expanduser().resolve()
    if not pm.exists():
        r.error(tier, f"Provider map file not found: {provider_map_path}")
        return
    try:
        data = json.loads(pm.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.error(tier, f"Provider map is not valid JSON: {e}")
        return
    if skill_name not in json.dumps(data):
        r.warn(tier, f"Skill '{skill_name}' not referenced in provider-skills-map.json")
    else:
        r.ok(tier, f"Skill '{skill_name}' found in provider-skills-map.json")


TIER_NAMES = {
    1: "Tier 1 — Structure",
    2: "Tier 2 — Frontmatter Quality",
    3: "Tier 3 — Body Quality",
    4: "Tier 4 — Manifest Integration",
    5: "Tier 5 — Provider Compatibility",
}


def _print_report(skill_name: str, r: Report) -> None:
    print(f"\n=== Skill Validator: {skill_name} ===\n")
    current_tier = None
    for tier_num, sev, msg in r.results:
        if tier_num != current_tier:
            current_tier = tier_num
            print(TIER_NAMES.get(tier_num, f"Tier {tier_num}"))
        if sev == "OK":
            print(f"  ✅ {msg}")
        elif sev == "ERROR":
            print(f"  ❌ ERROR: {msg}")
        elif sev == "WARN":
            print(f"  ⚠️  WARN: {msg}")
    print(f"\n=== SUMMARY ===")
    print(f"Errors:   {r.errors}")
    print(f"Warnings: {r.warnings}")
    if r.errors > 0:
        print("Result:   FAIL")
    elif r.warnings > 0:
        print("Result:   PASS (with warnings)")
    else:
        print("Result:   PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill Validator — agentskills.io compliance gauntlet")
    parser.add_argument("skill_dir", nargs="?", help="path to the skill directory")
    parser.add_argument("--manifest", help="path to manifest.json for Tier 4 check")
    parser.add_argument("--dispatch-config", help="path to dispatch-config.json")
    parser.add_argument("--provider-map", help="path to provider-skills-map.json")
    parser.add_argument("--json", action="store_true", help="output JSON instead of text")
    add_config_args(parser)
    args = parser.parse_args()

    skill_dir_arg = args.skill_dir
    skill_dir = Path(skill_dir_arg).resolve() if skill_dir_arg else Path.cwd()

    try:
        cfg = load_config(skill_dir=skill_dir if skill_dir_arg else None, cli_path=args.config)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if maybe_print_config(args, cfg):
        return 0

    if not skill_dir_arg:
        print("error: skill_dir is required (unless --print-config)", file=sys.stderr)
        return 2
    if not skill_dir.is_dir():
        print(f"error: '{skill_dir_arg}' is not a directory", file=sys.stderr)
        return 2

    r = validate_skill(
        skill_dir, cfg,
        manifest_path=args.manifest,
        dispatch_config_path=args.dispatch_config,
        provider_map_path=args.provider_map,
    )

    if args.json:
        out = {
            "skill_name": skill_dir.name,
            "results": [{"tier": t, "severity": s, "message": m} for t, s, m in r.results],
            "errors": r.errors,
            "warnings": r.warnings,
            "passed": r.errors == 0,
        }
        print(json.dumps(out, indent=2))
    else:
        _print_report(skill_dir.name, r)
    return 1 if r.errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
