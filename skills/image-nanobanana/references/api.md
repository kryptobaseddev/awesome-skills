# Gemini Image API (Nano Banana) — Reference

Read this when you need exact request shapes, model capabilities, pricing, or
error handling for direct API generation. Facts verified against the official
docs in June 2026; the bundled `scripts/nb-generate.py` already implements all
of this.

## Table of contents

1. [Models](#1-models)
2. [REST request shape](#2-rest-request-shape)
3. [Aspect ratios and sizes](#3-aspect-ratios-and-sizes)
4. [Reference images (editing and consistency)](#4-reference-images-editing-and-consistency)
5. [Thinking behavior](#5-thinking-behavior)
6. [Search grounding and video input](#6-search-grounding-and-video-input)
7. [Pricing](#7-pricing)
8. [Rate limits and tiers](#8-rate-limits-and-tiers)
9. [SDK snippets](#9-sdk-snippets)
10. [Error handling](#10-error-handling)

---

## 1. Models

| Model ID | Marketing name | Status | Best for |
|---|---|---|---|
| `gemini-3.1-flash-image` | Nano Banana 2 | GA (2026-05-28) | Default. Fast, cheap, 512–4K, widest aspect set, thinking-level control, video-to-image |
| `gemini-3-pro-image` | Nano Banana Pro | GA (2026-05-28) | Maximum fidelity, complex composition, best in-image text, factual accuracy |
| `gemini-2.5-flash-image` | Nano Banana | Stable | Legacy; fixed ~1024px, cheapest per image |

**Deprecated:** `gemini-3.1-flash-image-preview` and `gemini-3-pro-image-preview`
shut down **2026-06-25**. Anything still pointing at a `-preview` id (including
the nanobanana gemini-cli extension's built-in default) breaks that day.

Context windows: 3-pro-image 65,536 in / 32,768 out; 3.1-flash-image 131,072 in
/ 32,768 out. Source: https://ai.google.dev/gemini-api/docs/models

## 2. REST request shape

```
POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent
x-goog-api-key: $GEMINI_API_KEY
Content-Type: application/json
```

Text-to-image with format control:

```json
{
  "contents": [{"parts": [{"text": "A photorealistic ..."}]}],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}
  }
}
```

Notes:

- **Docs vs live behavior** (verified by live probe, June 2026): the docs'
  curl examples show `/v1/` and a newer
  `generationConfig.responseFormat.image` spelling — but the live `/v1`
  surface rejects `responseModalities` entirely, and `/v1beta` rejects
  `responseFormat.image` string values like `"1K"` (enum mismatch). What
  actually works today is **`/v1beta` + `generationConfig.imageConfig`** with
  string values, as shown above. `nb-generate.py` sends exactly that and
  auto-swaps to the `responseFormat` spelling if Google flips the migration.
- Every official example sets `responseModalities` explicitly (no documented
  default — always set it); `["IMAGE"]`-only is also accepted.
- Editing/reference input goes in as additional parts:
  `{"inline_data": {"mime_type": "image/png", "data": "<BASE64>"}}`
  (snake_case in raw REST; `inlineData`/`mimeType` camelCase in responses and
  the JS SDK — parse both defensively).

Response shape:

```
candidates[0].content.parts[]  →  {"text": "..."}                      (model commentary)
                                  {"inlineData": {"mimeType": "image/png", "data": "<BASE64>"}}
                                  parts with "thought": true            (interim — skip them)
```

A safety-blocked request returns no image parts; check
`promptFeedback.blockReason` and `candidates[0].finishReason`.

## 3. Aspect ratios and sizes

Ratios: `1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9` on all current models,
plus banner ratios `1:4 4:1 1:8 8:1` on `gemini-3.1-flash-image` only.

`imageSize` (uppercase K required): `512` (flash only), `1K`, `2K`, `4K`.
`gemini-2.5-flash-image` takes no `imageSize` (fixed ~1024px).

Pixel examples — 1:1 = 1024/2048/4096 square (confirmed by the pricing page);
other ratios approximate, the docs no longer publish a per-ratio pixel table:
16:9 @ 4K ≈ 5504x3072; 8:1 @ 4K ≈ 12288x1536 (flash banner). Verify actual
output dimensions with `identify`/`file` when exact pixels matter.

Output token costs per image: flash 747 (512) / 1120 (1K) / 1680 (2K) /
2520 (4K); pro 1120 (1K) / 1120 (2K) / 2000 (4K); legacy always 1290.

## 4. Reference images (editing and consistency)

Gemini 3 image models mix up to **14 reference images** per request:

| Model | Object refs (high fidelity) | Character refs |
|---|---|---|
| `gemini-3.1-flash-image` | up to 10 | up to 4 |
| `gemini-3-pro-image` | up to 6 | up to 5 |

Use cases: pass the previous output back with an edit instruction
(conversational editing), pass brand/product shots for style and identity
consistency, pass a sketch for structural control. See
[prompting.md](prompting.md) for instruction phrasing.

## 5. Thinking behavior

Gemini 3 image models **think by default and this cannot be disabled**. The
model produces up to two interim "thought images" (not charged, flagged
`"thought": true` in parts — always skip them when saving output).

On `gemini-3.1-flash-image` only, control depth with:

```json
"generationConfig": {"thinkingConfig": {"thinkingLevel": "minimal"}}
```

Levels: `minimal` (default, fastest) and `high` (complex compositions, many
constraints, in-image text layout). The docs' examples capitalize the value
(`"High"`) while prose uses lowercase — both spellings appear; if a call is
rejected, try the other casing. `gemini-3-pro-image` has no documented
thinking knob.

## 6. Search grounding and video input

- Add `"tools": [{"google_search": {}}]` to ground generation in live data
  (e.g. "current weather in Tokyo as an infographic"). Image-search grounding
  is flash-only and cannot search people.
- Video-to-image (frame extraction / style transfer from a YouTube URL or
  Files-API video part) is exclusive to `gemini-3.1-flash-image`.

## 7. Pricing

Paid tier, per generated image (Standard; Batch ≈ half):

| Model | 512 | 1K | 2K | 4K |
|---|---|---|---|---|
| `gemini-3.1-flash-image` | $0.045 | $0.067 | $0.101 | $0.151 |
| `gemini-3-pro-image` | — | $0.134 | $0.134 | $0.24 |
| `gemini-2.5-flash-image` | — | $0.039 flat | — | — |

Input: $0.50/1M tokens (flash), $2.00/1M (pro — image input ≈ $0.0011/image),
$0.30/1M (legacy). Text/thinking output: $3/1M (flash), $12/1M (pro).

**The API free tier does NOT include any image model** ("Not available" on the
pricing page). A key without billing gets quota errors (HTTP 429, quota 0).
Source: https://ai.google.dev/gemini-api/docs/pricing

## 8. Rate limits and tiers

Per-model RPM/TPM/IPM tables are no longer published — live limits show in the
AI Studio rate-limits dashboard for your key. Tiers: Tier 1 (billing linked),
Tier 2 ($100 spent + 3 days), Tier 3 ($1,000 + 30 days). Batch enqueued-token
caps at Tier 1: 1M (flash-image) / 2M (pro-image).

## 9. SDK snippets

Python (`pip install google-genai`):

```python
from google import genai

client = genai.Client()  # reads GEMINI_API_KEY
resp = client.models.generate_content(
    model="gemini-3-pro-image",
    contents="A photorealistic product shot of ...",
)
for part in resp.parts:
    if getattr(part, "thought", False):
        continue
    if part.as_image():
        part.as_image().save("asset.png")
```

JavaScript (`npm install @google/genai`):

```js
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({});
const resp = await ai.models.generateContent({
  model: "gemini-3.1-flash-image",
  contents: prompt,
  config: { responseModalities: ["TEXT", "IMAGE"] },
});
for (const part of resp.candidates[0].content.parts) {
  if (part.inlineData) fs.writeFileSync("asset.png",
    Buffer.from(part.inlineData.data, "base64"));
}
```

Caveat: the official docs' Python examples for the new
`responseFormat`/image-size config were syntactically inconsistent at the time
of writing — when in doubt, the raw REST shape in §2 is authoritative, and
`nb-generate.py` wraps it.

## 10. Error handling

| HTTP | Meaning | Action |
|---|---|---|
| 400 `API_KEY_INVALID` | **Bad keys return 400, not 401** ("API key not valid") | Regenerate at https://aistudio.google.com/apikey |
| 400 `INVALID_ARGUMENT` (other) | Bad field (`imageConfig` vs `responseFormat` spelling, unsupported size/ratio) | Check §2-§3; swap the config spelling |
| 401/403 | Key missing/revoked/restricted | Regenerate at https://aistudio.google.com/apikey |
| 404 | Model id wrong or retired (`-preview` after 2026-06-25) | Use GA ids from §1 |
| 429 `RESOURCE_EXHAUSTED` | Quota — on a fresh key this almost always means **no billing** (free tier = 0 image quota) | Enable billing; back off per `Retry-After` |
| 500/503/504 | Transient server | Exponential backoff, ≤3 retries |
| 200 but no image parts | Safety block or refusal | Inspect `promptFeedback.blockReason`; rephrase |

Sources: https://ai.google.dev/gemini-api/docs/image-generation ·
https://ai.google.dev/gemini-api/docs/models ·
https://ai.google.dev/gemini-api/docs/pricing ·
https://ai.google.dev/gemini-api/docs/changelog
