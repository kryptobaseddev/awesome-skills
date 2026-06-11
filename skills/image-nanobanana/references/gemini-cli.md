# gemini-cli + nanobanana Extension — Reference

Read this when driving image generation through gemini-cli instead of the
direct API script — interactive sessions, slash commands, or when the user
already lives in gemini-cli.

## Table of contents

1. [When to use which path](#1-when-to-use-which-path)
2. [Auth — read this first](#2-auth--read-this-first)
3. [Installing the nanobanana extension](#3-installing-the-nanobanana-extension)
4. [The preview-model time bomb](#4-the-preview-model-time-bomb)
5. [Commands](#5-commands)
6. [Headless / scripted invocation](#6-headless--scripted-invocation)
7. [Output and limitations](#7-output-and-limitations)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. When to use which path

| Need | Use |
|---|---|
| Precise aspect ratio / 2K / 4K output | `scripts/nb-generate.py` (the extension has **no** aspect/size controls) |
| Machine-readable output, batch, CI | `scripts/nb-generate.py --json` |
| Interactive ideation inside a gemini-cli session | nanobanana extension slash commands |
| Multi-step asset sessions with the model picking tools | nanobanana extension (`/nanobanana` natural-language command) |

Both paths hit the same API with the same key and produce identical
watermark-free output (invisible SynthID only — see
[watermarks.md](watermarks.md)).

## 2. Auth — read this first

Two hard deadlines collapsed gemini-cli auth onto API keys:

- **2026-06-18**: gemini-cli/Code Assist **stops serving consumer OAuth**
  (`oauth-personal` — individuals, AI Pro, AI Ultra) per Google's Antigravity
  CLI migration. Only paid API keys and Code Assist Standard/Enterprise
  licenses keep working.
- Image models were **never** available on free quota anyway (quota 0 without
  billing).

So: get a key at https://aistudio.google.com/apikey, enable billing on its
project, then:

```bash
export GEMINI_API_KEY="..."          # also put it in your shell profile
```

and set `~/.gemini/settings.json` → `security.auth.selectedType` to
`"gemini-api-key"` (run `scripts/nb-cli-setup.sh --fix-auth` to do both checks
and the edit with a backup).

Key resolution order inside the nanobanana extension:
`NANOBANANA_API_KEY` → `NANOBANANA_GEMINI_API_KEY` → `NANOBANANA_GOOGLE_API_KEY`
→ `GEMINI_API_KEY` → `GOOGLE_API_KEY`.

Google's successor for the OAuth/agent workflow is the **Antigravity CLI**
(keeps Skills, Hooks, Subagents; extensions carry over as plugins, parity not
guaranteed). This reference targets gemini-cli with API-key auth, which
continues to work.

## 3. Installing the nanobanana extension

```bash
gemini extensions install https://github.com/gemini-cli-extensions/nanobanana
gemini extensions list            # verify
gemini extensions update nanobanana
```

Installs under `~/.gemini/extensions/nanobanana/` (an MCP server + slash
commands). `scripts/nb-cli-setup.sh` automates install + model pinning + auth
audit in one shot.

## 4. The preview-model time bomb

The extension's built-in default model is `gemini-3.1-flash-image-preview` — a
**deprecated id that shuts down 2026-06-25**. Until the extension ships a fix,
every install MUST override it:

```bash
export NANOBANANA_MODEL=gemini-3.1-flash-image    # or gemini-3-pro-image
```

`nb-cli-setup.sh` pins this in `~/.gemini/.env` so interactive sessions pick it
up automatically. If generation suddenly starts failing with 404s, this is the
first thing to check.

## 5. Commands

All commands accept natural-language arguments and write to
`./nanobanana-output/`:

| Command | Use case | Notable flags |
|---|---|---|
| `/generate <prompt>` | Text-to-image | `--count=N` (1-8), `--format=grid\|separate`, `--styles=...`, `--seed=N`, `--preview` |
| `/edit <file> <instruction>` | Modify an existing image | |
| `/restore <file> [notes]` | Repair/restore old or damaged photos | |
| `/icon <description>` | App icons, favicons, UI elements | `--sizes="16,32,64,..."` (16-1024 px) |
| `/diagram <description>` | Flowcharts, architecture diagrams | |
| `/pattern <description>` | Seamless textures and patterns | `--size=WxH` (e.g. 256x256) |
| `/story <description>` | Sequential/narrative image sets | |
| `/nanobanana <anything>` | Natural-language interface to all of the above | |

No command exposes **aspect-ratio or API-resolution (1K/2K/4K)** control — the
model infers format from the prompt ("a wide 16:9 banner..."); `/icon --sizes`
and `/pattern --size` set pixel presets for those asset types only. For
guaranteed dimensions use `nb-generate.py`.

## 6. Headless / scripted invocation

Slash commands work non-interactively when passed as the prompt with
auto-approval:

```bash
gemini --yolo "/generate 'flat illustration of a rocket launch, purple gradient'"
gemini --yolo "/edit nanobanana-output/rocket.png 'make the sky darker'"
```

Notes:

- `--yolo` auto-approves the extension's tool calls (file writes). Newer CLI
  versions also accept `--approval-mode yolo`.
- `-m <model>` selects the *chat* model driving the session, not the image
  model — the image model comes from `NANOBANANA_MODEL`.
- Plain `gemini -p "..."` without the extension does NOT generate images; the
  core CLI has no native image generation (true through v0.45).

## 7. Output and limitations

- Images land in `./nanobanana-output/` relative to the working directory.
- One image per command by default (`/generate --count=N` for variants); no
  aspect-ratio or 1K/2K/4K resolution control on any command.
- `--preview`-style auto-opening depends on a display; on headless boxes just
  list the directory and present file paths.
- The extension is an MCP server (Node) started by gemini-cli; it does not
  work standalone.

## 8. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| 404 model not found (after 2026-06-25) | Preview default → `export NANOBANANA_MODEL=gemini-3.1-flash-image` |
| 429 quota exceeded on a brand-new key | No billing on the key's project — image models have zero free quota |
| Auth errors after 2026-06-18 | Consumer OAuth retired → switch to `gemini-api-key` auth (`nb-cli-setup.sh --fix-auth`) |
| `gemini: command not found` | `npm install -g @google/gemini-cli` |
| Extension listed but commands missing | Restart the session; extensions load at startup |
| Images have a visible sparkle watermark | They came from the consumer Gemini app, not the API — regenerate via API/CLI (see [watermarks.md](watermarks.md)) |

Sources: https://github.com/gemini-cli-extensions/nanobanana ·
https://github.com/google-gemini/gemini-cli ·
https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
