# Ship

## The sequence

```bash
# 1. gate
python3 skills/skill-forge/scripts/forge_check.py skills/<name>

# 2. executable bits IN GIT -- core.fileMode=false hides the local ones
git add -A skills/<name>
git update-index --chmod=+x skills/<name>/scripts/<each-directly-invoked-script>

# 3. regenerate (the pre-commit hook also does this and re-stages)
python3 scripts/build_registry.py

# 4. commit
git add -A skills/<name> README.md registry.json
git commit
```

## Commit conventions

```
feat(<skill-name>): summary (vX.Y.Z)
fix(<skill-name>): summary (vX.Y.Z)
chore(registry): ...
```

Bump `metadata.version` and `metadata.last_updated` on every substantive edit.
The version in the commit subject should match the one in the frontmatter.

Write the body for someone reading it in a year with no context: what changed,
what it was before, and why the before was wrong. If a measurement motivated the
change, put the numbers in — "119 → 35 findings, true positives retained" ages
far better than "improved precision".

Report negative results too. A commit saying "this made no measurable difference
on knowledge tasks" is more useful than one implying an improvement that was
never demonstrated.

## Packaging

```bash
python3 -m scripts.package_skill <path-to-skill>      # from the skill-creator dir
```

Produces a `.skill` archive. `*.skill`, `*.zip` and `dist/` are gitignored —
packaged artifacts stay out of the repo. Move the output somewhere findable; it
lands next to the packager by default.

## Wrapping it in a plugin

Only when you need something a skill cannot do: a slash command, a subagent, or
a hook. `plugin-creator` has the scaffolder and the manifest reference.

```
<name>-plugin/
├── .claude-plugin/plugin.json
├── commands/          # slash commands
├── agents/            # subagent definitions
├── hooks/hooks.json   # the reason most plugins exist
└── skills/<name>      # the skill itself, or a symlink to it
```

Use `${CLAUDE_PLUGIN_ROOT}` for every intra-plugin path. A hook that shells out
to a bundled script needs it, and a relative path will work on your machine and
nowhere else.

The highest-value hook is usually `PostToolUse` on `Write|Edit`: it surfaces
problems while the code is being written rather than at review. Give it a short
timeout and make the script exit quietly when the file is out of scope, or it
becomes noise on every edit.

## After shipping

Leave the workspace behind. `*-workspace/` is gitignored build output — eval
runs, benchmarks and the review HTML belong there, not in the repo. Keep the
`evals/` directory, which is source.
