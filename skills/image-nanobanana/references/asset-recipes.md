# Production Asset Recipes — Reference

Read this when the user names a concrete deliverable (icon, thumbnail, OG
card, banner, pattern...). Each recipe gives the right model/aspect/size and a
command template for `scripts/nb-generate.py`. Combine with
[prompting.md](prompting.md) for the prompt itself.

## Format cheat sheet

| Asset | Aspect | Size | Model | Why |
|---|---|---|---|---|
| App icon / favicon source | 1:1 | 2K–4K | pro | Downscales to every icon size; pro nails simple geometry |
| YouTube thumbnail (1280x720) | 16:9 | 1K | flash | Fast iteration; 1K ≥ target |
| OG / social card (1200x630) | 16:9 | 1K | flash or pro | Crop 1920x1080 → 1200x630, or prompt for safe margins |
| Blog hero | 16:9 or 21:9 | 2K | flash | Wide, text overlay space |
| Twitter/X header (1500x500) | 4:1 (flash only) | 2K | flash | Native extreme ratio — no cropping |
| Leaderboard ad (728x90 class) | 8:1 (flash only) | 1K–2K | flash | Native banner ratio |
| Instagram post | 1:1 or 4:5 | 1K–2K | flash | |
| Story / Reel / Shorts cover | 9:16 | 1K–2K | flash | |
| Poster / print | 2:3 or 3:4 | 4K | pro | Fidelity + in-image text quality |
| App store screenshot backdrop | 9:16 | 2K | pro | Clean device-frame composition |
| Seamless texture / pattern | 1:1 | 1K | flash | Prompt "seamless tileable pattern" |
| Architecture / flow diagram | 16:9 or 4:3 | 2K | pro | Pro's text rendering keeps labels legible |
| Character / sprite sheet | 1:1 or 16:9 | 2K | flash | Use character reference images for consistency |
| Email header | 4:1 or 21:9 | 1K | flash | |

`pro` = `gemini-3-pro-image` ($0.134/1K-2K, $0.24/4K) ·
`flash` = `gemini-3.1-flash-image` ($0.045–$0.151). Iterate on flash @ 1K,
do the final render on the target model/size.

## Recipes

All commands run from the skill directory; adjust paths as needed. Always tell
the user the per-image cost before large batches.

### App icon (full size set)

```bash
python3 scripts/nb-generate.py \
  "minimalist app icon for a habit-tracking app, a single bold checkmark forming a rising path, flat geometric style, deep teal on warm off-white, centered with generous padding, no text, no watermarks" \
  -m pro -a 1:1 -s 4K -o assets/icons --name habit-icon
```

Then derive the platform size set from the 4K master with ImageMagick
(`magick habit-icon-*.png -resize 512x512 icon-512.png` … 256/128/64/48/32/16)
— generating each size separately wastes money and loses consistency. For
favicons, run the 32px PNG through an ICO converter.

