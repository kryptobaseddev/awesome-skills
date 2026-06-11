---
name: image-nanobanana
description: "Generate and edit production-ready, watermark-free image assets with Google's Nano Banana models — gemini-3.1-flash-image (Nano Banana 2) and gemini-3-pro-image (Nano Banana Pro) — via the paid Gemini API and the gemini-cli nanobanana extension. Use when the user wants to create, generate, make, draw, design, edit, restore, or iterate on any image, picture, photo, graphic, illustration, logo, or visual asset; mentions Nano Banana, Gemini image generation, text-to-image, or AI images; complains about the Gemini sparkle watermark or wants a watermark removed from an image; or asks for app icons, favicons, hero banners, OG/social cards, YouTube thumbnails, marketing creatives, diagrams, seamless patterns, sprite sheets, or consistent characters. Bundles preflight, a direct-API generator with aspect-ratio and 512/1K/2K/4K control, gemini-cli setup, prompting guidance, and per-asset production recipes."
license: MIT
compatibility: >-
  Bundled scripts need Python 3.8+ (standard library only), bash, and curl.
  A paid-tier Gemini API key is required for generation (image models have no
  free-tier quota). gemini-cli is optional — only the interactive extension
  path uses it. Linux, macOS, and WSL.
inputs:
  - name: GEMINI_API_KEY
    description: Gemini API key from https://aistudio.google.com/apikey — its Google Cloud project must have billing enabled (Tier 1+); image models are not available on the API free tier. GOOGLE_API_KEY and NANOBANANA_API_KEY work as fallbacks. Instead of an env var, the key can be stored in ~/.gemini/.env via scripts/nb-cli-setup.sh --set-key (never in the skill folder — it is git-tracked).
    required: true
metadata:
  author: github.com/kryptobaseddev
  version: "1.1.0"
  last_updated: "2026-06-11 18:15:00"
  category: media
allowed-tools: Bash Read Write Edit Glob Grep
---

# Nano Banana Image Asset Generation

Produce professional, production-ready image assets — icons, banners,
thumbnails, OG cards, diagrams, patterns, character sets — with Google's
Gemini image models ("Nano Banana"). Two execution paths, one skill:

1. **Direct API** via `scripts/nb-generate.py` — the production path: exact
   aspect ratios, 512/1K/2K/4K sizes, editing with reference images, retries,
   JSON output, cost estimates.
2. **gemini-cli** + nanobanana extension — the interactive path for users who
   live in a gemini-cli session (`/generate`, `/edit`, `/icon`, ...).

Both paths produce images with **no visible watermark** (the Gemini "sparkle"
overlay exists only in the consumer Gemini app for free/Pro tiers). Every
image carries Google's invisible SynthID provenance mark — leave it intact.

## Facts that prevent broken work (June 2026)

| Fact | Consequence |
|---|---|
| GA model ids: `gemini-3.1-flash-image` (Nano Banana 2), `gemini-3-pro-image` (Nano Banana Pro) | Use these. The `-preview` ids **shut down 2026-06-25** |
| The nanobanana extension still defaults to a `-preview` id | Always pin `NANOBANANA_MODEL` (nb-cli-setup.sh does it) |
| Image models have **zero free-tier API quota** | A key without billing gets 429s — that's a billing problem, not a bug |
| gemini-cli consumer OAuth retires **2026-06-18** | API-key auth is the only durable gemini-cli setup |
| Visible sparkle watermark = consumer Gemini app (free/Pro) only | Never source production assets from the Gemini app; generate via API |

## Preflight (run once per session)

```bash
bash scripts/nb-preflight.sh          # human-readable; --quiet for JSON
```

It verifies python3/curl, finds the API key, probes the GA model with the key,
and audits gemini-cli/extension/auth. Exit codes: 0 ready, 2 usage, 4 missing
binary, 5 network, 6 key missing/rejected. One blind spot: preflight cannot
prove billing — an un-billed key still passes and then 429s on the first real
generation (that 429 means "enable billing", not "retry").

If there's no key: send the user to https://aistudio.google.com/apikey,
remind them to enable billing on the key's project, then either
`export GEMINI_API_KEY=...` (session/profile) or store it persistently with
`bash scripts/nb-cli-setup.sh --set-key -` (writes `~/.gemini/.env`,
chmod 600 — the one file gemini-cli, the extension, and these scripts all
read). **Never write a key into the skill folder** — it's a git-tracked
directory and keys placed there end up in commits. Don't attempt generation
before preflight passes — every failure mode after that is harder to
diagnose.

## Generating assets

Default model choice: iterate on **flash** at 1K (cheap, fast), render the
final on the format the asset needs — switch to **pro** for maximum fidelity,
complex composition, or in-image text.

```bash
# Basic generation
python3 scripts/nb-generate.py "modern flat illustration of a rocket launch, purple gradient, no text" \
  -a 16:9 -s 1K

# Production render: pro model, 4K, named output
python3 scripts/nb-generate.py "minimalist app icon, bold checkmark, flat geometric, teal on off-white, no text" \
  -m pro -a 1:1 -s 4K -o assets/icons --name app-icon

# Variants to choose from
python3 scripts/nb-generate.py "..." -n 3

# Edit / iterate (pass the exact path the previous run printed — cheaper and
# more faithful than re-rolling)
python3 scripts/nb-generate.py "make the background darker, keep everything else identical" \
  -i assets/icons/app-icon-20260611-173000.png

# Machine-readable result (paths, cost, model) on stdout
python3 scripts/nb-generate.py "..." --json

# Inspect the exact API payload without spending money or needing a key
python3 scripts/nb-generate.py "..." -a 21:9 -s 2K --dry-run
```

