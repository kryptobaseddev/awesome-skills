# Decide: should this be a skill, and what shape

The cheapest skill is the one you do not write. Three questions.

## 1. Does this need to be a skill at all?

A skill earns its place when at least one is true:

- **Multi-step with a required order.** The value is the sequence, not the facts.
- **Non-obvious failure modes.** Things that look right and are wrong — the class
  of problem where a competent model confidently does the wrong thing.
- **Knowledge the model lacks or has stale.** A library that changed, an internal
  convention, a version-specific gotcha.
- **Deterministic work worth scripting.** If every invocation would otherwise
  rewrite the same helper, bundle the helper.

It does **not** earn its place when the model already does the task well. That is
worth measuring rather than assuming: run the task once without a skill and look
at the output. If it is already good, a skill adds tokens and no quality — the
honest result, and one worth finding before you write 90 files instead of after.

What a skill *can* still add over a capable model is **verifiability**: turning an
assertion into something checkable. That is a real contribution even when the
prose quality is unchanged, but be clear which one you are claiming.

## 2. Prose, or prose plus scripts?

| Ship a script when | Keep it prose when |
|---|---|
| The work is deterministic and repeated | The work is judgement |
| Re-deriving it each time costs more than running it | It is a one-liner the model knows |
| It produces evidence a reader can check | The output is advice |
| Its absence means every run reinvents it | Bundling would just wrap a CLI |

A script that ships must be able to fail. If it has no selftest and no fixtures,
nobody — including you — knows whether it still works. `forge_check.py` warns on
a skill that ships `scripts/` without a `selftest.py` for this reason.

## 3. Skill or plugin, or both?

| You want | You need |
|---|---|
| Knowledge an agent loads when relevant | A **skill** |
| A slash command the user types | A **plugin** (`commands/`) |
| A subagent with its own instructions | A **plugin** (`agents/`) |
| Something to run *automatically* on a tool call | A **plugin** (`hooks/`) — this is the one that cannot be done with a skill |
| Tools callable by non-Claude-Code agents | A **plugin** with an MCP server |

A plugin can carry the skill (`skills/<name>` inside it, or a symlink), so
"both" is the normal answer when you want a hook. See `plugin-creator`, and use
`${CLAUDE_PLUGIN_ROOT}` for every intra-plugin path.

## 4. Does it overlap something that exists?

Check before naming it. Two skills claiming the same territory pull an agent in
different directions and make triggering unpredictable.

```bash
grep -l '' skills/*/SKILL.md | xargs -I{} sh -c 'echo "== {}"; grep -m1 "^description:" {}' | less
```

If there is overlap, decide explicitly: absorb, defer, or draw a boundary — and
write the boundary into **both** descriptions. A boundary that exists only in the
body does not affect triggering, because the body is not what the agent reads
when deciding.
