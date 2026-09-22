# hooks — put the defect in front of the agent while the file is open

The highest-leverage piece of this tool, and the one most often skipped. A
violation surfaced at review time is a task; the same violation surfaced during
the write is a keystroke.

Derived from impeccable's `hooks` (Apache-2.0); the contract below is deuxui's
own, learned the hard way — see NOTICE.md.

## What it does

A `PostToolUse` hook runs `ux_check.py --stdin` after every Write and Edit. When
the file has a P0 or P1 finding, the hook returns it as context the agent reads
immediately. When the file is clean, it returns nothing at all.

The deuxui plugin ships this wired. Standalone:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/deuxui/scripts/ux_check.py --stdin"
      }]
    }]
  }
}
```

## The contract, and why each part is the way it is

**JSON on stdout, `hookSpecificOutput.additionalContext`, exit 0.** Not stderr:
on exit 0, stderr never reaches the model, so a hook that wrote there was a hook
whose findings nobody ever saw. Not exit 2 either: exit 2 renders a write that in
fact succeeded as a failed tool call, and the hook's job is to report a defect,
not to invent a failure.

**Nothing when the file is clean.** A hook that speaks on every write becomes
noise, and noise gets ignored — which costs more than the hook was worth.

**P0 and P1 only.** A P2 is not worth interrupting for. It will be caught by the
project scan.

**Single-file scope reports no rule as PASS.** One file cannot establish a
product-wide property. Reporting 116 of 190 rules as PASS off one edited
component is the exact laundering this tool exists to refuse, and it is what the
hook did in its first version.

## Speed is a correctness property

A hook that costs 260ms on every write gets uninstalled. `ux_check.py` sniffs the
payload's file extension **before** importing yaml and the check modules, so
editing a `.py` or a `.md` costs a bare interpreter start rather than sixty
milliseconds of imports. The rule pack is a size-and-mtime-keyed JSON cache, which
took rule loading from 128ms to 1ms. Current cost on an interface file: about
130ms.

`HOOK_EXT` duplicates the extension list for that fast path, and `selftest.py`
asserts it has not drifted from `SOURCE_EXT | STYLE_EXT | NATIVE_EXT` — because a
silent drift there means the hook stops seeing a whole file type, and nothing else
would ever notice. That guard has already caught one drift it was written for.

## Will a plugin conflict with a skill install?

No, but be deliberate. A plugin install copies the skill into a version-keyed
cache; a symlinked or copied skill in `~/.claude/skills/` is a second copy with
its own trigger surface. Two copies do not break anything, but they can both fire
and they can be different versions. Pick one. `scripts/doctor.py` reports the
registry it loaded, which is how you tell which copy answered.

Setup: [onboard.md](onboard.md).