Model aliases: `-m flash` → gemini-3.1-flash-image · `-m pro` →
gemini-3-pro-image · `-m legacy` → gemini-2.5-flash-image. Aspect ratios:
1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 everywhere; banner ratios
1:4, 4:1, 1:8, 8:1 on flash only. The script validates combinations before
spending money and prints an estimated cost after.

### Crafting the prompt

Write prompts as creative direction, not keyword soup. The four golden rules:
natural language, specific subjects/materials, state the purpose, edit instead
of re-rolling. For the full method (dimension checklist, camera/lighting
vocabulary, text rendering, anti-patterns, calibration examples), read
[references/prompting.md](references/prompting.md) before writing anything
beyond a trivial prompt. For named deliverables (icon, thumbnail, OG card...)
start from the matching recipe in
[references/asset-recipes.md](references/asset-recipes.md) — it fixes the
right model/aspect/size per asset type.

## gemini-cli path (interactive)

Set up once:

```bash
bash scripts/nb-cli-setup.sh --model flash        # install extension + pin GA model
bash scripts/nb-cli-setup.sh --fix-auth           # also switch auth to gemini-api-key
```

Then, inside gemini-cli or headless:

```bash
gemini --yolo "/generate 'watercolor fox reading a book'"
gemini --yolo "/edit nanobanana-output/fox.png 'add falling leaves'"
```

Commands: `/generate`, `/edit`, `/restore`, `/icon`, `/diagram`, `/pattern`,
`/story`, `/nanobanana`. Output lands in `./nanobanana-output/`. The extension
has **no aspect-ratio or API-resolution control** (only `/generate --count`,
`/icon --sizes`, `/pattern --size` presets) — for exact dimensions use
`nb-generate.py`. Details:
[references/gemini-cli.md](references/gemini-cli.md).

## Production workflow

1. **Pin the spec** — asset type, exact target dimensions, style, text,
   where it ships. Use the recipe table in asset-recipes.md.
2. **Preflight** — `nb-preflight.sh`.
3. **Draft cheap** — flash @ 1K, `-n 3` if direction is uncertain.
4. **Iterate via edits** — pass the chosen draft back with `-i` and a precise
   change instruction; don't regenerate from scratch.
5. **Final render** — target model/size (pro @ 2K/4K for hero/print/text).
6. **QA** — verify pixel dimensions, no uninvited text, legibility at target
   size (the checklist at the end of asset-recipes.md).
7. **Report** — tell the user the file paths and the estimated spend.

## Routing

| Intent | Reference | Use for |
|---|---|---|
| Exact API details | [api.md](references/api.md) | REST shape, model matrix, sizes/ratios, thinking, grounding, pricing, error table, SDK snippets |
| Write a great prompt | [prompting.md](references/prompting.md) | Golden rules, dimension checklist, technique vocabulary, anti-patterns, calibration examples |
| A named asset type | [asset-recipes.md](references/asset-recipes.md) | Per-asset model/aspect/size + command templates + QA checklist |
| gemini-cli / extension | [gemini-cli.md](references/gemini-cli.md) | Auth deadlines, install, commands, headless use, troubleshooting |
| Watermark questions | [watermarks.md](references/watermarks.md) | Sparkle vs SynthID, which surfaces are clean, provenance ethics |

If a request spans areas ("make me an OG card and explain the watermark
story"), load both references and compose one answer.

## Scripts

| Script | Purpose | Notable flags |
|---|---|---|
| `scripts/nb-preflight.sh` | Verify binaries, key validity, model visibility, gemini-cli state | `--quiet` (JSON) |
| `scripts/nb-generate.py` | Generate/edit via the API (the production path) | `-m -a -s -i -n -o --name --thinking-level --search-grounding --json --dry-run` |
| `scripts/nb-cli-setup.sh` | Install/update extension, pin GA model, store key, audit auth | `--model flash\|pro --set-key KEY\|- --fix-auth --dry-run` |

## Conduct

- **Spend awareness**: state the estimated cost before batches (`-n` > 3 or
  any 4K run) and report actual estimates after. Pro @ 4K is $0.24/image.
- **Never strip or alter SynthID**, and decline requests to remove watermarks
  from images the user didn't generate — regenerate through the API instead
  (watermarks.md explains why).
- **Iterate via edit, not re-roll** — it's cheaper and preserves what's right.
- **Always report saved file paths**; never leave outputs undisclosed.
- **Safety blocks**: a 200 response with no image means the prompt was
  blocked — rephrase and explain, don't retry verbatim.
- **Text in images**: quote exact strings, switch to pro when text matters,
  and add "no text, no watermarks" when it doesn't.

## Troubleshooting quick hits

| Symptom | Fix |
|---|---|
| 429 on a fresh key | Enable billing — image models have no free quota |
| 404 model not found | You're on a `-preview` id (dead after 2026-06-25) — use GA ids |
| gemini-cli auth fails (after 2026-06-18) | `nb-cli-setup.sh --fix-auth` + `export GEMINI_API_KEY` |
| Image has a sparkle watermark | It came from the consumer Gemini app — regenerate via API |
| Wrong dimensions from the extension | Extension can't control format — use `nb-generate.py -a -s` |
| No image in response | Safety block — check stderr for the reason, rephrase |
