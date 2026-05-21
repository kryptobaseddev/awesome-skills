#!/usr/bin/env python3
"""
CLEO Skill Depth Check — progressive-disclosure-depth rule (T9684).

Fails when a skill's SKILL.md is below the depth threshold AND it has
no references/ subdir with at least the manifest-declared reference
files. The gold standard is ct-orchestrator (9 references) and
ct-skill-creator (7 references); the rule is calibrated to flag
stubs without forcing every skill to that depth.

Rule logic:
  PASS when ANY of:
    - SKILL.md body has >= MIN_BODY_LINES content lines
    - references/ subdir exists with >= MIN_REF_FILES files
    - manifest.json references[] array populated with file paths that
      all exist on disk

  FAIL when:
    - SKILL.md body < MIN_BODY_LINES lines AND
    - references/ missing or has < MIN_REF_FILES files AND
    - manifest.json references[] empty or files missing

Error message points at the gold standard and lists expected files
from the manifest entry (when present) so the fix is obvious.

Usage:
    check_depth.py <skill-directory>
    check_depth.py <skill-directory> --manifest path/to/manifest.json
    check_depth.py <skill-directory> --all                  # walk all skills under a root
    check_depth.py <skill-directory> --json
"""
import sys
import re
import json
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import add_config_args, cfg_get, load_config, maybe_print_config  # noqa: E402


