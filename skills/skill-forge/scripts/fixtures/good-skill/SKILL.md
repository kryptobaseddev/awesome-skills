---
name: good-skill
description: "A minimal well-formed skill used as a positive fixture. Use when testing that forge_check does not report problems on a sound skill. Not for real work. Use even if the user only says 'fixture'."
license: MIT
metadata:
  author: github.com/kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-09-20 19:00:00"
  category: skill-development
---

# good-skill

A positive fixture. It exists so the checker can be shown not to fire on a sound
skill, which is the half of a checker people forget to test.

## Body

It has three top-level reference files and never tells the agent to run a script,
so the executable-bit check has nothing to complain about.
