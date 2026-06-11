# Nano Banana Prompting Guide

How to write prompts that get production-quality results from Gemini image
models (`gemini-3-pro-image` / Nano Banana Pro and the flash-image line).
Based on Google's official prompting guidance.

## Contents

- [Core principles](#core-principles)
- [Prompt structure template](#prompt-structure-template)
- [Dimension checklist](#dimension-checklist)
- [Technique library](#technique-library)
- [Text rendering](#text-rendering)
- [Editing and iteration](#editing-and-iteration)
- [Reference images and consistency](#reference-images-and-consistency)
- [Anti-patterns](#anti-patterns)
- [Calibration examples](#calibration-examples)

## Core principles

These models understand intent, physics, and composition. They reward
**clear creative direction** over keyword lists.

1. **Natural language over tag soup.** Write as if briefing a human artist.
   - BAD: `dog, park, sunset, 4k, realistic, cinematic`
   - GOOD: `A golden retriever bounding through a sun-dappled park at golden
     hour, shot from a low angle with shallow depth of field`

2. **Specificity matters.** Define subjects with materiality, texture, and
   detail. Instead of "a woman": "a sophisticated elderly woman wearing a
   vintage Chanel-style tweed suit". Name materials: "matte finish",
   "brushed steel", "soft velvet", "weathered leather".

3. **State the purpose.** "Hero image for a premium coffee brand's website"
   lets the model infer professional lighting, composition, and mood. Always
   include the use case when the asset has one.

4. **Edit, don't re-roll.** When a result is mostly right, send the image
   back with a specific conversational change instead of regenerating from
   scratch. The model preserves what you don't mention.

## Prompt structure template

Not every element is required — use what's relevant, keep it coherent:

```
[Style/medium] of [specific subject with details] in [setting/environment],
[action or pose], [lighting description], [mood/atmosphere],
[camera angle/composition], [texture, color palette, materiality].
[Purpose context.]
```

## Dimension checklist

When a request is vague, fill these gaps (ask the user, or infer from the
use case — 2-3 questions max per round, never a full interrogation):

| Dimension | What to pin down | Examples |
|---|---|---|
| Subject | Who/what is the focus? | Person, product, scene, abstract concept |
| Setting | Where? | Studio, urban, nature, fantastical |
| Mood | What feeling? | Serene, dramatic, playful, premium |
| Style | Visual language? | Photorealistic, flat illustration, watercolor, editorial, 3D render |
| Composition | Framing? | Close-up, wide shot, flat lay, rule of thirds |
| Lighting | Conditions? | Golden hour, soft window light, neon, chiaroscuro |
| Purpose | Where will it live? | Website hero, app icon, social post, print |
| Text | Exact strings to render? | Put exact text in quotation marks |
| Format | Aspect ratio + resolution? | 16:9 @ 2K for hero, 1:1 @ 1K for avatar |

## Technique library

- **Camera language**: "wide establishing shot", "tight close-up",
  "over-the-shoulder", "Dutch angle", "shallow depth of field", "85mm
  portrait lens", "macro detail shot".
- **Lighting specifics**: "Rembrandt lighting", "backlit with rim light",
  "soft window light from the left", "three-point studio lighting",
  "dramatic chiaroscuro".
- **Material and texture**: "brushed aluminum", "hand-knit wool", "cracked
  leather", "translucent frosted glass", "soft-touch matte plastic".
- **Color direction**: "muted earth tones", "high-contrast complementary
  colors", "monochromatic blue palette", "brand colors #1A73E8 and white".
- **Negative space**: ask for it explicitly when the asset needs room for
  overlaid text — "generous negative space on the right third for headline
  text".
- **Style isolation**: for UI/asset work, add "isolated on a solid white
  background" or "transparent-style flat background" to ease post-cropping.

## Text rendering

Nano Banana models have state-of-the-art in-image text rendering:

- Put the **exact text in quotation marks**: `the headline "SHIP FASTER" in
  bold geometric sans-serif`.
- Specify typography style: "bold art deco", "handwritten script",
  "retro neon sign", "clean Swiss grid typography".
- Keep rendered text short; long paragraphs still degrade.
- For localization: "Translate the text in this image to Japanese" works as
  an edit instruction with the source image attached.
- If you want NO text in the image, say "no text, no typography, no
  watermarks, no labels" — generated assets otherwise often invent captions.

## Editing and iteration

Send the previous image back with a natural-language instruction:

- "Change the sunny day to a rainy night" — lighting, reflections, and
  physics adjust automatically.
- "Remove the person in the background and add a potted plant"
- "Make the text neon blue instead of white"
- "Zoom out to show the full desk" / "Crop tighter on the face"

Dimensional translation also works as an edit: hand-drawn sketch →
photorealistic render, floor plan → 3D room visualization, wireframe →
high-fidelity UI mockup, product photo → lifestyle scene.

## Reference images and consistency

Both model lines accept multiple input images for character/object/style
consistency — up to 14 mixed reference images per request; within that,
flash (`gemini-3.1-flash-image`) honors up to 10 object refs + 4 character
refs, pro (`gemini-3-pro-image`) up to 6 object refs + 5 character refs:

- "Use the attached images as a strict style reference"
- "Keep the character from image 1 but place them in the setting from image 2"
- "Keep facial features exactly the same as the reference"
- Storyboards: "The identity and attire of all characters must stay
  consistent throughout"

## Anti-patterns

- **Tag soup** — disconnected keywords; rewrite as sentences.
- **Vague subjects** — "a person", "a building"; add specifics.
- **Missing mood/lighting** — these two dimensions move quality the most.
- **No purpose context** — the model can't infer "this is an app store
  screenshot" unless told.
- **Over-prompting** — contradictory or excessive detail confuses
  composition; keep one coherent creative direction per prompt.
- **Re-rolling instead of editing** — wastes money and loses the parts that
  were already right.

## Calibration examples

**Product photography**
> A flat lay of artisanal coffee beans spilling from a matte black ceramic
> cup onto a weathered oak table, soft directional window light from the
> upper left, warm earth tones with deep shadows, shot from directly above,
> styled for a premium coffee brand's Instagram feed.

**Portrait**
> A cinematic medium close-up portrait of a jazz musician mid-performance,
> eyes closed, sweat glistening under warm amber stage lighting, shallow
> depth of field with bokeh from string lights in the background, shot on
> what looks like 35mm film with natural grain.

**Text-heavy design**
> A vintage-style concert poster with the text "MIDNIGHT REVERIE" in bold
> art deco typography at the top, a silhouette of a saxophone player against
> a deep indigo night sky with a full moon, "Live at The Blue Note — March
> 15, 2026" in smaller elegant serif type at the bottom, gold and navy
> color palette.

**Fantasy/illustration**
> A lush watercolor illustration of a hidden forest library, towering
> bookshelves made from living trees with glowing mushrooms as reading
> lamps, a cozy armchair draped in moss-green velvet, shafts of golden
> sunlight filtering through the canopy above, whimsical and enchanting
> atmosphere.

**UI asset (negative space + no text)**
> A modern flat illustration of a developer at a laptop surrounded by
> floating geometric shapes, purple-to-blue gradient background, minimalist
> vector style, generous negative space in the upper half for headline
> text, no text, no labels, no watermarks.

## Sources

- [7 tips to get the most out of Nano Banana Pro](https://blog.google/products/gemini/prompting-tips-nano-banana-pro/) — Google Blog
- [Nano Banana 2: Combining Pro capabilities with lightning-fast speed](https://blog.google/innovation-and-ai/technology/ai/nano-banana-2/) — Google Blog
- [Image generation](https://ai.google.dev/gemini-api/docs/image-generation) — Gemini API docs
