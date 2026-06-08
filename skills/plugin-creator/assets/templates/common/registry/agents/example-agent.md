---
name: example-agent
description: Replace me. A specialized subagent — what it does and what it returns.
---

You are the `example-agent` dispatched by the {{DISPLAY_NAME}} plugin. Replace this
entire body with the real system prompt for the subagent.

## Mission
State the single job this agent does.

## Method
1. ...
2. ...

## Return format (strict)
- ...

The host agent obtains this via `load_agent("example-agent")` (or `agent://example-agent`)
and runs it by spawning a generic subagent with this text as its instructions — so the
agent is plugin-scoped and loaded on demand, never registered into the always-on list.
