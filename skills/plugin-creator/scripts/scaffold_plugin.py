#!/usr/bin/env python3
"""
scaffold_plugin.py — generate a complete, ready-to-run Claude Code plugin +
marketplace whose only component is an MCP server that surfaces skills/agents on
demand. Output is immediately installable and passes `claude plugin validate`.

Example:
    python scaffold_plugin.py --name acme-tools \
        --description "Acme's internal design + data capabilities, on demand." \
        --owner acme --dest /mnt/projects/acme-tools --lang node --force

Produces:
    <dest>/<marketplace>/
      .claude-plugin/marketplace.json
      plugins/<name>/
        .claude-plugin/plugin.json
        .mcp.json
        mcp/server.(mjs|py)
        registry/skills/example-skill/SKILL.md
        registry/agents/example-agent.md
        README.md  .gitignore

Then: smoke-test the server, `claude plugin validate`, install, fill the registry.
Standard library only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
# Anthropic's plugin name rule: lowercase, must start with a letter, kebab-case.
KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def die(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def title_case(name: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_]", name))


def substitute(text: str, repl: dict) -> str:
    for k, v in repl.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def write(path: Path, text: str, force: bool):
    if path.exists() and not force:
        die(f"{path} exists (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  + {path}")


def _prune_empty(o):
    """Drop optional fields left empty (e.g. homepage="") — the validator
    rejects empty strings where it expects a URL."""
    if isinstance(o, dict):
        return {k: _prune_empty(v) for k, v in o.items()
                if not (isinstance(v, str) and v.strip() == "")}
    if isinstance(o, list):
        return [_prune_empty(x) for x in o]
    return o


def write_json(path: Path, text: str, force: bool):
    """Substituted JSON: parse, prune empty optionals, re-emit tidy."""
    import json as _json
    obj = _prune_empty(_json.loads(text))
    write(path, _json.dumps(obj, indent=2) + "\n", force)


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold an MCP-registry Claude Code plugin.")
    ap.add_argument("--name", required=True, help="plugin name (kebab-case)")
    ap.add_argument("--marketplace", help="marketplace name (default <name>-marketplace)")
    ap.add_argument("--server-name", help="MCP server name (default <name>)")
    ap.add_argument("--display-name", help="human display name (default Title Case)")
    ap.add_argument("--description", default="", help="plugin description (the 'when to use' matters)")
    ap.add_argument("--owner", default="your-org")
    ap.add_argument("--homepage", default="")
    ap.add_argument("--license", default="MIT")
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--lang", choices=["node", "python"], default="node")
    ap.add_argument("--dest", default=".", help="directory to create the marketplace in")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    if not KEBAB.match(args.name):
        die(f"--name must be kebab-case (got '{args.name}')")
    marketplace = args.marketplace or f"{args.name}-marketplace"
    if not KEBAB.match(marketplace):
        die(f"marketplace name must be kebab-case (got '{marketplace}')")
    server_name = args.server_name or args.name
    display = args.display_name or title_case(args.name)
    description = args.description or f"{display}: project capabilities surfaced to your coding agent on demand over MCP."
    env_prefix = re.sub(r"[^A-Z0-9]", "_", server_name.upper())
    runtime = "node" if args.lang == "node" else "python3"
    server_entry = "mcp/server.mjs" if args.lang == "node" else "mcp/server.py"

    repl = {
        "PLUGIN_NAME": args.name,
        "MARKETPLACE_NAME": marketplace,
        "SERVER_NAME": server_name,
        "DISPLAY_NAME": display,
        "DESCRIPTION": description,
        "MARKETPLACE_DESCRIPTION": f"Marketplace for {display}.",
        "OWNER": args.owner,
        "HOMEPAGE": args.homepage,
        "LICENSE": args.license,
        "VERSION": args.version,
        "RUNTIME": runtime,
        "SERVER_ENTRY": server_entry,
        "ENV_PREFIX": env_prefix,
    }

    root = Path(args.dest).resolve() / marketplace
    plugin_dir = root / "plugins" / args.name
    common = TEMPLATES / "common"
    lang_dir = TEMPLATES / args.lang

    print(f"Scaffolding '{args.name}' ({args.lang}) into {root}")

    # marketplace + plugin manifests (write_json prunes empty optionals like homepage="")
    write_json(root / ".claude-plugin" / "marketplace.json",
               substitute((common / "marketplace.json").read_text(), repl), args.force)
    write_json(plugin_dir / ".claude-plugin" / "plugin.json",
               substitute((common / "plugin.json").read_text(), repl), args.force)
    write(plugin_dir / ".mcp.json",
          substitute((common / ".mcp.json").read_text(), repl), args.force)
    write(plugin_dir / "README.md",
          substitute((common / "README.md").read_text(), repl), args.force)
    write(plugin_dir / ".gitignore",
          (common / "gitignore").read_text(), args.force)

    # the server (language-specific)
    server_src = lang_dir / server_entry
    write(plugin_dir / server_entry, substitute(server_src.read_text(), repl), args.force)

    # registry examples (skills + agents)
    reg = common / "registry"
    for src in reg.rglob("*"):
        if src.is_file():
            rel = src.relative_to(reg)
            write(plugin_dir / "registry" / rel, substitute(src.read_text(), repl), args.force)

    print(f"""
Done. Next steps:
  1. Smoke-test the server:
       python {Path(__file__).parent / 'smoke_test_mcp.py'} --plugin {plugin_dir} \\
         --expect-tool list_skills --call list_skills
  2. Validate manifests:
       python {Path(__file__).parent / 'validate_plugin.py'} {plugin_dir}
  3. Install locally and confirm it connects:
       claude plugin marketplace add {root} --scope user
       claude plugin install {args.name}@{marketplace} --scope user
       claude mcp list | grep {server_name}
  4. Fill the registry: add registry/skills/<id>/SKILL.md and registry/agents/<id>.md
     for the capabilities THIS project needs, then customize {server_entry} with any
     project-specific tools (see references/mcp-server.md).
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