# Defaults if config is missing or doesn't override them.
DEFAULT_MIN_BODY_LINES = 100
DEFAULT_MIN_REF_FILES = 3
DEFAULT_REF_EXTENSIONS = (".md",)
DEFAULT_STALE_DAYS = 30
DEFAULT_TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
LAST_REVIEWED_RE = re.compile(r"last_reviewed:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

# Allowlist — pre-existing stub skills exempted at T9567 (E-SKILLS-DEPTH-BACKFILL).
# Each entry MUST have a follow-up task ID. Remove the entry once that task
# lands a depth backfill. New entries require owner approval — do not add
# silently.
#
# Default empty allowlist. Projects opt in via config:
#   depth:
#     allowlist:
#       my-stub-skill: "TICKET-123: rationale | last_reviewed: 2026-05-21 14:00:18"
#
# AUDIT CADENCE: every entry MUST carry `last_reviewed: YYYY-MM-DD HH:MM:SS`.
# Entries older than `depth.allowlist_stale_days` (default 30) emit a WARN.
ALLOWLIST: dict[str, str] = {}


def count_body_lines(skill_md_path: Path) -> int:
    """Count content lines in the SKILL.md body (excluding frontmatter)."""
    if not skill_md_path.exists():
        return 0
    raw = skill_md_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        # No frontmatter — count whole file
        return len(raw.split("\n"))
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return 0
    body = parts[2].strip()
    if not body:
        return 0
    return len(body.split("\n"))


def manifest_references_for(skill_name: str, manifest_path: Path) -> list[str]:
    """Return the references array from manifest.json for the given skill,
    or empty list if not present."""
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    for entry in data.get("skills", []):
        if entry.get("name") == skill_name:
            return entry.get("references", []) or []
    return []


def repo_root_of(skill_dir: Path) -> Path:
    """Walk up from skill_dir to the repo root (heuristic: contains
    `packages/skills/skills/manifest.json`)."""
    cur = skill_dir.resolve()
    for _ in range(10):
        if (cur / "packages" / "skills" / "skills" / "manifest.json").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return skill_dir  # fallback


def check_depth(skill_path: Path, manifest_path: Path | None = None,
                cfg: dict | None = None) -> tuple[bool, dict]:
    """Run the depth check on a single skill directory.

    Args:
        skill_path:     Skill directory.
        manifest_path:  Optional manifest.json (for the manifest-references threshold).
        cfg:            Loaded config. If None, uses module defaults.

    Returns:
        (passed, report_dict).
    """
    cfg = cfg or {}
    min_body = int(cfg_get(cfg, "depth.min_body_lines", DEFAULT_MIN_BODY_LINES))
    min_refs = int(cfg_get(cfg, "depth.min_reference_files", DEFAULT_MIN_REF_FILES))
    ref_exts = tuple(cfg_get(cfg, "depth.reference_extensions", list(DEFAULT_REF_EXTENSIONS)))
    allowlist = cfg_get(cfg, "depth.allowlist", ALLOWLIST) or {}

    skill_dir = Path(skill_path).resolve()
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    refs_dir = skill_dir / "references"

    report: dict = {
        "skill_name": skill_name,
        "path": str(skill_dir),
        "body_lines": 0,
        "ref_files_on_disk": 0,
        "manifest_references": [],
        "manifest_references_missing": [],
        "thresholds": {
            "min_body_lines": min_body,
            "min_ref_files": min_refs,
        },
        "passed": False,
        "reasons": [],
        "remediation": [],
    }

    body_lines = count_body_lines(skill_md)
    report["body_lines"] = body_lines
    body_passes = body_lines >= min_body

    ref_files_on_disk = 0
    if refs_dir.is_dir():
        ref_files_on_disk = len([p for p in refs_dir.iterdir() if p.is_file() and p.suffix in ref_exts])
    report["ref_files_on_disk"] = ref_files_on_disk
    refs_dir_passes = ref_files_on_disk >= min_refs

    manifest_passes = False
    if manifest_path is None:
        # Auto-locate from repo root (legacy CLEO layout; harmless if not present)
        root = repo_root_of(skill_dir)
        manifest_path = root / "packages" / "skills" / "skills" / "manifest.json"

    if manifest_path.exists():
        manifest_refs = manifest_references_for(skill_name, manifest_path)
        report["manifest_references"] = manifest_refs
        if manifest_refs:
            root = repo_root_of(skill_dir)
            base = root / "packages" / "skills"
            missing = []
            for rel in manifest_refs:
                ref_abs = base / rel
                if not ref_abs.exists():
                    fallback = skill_dir / Path(rel).relative_to(Path(rel).parts[0]) \
                        if Path(rel).parts else None
                    if fallback is None or not fallback.exists():
                        missing.append(rel)
            report["manifest_references_missing"] = missing
            manifest_passes = (len(manifest_refs) >= min_refs and not missing)

    passed = body_passes or refs_dir_passes or manifest_passes
    report["passed"] = passed

    if body_passes:
        report["reasons"].append(f"body_lines={body_lines} >= {min_body}")
    if refs_dir_passes:
        report["reasons"].append(f"references/ has {ref_files_on_disk} files >= {min_refs}")
    if manifest_passes:
        report["reasons"].append(
            f"manifest references[] populated with {len(report['manifest_references'])} files (all on disk)"
        )

    if not passed and skill_name in allowlist:
        passed = True
        report["passed"] = True
        report["allowlisted"] = True
        report["allowlist_reason"] = allowlist[skill_name]
        report["reasons"].append(f"allowlisted: {allowlist[skill_name]}")

    if not passed:
        report["reasons"].append("none of the three thresholds met")
        report["remediation"] = [
            f"Expand SKILL.md body to >= {min_body} content lines (currently {body_lines}), OR",
            f"Add references/ subdir with >= {min_refs} markdown files (currently {ref_files_on_disk}), OR",
            "Populate manifest.json references[] array for this skill with file paths.",
        ]
        if report["manifest_references_missing"]:
            report["remediation"].append(
                "Manifest references[] lists files that do not exist on disk: "
                + ", ".join(report["manifest_references_missing"])
            )

    return passed, report


def _print_report(report: dict, cfg: dict | None = None) -> None:
    cfg = cfg or {}
    min_body = int(cfg_get(cfg, "depth.min_body_lines", DEFAULT_MIN_BODY_LINES))
    min_refs = int(cfg_get(cfg, "depth.min_reference_files", DEFAULT_MIN_REF_FILES))
    name = report["skill_name"]
    status = "PASS" if report["passed"] else "FAIL"
    icon = "✅" if report["passed"] else "❌"
    print(f"\n{icon} {status}  {name}")
    print(f"     body_lines={report['body_lines']} (min {min_body})")
    print(f"     ref_files_on_disk={report['ref_files_on_disk']} (min {min_refs})")
    print(f"     manifest_references={len(report['manifest_references'])} files")
    if report["manifest_references_missing"]:
        print(f"     manifest_references_missing={report['manifest_references_missing']}")
    for r in report["reasons"]:
        print(f"     - {r}")
    if not report["passed"]:
        print("     remediation:")
        for r in report["remediation"]:
            print(f"       * {r}")


def audit_allowlist(
    *,
    now: datetime.datetime | None = None,
    stale_days: int | None = None,
    allowlist: dict | None = None,
) -> list[dict]:
    """Audit the allowlist for malformed or stale `last_reviewed` stamps.

    Args:
        now:        Override for the current time (testing).
        stale_days: Override cadence threshold.
        allowlist:  Override the allowlist dict (defaults to module ALLOWLIST).

    Returns:
        List of finding dicts (`skill`, `severity`, `message`, optional `age_days`).
        Empty list = every entry is well-formed and fresh.
    """
    now = now or datetime.datetime.now()
    if stale_days is None:
        stale_days = DEFAULT_STALE_DAYS
    if allowlist is None:
        allowlist = ALLOWLIST
    findings: list[dict] = []
    for skill, rationale in allowlist.items():
        m = LAST_REVIEWED_RE.search(rationale)
        if not m:
            findings.append({
                "skill": skill, "severity": "WARN",
                "message": "missing or malformed 'last_reviewed: YYYY-MM-DD HH:MM:SS' stamp",
            })
            continue
        stamp = m.group(1)
        try:
            ts = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            findings.append({
                "skill": skill, "severity": "WARN",
                "message": f"invalid timestamp '{stamp}': {e}",
            })
            continue
        age_days = (now - ts).days
        if age_days > stale_days:
            findings.append({
                "skill": skill, "severity": "WARN", "age_days": age_days,
                "message": (
                    f"stale: last_reviewed was {age_days}d ago "
                    f"(cadence: {stale_days}d). Audit and bump the stamp."
                ),
            })
    return findings


def _print_allowlist_audit(findings: list[dict], *, stream=sys.stderr) -> None:
    if not findings:
        return
    print("=== allowlist audit ===", file=stream)
    for f in findings:
        print(f"  ⚠️  {f['skill']}: {f['message']}", file=stream)
    print(file=stream)


def walk_all_skills(root: Path) -> list[Path]:
    """Find all skill directories under packages/skills/skills/.
    Skips manifest.json, _shared/, and any dir without SKILL.md."""
    base = root if (root / "SKILL.md").exists() else (root / "packages" / "skills" / "skills")
    if not base.is_dir():
        return []
    skills = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_") or entry.name.startswith("."):
            continue
        if (entry / "SKILL.md").exists():
            skills.append(entry)
    return skills


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skill depth check — progressive-disclosure rule"
    )
    parser.add_argument("skill_dir", help="Path to the skill directory (or repo root if --all)")
    parser.add_argument("--manifest", help="Path to manifest.json (auto-located if omitted)")
    parser.add_argument(
        "--all", action="store_true",
        help="Walk every skill under the given directory (looks for SKILL.md children)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument(
        "--audit-allowlist", action="store_true",
        help=(
            "Audit allowlist entries for malformed or stale `last_reviewed` "
            "stamps and exit. Exits 1 if any finding is reported."
        ),
    )
    add_config_args(parser)
    args = parser.parse_args()

    arg_path = Path(args.skill_dir).resolve()
    skill_dir_for_cfg = arg_path if (arg_path / "SKILL.md").exists() else None
    try:
        cfg = load_config(skill_dir=skill_dir_for_cfg, cli_path=args.config)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if maybe_print_config(args, cfg):
        return 0

    allowlist = cfg_get(cfg, "depth.allowlist", ALLOWLIST) or {}
    stale_days = int(cfg_get(cfg, "depth.allowlist_stale_days", DEFAULT_STALE_DAYS))

    # Standalone audit mode — for CI / cron use.
    if args.audit_allowlist:
        findings = audit_allowlist(stale_days=stale_days, allowlist=allowlist)
        if args.json:
            print(json.dumps({
                "stale_days_cadence": stale_days,
                "findings": findings,
                "passed": len(findings) == 0,
            }, indent=2))
        else:
            if findings:
                _print_allowlist_audit(findings, stream=sys.stdout)
                print(f"=== SUMMARY ===\nFindings: {len(findings)}\nResult: FAIL",
                      file=sys.stdout)
            else:
                print("=== allowlist audit ===", file=sys.stdout)
                print(f"  ✅ all {len(allowlist)} entries have fresh stamps "
                      f"(cadence: {stale_days}d)", file=sys.stdout)
                print(f"\n=== SUMMARY ===\nFindings: 0\nResult: PASS",
                      file=sys.stdout)
        return 1 if findings else 0

    # Background audit — runs on every invocation, silent when clean, emits
    # to stderr so --json output on stdout stays parseable.
    if not args.json:
        _print_allowlist_audit(audit_allowlist(stale_days=stale_days, allowlist=allowlist))

    manifest = Path(args.manifest).resolve() if args.manifest else None

    if args.all:
        skills = walk_all_skills(arg_path)
        if not skills:
            print(f"Error: no skill directories found under {arg_path}", file=sys.stderr)
            return 1
        all_reports = []
        total_fail = 0
        for s in skills:
            passed, report = check_depth(s, manifest, cfg=cfg)
            all_reports.append(report)
            if not passed:
                total_fail += 1
        if args.json:
            print(json.dumps({
                "summary": {
                    "total": len(all_reports),
                    "passed": len(all_reports) - total_fail,
                    "failed": total_fail,
                    "thresholds": {
                        "min_body_lines": int(cfg_get(cfg, "depth.min_body_lines", DEFAULT_MIN_BODY_LINES)),
                        "min_ref_files": int(cfg_get(cfg, "depth.min_reference_files", DEFAULT_MIN_REF_FILES)),
                    },
                },
                "skills": all_reports,
            }, indent=2))
        else:
            print(f"=== Skill Depth Check (all skills under {arg_path}) ===")
            for r in all_reports:
                _print_report(r, cfg=cfg)
            print(f"\n=== SUMMARY ===")
            print(f"Total skills: {len(all_reports)}")
            print(f"Passed: {len(all_reports) - total_fail}")
            print(f"Failed: {total_fail}")
        return 1 if total_fail > 0 else 0

    # Single-skill mode
    if not arg_path.is_dir():
        print(f"Error: '{args.skill_dir}' is not a directory", file=sys.stderr)
        return 1
    if not (arg_path / "SKILL.md").exists():
        print(f"Error: '{args.skill_dir}' has no SKILL.md", file=sys.stderr)
        return 1

    passed, report = check_depth(arg_path, manifest, cfg=cfg)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report, cfg=cfg)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