Icon prompt rules: one concept, strong silhouette, no fine detail (dies at
16px), flat or subtly-shaded style, explicit background (or "isolated on
solid white background" for easy masking), always "no text".

### YouTube thumbnail

```bash
python3 scripts/nb-generate.py \
  "YouTube thumbnail: shocked developer staring at a laptop screen glowing red, dramatic side lighting, bold composition with empty space on the right third for title text, hyper-saturated, no text, no watermarks" \
  -m flash -a 16:9 -s 1K -n 3 -o assets/thumbs --name ep42
```

`-n 3` gives variants to pick from. Add the title text in your editor, or let
the model render it: put the exact words in quotes and switch `-m pro` for
text fidelity.

### OG / social preview card

```bash
python3 scripts/nb-generate.py \
  "open-graph card for a developer blog post about database indexing, abstract B-tree made of glowing glass nodes on dark navy, headline 'INDEX SMARTER' in bold white grotesque sans-serif left-aligned, generous margins, no other text" \
  -m pro -a 16:9 -s 2K -o assets/og --name indexing-post
```

Crop the ~1920x1080-class 2K output down to 1200x630 (center-crop or
top-anchor). Keep critical content inside the middle 80% — platforms crop
differently.

### Native wide banners (no cropping)

Extreme ratios are flash-only:

```bash
python3 scripts/nb-generate.py \
  "sleek product banner, midnight gradient with a thin neon data-stream flowing left to right, minimalist, space on the left for logo, no text, no watermarks" \
  -m flash -a 4:1 -s 2K -o assets/banners --name x-header     # 1500x500-class
```

Use `-a 8:1` for leaderboard-class strips.

### Seamless pattern / texture

```bash
python3 scripts/nb-generate.py \
  "seamless tileable pattern of hand-drawn botanical leaves and berries, muted sage and terracotta on cream, repeating wallpaper style, even density, no focal point, no text" \
  -m flash -a 1:1 -s 1K -o assets/patterns --name botanical
```

Verify tiling by placing two copies side by side; if seams show, edit with the
exact saved path:
`nb-generate.py "make the edges tile seamlessly" -i assets/patterns/botanical-20260611-173002.png`.

### Diagram (architecture / flow)

```bash
python3 scripts/nb-generate.py \
  "clean architecture diagram: three labeled boxes 'Client', 'API Gateway', 'Postgres' connected left to right with arrows, flat design, white background, blue accent, sans-serif labels exactly as quoted" \
  -m pro -a 16:9 -s 2K -o assets/diagrams --name arch
```

Pro gives the best label fidelity (it thinks by default; no flag needed). If
iterating on flash instead, add `--thinking-level high` for complex labeled
layouts. For diagrams with more than ~6 labeled elements, prefer
Mermaid/Graphviz — deterministic text beats generated text at high density.

### Consistent character set (sprites, storyboards, mascots)

Generate the canonical character once, then reference it in every subsequent
asset:

```bash
python3 scripts/nb-generate.py \
  "character sheet of a friendly robot mascot, front view, side view, back view, flat illustration, cobalt and silver, white background" \
  -m flash -a 16:9 -s 2K -o assets/mascot --name robot-sheet
# → prints the saved path, e.g. assets/mascot/robot-sheet-20260611-173001.png

python3 scripts/nb-generate.py \
  "the robot from the reference image waving hello, same proportions, colors and style, white background" \
  -i assets/mascot/robot-sheet-20260611-173001.png -m flash -a 1:1 -s 1K -o assets/mascot --name robot-wave
```

`-i` takes exactly one file — repeat `-i` per reference image, and pass the
concrete path the previous run printed (don't use globs: timestamped names
mean a glob soon matches several files and breaks the command line). Flash
takes up to 4 character refs + 10 object refs; pro takes 5 + 6.

### Photo restoration / cleanup

```bash
python3 scripts/nb-generate.py \
  "restore this photo: remove scratches and dust, repair the torn corner, correct faded colors, keep faces exactly as they are" \
  -i old-family-photo.jpg -m pro -s 2K -o restored
```

### Brand-consistent batch

For a set (hero + OG + square + story) from one art direction: write the
shared style block once, generate the hero first, then pass the hero as a
style reference to the other formats so palette/lighting match:

```bash
python3 scripts/nb-generate.py "$STYLE. Square crop composition centered on the product" \
  -i assets/hero/hero-20260611-173003.png -m flash -a 1:1 -s 2K --name square
```

## Production QA checklist

Before delivering any asset:

1. **Dimensions** — `file out.png` / `identify out.png`; confirm the pixel
   size matches the target (resize/crop if the platform needs exact pixels).
2. **No accidental text** — models love inventing captions; if any appears
   uninvited, edit it out: `-i out.png "remove all text"`.
3. **No visible watermark** — API output has none by design; if you see a
   sparkle overlay the image came from the consumer Gemini app
   (see [watermarks.md](watermarks.md)).
4. **Legibility at target size** — downscale icons to 16-32px and squint.
5. **Cost reported** — `nb-generate.py` prints the estimate; relay it.
