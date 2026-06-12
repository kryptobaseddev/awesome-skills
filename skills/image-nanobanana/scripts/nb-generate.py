#!/usr/bin/env python3
"""nb-generate.py — generate or edit images via the Gemini API (Nano Banana).

Direct REST client for the GA image models. No third-party deps (stdlib only).
Output images carry Google's invisible SynthID watermark but NO visible
"sparkle" watermark (that overlay is applied only in the consumer Gemini app
for free/Pro tiers — never on paid API output).

Usage:
  nb-generate.py "PROMPT" [options]
  nb-generate.py --prompt-file brief.txt [options]

Options:
  -m, --model M        flash | pro | legacy | full model id   (default: flash)
                         flash  = gemini-3.1-flash-image  (Nano Banana 2)
                         pro    = gemini-3-pro-image      (Nano Banana Pro)
                         legacy = gemini-2.5-flash-image  (Nano Banana)
  -a, --aspect R       1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9
                       (flash also: 1:4 4:1 1:8 8:1)
  -s, --size S         512 | 1K | 2K | 4K  (512 = flash only; legacy = fixed)
  -i, --image PATH     input/reference image; repeat up to 14 times
                       (presence switches the call from generation to editing)
  -n, --count N        number of images to generate (sequential calls)
  -o, --out DIR        output directory                (default: ./nanobanana-output)
      --name BASE      output file basename            (default: slug of prompt)
      --thinking-level minimal | high   (gemini-3.1-flash-image only)
      --search-grounding                ground the prompt with Google Search
      --timeout SEC    per-request timeout             (default: 300)
      --json           machine-readable result on stdout (logs go to stderr)
      --dry-run        print the request payload and exit (no API call, no key needed)

API key (paid tier required — image models are NOT on the API free tier):
  Environment: GEMINI_API_KEY (preferred), GOOGLE_API_KEY, or NANOBANANA_API_KEY.
  File fallback: same names in ~/.gemini/.env (store one safely with
  `nb-cli-setup.sh --set-key -`). Never put keys in the skill folder — it is
  a git-tracked directory.
  GEMINI_API_BASE_URL — override https://generativelanguage.googleapis.com
  GEMINI_API_VERSION — override v1beta (the surface that accepts these payloads)

Exit codes:
  0 success | 2 usage/validation | 5 network | 6 auth/key | 7 quota/billing | 1 API/other
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com")
# The docs show /v1/ but the live /v1 surface rejects generationConfig.
# responseModalities (verified June 2026) — /v1beta is the one that works.
API_VERSION = os.environ.get("GEMINI_API_VERSION", "v1beta")

BASE_RATIOS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
EXTREME_RATIOS = {"1:4", "4:1", "1:8", "8:1"}  # gemini-3.1-flash-image only

MODELS = {
    "gemini-3.1-flash-image": {
        "aliases": ("flash", "nb2", "nano-banana-2"),
        "sizes": ("512", "1K", "2K", "4K"),
        "ratios": BASE_RATIOS | EXTREME_RATIOS,
        "thinking_config": True,
        "cost": {"512": 0.045, "1K": 0.067, "2K": 0.101, "4K": 0.151},
        "default_size": "1K",
    },
    "gemini-3-pro-image": {
        "aliases": ("pro", "nbp", "nano-banana-pro"),
        "sizes": ("1K", "2K", "4K"),
        "ratios": BASE_RATIOS,
        "thinking_config": False,
        "cost": {"1K": 0.134, "2K": 0.134, "4K": 0.24},
        "default_size": "1K",
    },
    "gemini-2.5-flash-image": {
        "aliases": ("legacy", "nb1", "nano-banana"),
        "sizes": (),  # fixed ~1024px output; no imageSize parameter
        "ratios": BASE_RATIOS,
        "thinking_config": False,
        "cost": {None: 0.039},
        "default_size": None,
    },
}

MIME_BY_EXT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
}
EXT_BY_MIME = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}


def log(msg):
    print(f"[nb-generate] {msg}", file=sys.stderr)


def die(msg, code):
    log(f"ERROR: {msg}")
    sys.exit(code)


def resolve_model(name):
    if name in MODELS:
        return name
    for model_id, spec in MODELS.items():
        if name.lower() in spec["aliases"]:
            return model_id
    if name.endswith("-preview"):
        log(f"WARNING: '{name}' is a deprecated preview id (shut down 2026-06-25). "
            f"Passing it through, but switch to the GA id.")
        return name
    log(f"NOTE: '{name}' is not a known image model; passing it through to the API.")
    return name


def validate_options(model_id, aspect, size, thinking_level):
    spec = MODELS.get(model_id)
    if spec is None:
        return size  # unknown model: trust the caller
    if aspect and aspect not in spec["ratios"]:
        extra = " (1:4/4:1/1:8/8:1 need gemini-3.1-flash-image)" if aspect in EXTREME_RATIOS else ""
        die(f"aspect {aspect} not supported by {model_id}{extra}. "
            f"Supported: {' '.join(sorted(spec['ratios']))}", 2)
    if size:
        if not spec["sizes"]:
            log(f"{model_id} has fixed ~1024px output; ignoring --size {size}")
            return None
        if size not in spec["sizes"]:
            die(f"size {size} not supported by {model_id}. Supported: {' '.join(spec['sizes'])}", 2)
    if thinking_level and not spec["thinking_config"]:
        die(f"--thinking-level is only configurable on gemini-3.1-flash-image", 2)
    return size


def encode_image(path):
    p = Path(path)
    if not p.is_file():
        die(f"input image not found: {path}", 2)
    mime = MIME_BY_EXT.get(p.suffix.lower())
    if mime is None:
        die(f"unsupported input image type '{p.suffix}': use png/jpg/webp/gif/bmp", 2)
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}}


def build_payload(args, model_id, size, image_parts):
    parts = [{"text": args.prompt}] + image_parts
    gen_cfg = {"responseModalities": ["TEXT", "IMAGE"]}
    image_cfg = {}
    if args.aspect:
        image_cfg["aspectRatio"] = args.aspect
    if size:
        image_cfg["imageSize"] = size
    if image_cfg:
        # imageConfig is the spelling the live endpoint accepts with string
        # values ("16:9", "2K"); the docs' newer responseFormat.image shape is
        # rejected today (enum mismatch). swap_image_config_spelling() handles
        # a future flip of that situation.
        gen_cfg["imageConfig"] = image_cfg
    if args.thinking_level:
        gen_cfg["thinkingConfig"] = {"thinkingLevel": args.thinking_level}
    payload = {"contents": [{"parts": parts}], "generationConfig": gen_cfg}
    if args.search_grounding:
        payload["tools"] = [{"google_search": {}}]
    return payload


def swap_image_config_spelling(payload, message):
    """The API is mid-migration between two spellings of the image format
    config (generationConfig.imageConfig vs generationConfig.responseFormat.
    image). If the endpoint rejected the one we sent, swap to the other."""
    relevant = any(t in message for t in (
        "imageConfig", "image_config", "responseFormat", "response_format",
        "Unknown name", "Invalid value"))
    if not relevant:
        return None
    alt = json.loads(json.dumps(payload))
    cfg = alt["generationConfig"]
    if "imageConfig" in cfg:
        cfg["responseFormat"] = {"image": cfg.pop("imageConfig")}
        return alt
    if "responseFormat" in cfg:
        cfg["imageConfig"] = cfg.pop("responseFormat")["image"]
        return alt
    return None


def parse_retry_after(value, fallback):
    if not value:
        return fallback
    try:
        return min(float(value), 120.0)
    except ValueError:
        try:  # RFC 7231 HTTP-date form, e.g. "Wed, 21 Oct 2026 07:28:00 GMT"
            from datetime import datetime, timezone
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(value)
            return min(max(0.0, (dt - datetime.now(timezone.utc)).total_seconds()), 120.0)
        except Exception:
            return fallback


def http_error_details(err):
    try:
        body = json.loads(err.read().decode())
        e = body.get("error", {})
        return e.get("status", ""), e.get("message", str(err))
    except Exception:
        return "", str(err)


def call_api(model_id, payload, api_key, timeout):
    """Returns (response, retry_count, payload) — the payload comes back so a
    config-spelling swap persists across multi-image (-n) runs."""
    url = f"{BASE_URL}/{API_VERSION}/models/{model_id}:generateContent"
    attempts = 0
    tried_alt = False
    while True:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode()), attempts, payload
        except urllib.error.HTTPError as err:
            status, message = http_error_details(err)
            if err.code == 400 and ("API key not valid" in message or "API_KEY_INVALID" in message):
                die(f"API key rejected ({status}): {message}\n"
                    f"  Regenerate at https://aistudio.google.com/apikey", 6)
            if err.code == 400 and not tried_alt:
                alt = swap_image_config_spelling(payload, message)
                if alt:
                    log("endpoint rejected the image config spelling; retrying with the alternate shape")
                    payload, tried_alt = alt, True
                    continue
            if err.code in (401, 403):
                die(f"auth failed ({err.code} {status}): {message}\n"
                    f"  Check GEMINI_API_KEY — create one at https://aistudio.google.com/apikey", 6)
            if err.code == 429:
                if attempts >= 3:
                    die(f"quota exhausted after retries ({status}): {message}\n"
                        f"  Image models are NOT on the API free tier — the key's project "
                        f"needs billing enabled (Tier 1+). https://ai.google.dev/gemini-api/docs/pricing", 7)
            elif err.code in (500, 503, 504):
                if attempts >= 3:
                    die(f"server error after retries ({err.code} {status}): {message}", 1)
            else:
                die(f"API error {err.code} {status}: {message}", 1)
            attempts += 1
            delay = parse_retry_after(err.headers.get("Retry-After"), 2.0 * (2 ** attempts))
            log(f"HTTP {err.code} — retry {attempts}/3 in {delay:.0f}s")
            time.sleep(delay)
        except urllib.error.URLError as err:
            die(f"network error reaching {BASE_URL}: {err.reason}", 5)
        except (TimeoutError, OSError) as err:
            die(f"network error reaching {BASE_URL}: {err}", 5)


def extract_outputs(response):
    """Return (image_parts, text_chunks), skipping interim 'thought' parts."""
    images, texts = [], []
    for cand in response.get("candidates", [])[:1]:
        for part in cand.get("content", {}).get("parts", []):
            if part.get("thought"):
                continue
            blob = part.get("inlineData") or part.get("inline_data")
            if blob:
                images.append(blob)
            elif part.get("text"):
                texts.append(part["text"])
    return images, texts


def slugify(text, limit=40):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-") or "image"


KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "NANOBANANA_API_KEY")
KEY_FILE = Path.home() / ".gemini" / ".env"  # written by nb-cli-setup.sh --set-key


def load_api_key():
    """Environment first, then ~/.gemini/.env (the one key file both this
    script and gemini-cli read). Never store keys in the skill folder — skill
    dirs are typically tracked in git and often public."""
    for name in KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name]
    if KEY_FILE.is_file():
        try:
            for line in KEY_FILE.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                v = v.strip().strip('"').strip("'")
                if k.strip() in KEY_NAMES and v:
                    return v
        except OSError:
            pass
    return None


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--prompt-file")
    ap.add_argument("-m", "--model", default="flash")
    ap.add_argument("-a", "--aspect")
    ap.add_argument("-s", "--size")
    ap.add_argument("-i", "--image", action="append", default=[])
    ap.add_argument("-n", "--count", type=int, default=1)
    ap.add_argument("-o", "--out", default="./nanobanana-output")
    ap.add_argument("--name")
    ap.add_argument("--thinking-level", choices=["minimal", "high"])
    ap.add_argument("--search-grounding", action="store_true")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    args = ap.parse_args()

    if args.help or (not args.prompt and not args.prompt_file):
        print(__doc__)
        sys.exit(0 if args.help else 2)
    if args.prompt and args.prompt_file:
        die("give PROMPT or --prompt-file, not both", 2)
    if args.prompt_file:
        try:
            args.prompt = Path(args.prompt_file).read_text().strip()
        except OSError as err:
            die(f"cannot read prompt file: {err}", 2)
    if not (args.prompt or "").strip():
        die("prompt is empty", 2)
    if args.count < 1 or args.count > 8:
        die("--count must be 1-8", 2)
    if len(args.image) > 14:
        die("at most 14 input/reference images are supported", 2)
    if args.size:
        args.size = args.size.upper()
    if args.aspect and not re.fullmatch(r"\d+:\d+", args.aspect):
        die(f"--aspect must look like W:H (got '{args.aspect}')", 2)

    model_id = resolve_model(args.model)
    spec = MODELS.get(model_id, {})
    size = args.size or spec.get("default_size")
    size = validate_options(model_id, args.aspect, size, args.thinking_level)

    image_parts = [encode_image(p) for p in args.image]
    payload = build_payload(args, model_id, size, image_parts)

    if args.dry_run:
        preview = json.loads(json.dumps(payload))
        for part in preview["contents"][0]["parts"]:
            if "inline_data" in part:
                part["inline_data"]["data"] = f"<base64 {len(part['inline_data']['data'])} chars>"
        print(json.dumps({"model": model_id, "url":
                          f"{BASE_URL}/{API_VERSION}/models/{model_id}:generateContent",
                          "payload": preview}, indent=2))
        sys.exit(0)

    api_key = load_api_key()
    if not api_key:
        die("no API key found. export GEMINI_API_KEY=... or store one with "
            "nb-cli-setup.sh --set-key  "
            "(create a key at https://aistudio.google.com/apikey — billing required for image models)", 6)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.name or slugify(args.prompt)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    per_image = spec.get("cost", {}).get(size if spec.get("sizes") else None)

    saved, texts_all, attempts_total = [], [], 0
    for n in range(args.count):
        log(f"generating {n + 1}/{args.count} with {model_id}"
            + (f" ({args.aspect or 'default'} @ {size})" if spec else ""))
        response, attempts, payload = call_api(model_id, payload, api_key, args.timeout)
        attempts_total += attempts
        images, texts = extract_outputs(response)
        texts_all.extend(texts)
        if not images:
            fb = response.get("promptFeedback", {})
            reason = fb.get("blockReason") or (response.get("candidates") or [{}])[0].get("finishReason")
            log(f"WARNING: no image returned (reason: {reason or 'unknown'}). "
                f"Rephrase the prompt if it was safety-blocked.")
            continue
        for i, blob in enumerate(images):
            ext = EXT_BY_MIME.get(blob.get("mimeType", "image/png"), "png")
            suffix = f"-{n + 1}" if args.count > 1 else ""
            suffix += f"-{i + 1}" if len(images) > 1 else ""
            path = out_dir / f"{base}-{stamp}{suffix}.{ext}"
            k = 2
            while path.exists():  # same prompt + same second must not clobber
                path = out_dir / f"{base}-{stamp}{suffix}-{k}.{ext}"
                k += 1
            path.write_bytes(base64.b64decode(blob["data"]))
            saved.append(str(path))
            log(f"saved {path}")

    if not saved:
        die("no images were produced", 1)
    cost = round(per_image * len(saved), 4) if per_image else None
    if cost is not None:
        log(f"estimated cost: ${cost} ({len(saved)} image(s) @ ${per_image})")
    for t in texts_all:
        log(f"model note: {t.strip()[:500]}")
    if args.as_json:
        print(json.dumps({"files": saved, "model": model_id, "aspect": args.aspect,
                          "size": size, "count": len(saved), "estimated_cost_usd": cost,
                          "retries": attempts_total, "text": " ".join(texts_all)[:2000]}))
    else:
        for p in saved:
            print(p)


if __name__ == "__main__":
    main()
