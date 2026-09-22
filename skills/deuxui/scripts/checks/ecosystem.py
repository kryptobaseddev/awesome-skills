"""Surfaces that are not ordinary DOM: 3D canvases and rendered video.

A WebGL scene is a single opaque element to assistive technology, and a
Remotion composition has no interaction at all. Applying the same interaction
rules to both would produce confident nonsense, so these get their own checks
and the interaction families are marked NOT_APPLICABLE for them.
"""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")


@check("S-CANVAS-A11Y", exts=SRC, surfaces=("ui", "canvas3d"))
def canvas_alternative(f, p):
    """Canvas content does not exist for a screen reader. Whatever the scene
    conveys has to also exist as text, or the information is simply absent for
    part of the audience (A11Y-007, COMP-015)."""
    out = []
    for t in f.tags:
        if t.name.lower() not in ("canvas", "view3d"):
            continue
        has_fallback = bool(re.sub(r"<[^>]*>", "", t.inner or "").strip())
        if t.has("aria-label", "aria-labelledby", "role") or has_fallback:
            continue
        out.append(finding("S-CANVAS-A11Y", f, t.line, t.raw,
                           "Canvas with no accessible name and no fallback content. Put the "
                           "meaning in child content or an adjacent text summary -- a 3D "
                           "scene is invisible to assistive technology and to search.",
                           "high"))
    # React Three Fiber's <Canvas> renders a real canvas but takes no fallback children
    for t in f.tags:
        if t.name != "Canvas":
            continue
        win = f.text[max(0, t.start - 800):t.end + 800]
        if re.search(r"aria-label|role=|sr-only|VisuallyHidden|<figcaption", win):
            continue
        out.append(finding("S-CANVAS-A11Y", f, t.line, t.raw,
                           "React Three Fiber <Canvas> with no text equivalent nearby. Wrap "
                           "it in a figure with a caption, or provide a described summary of "
                           "what the scene shows.", "medium"))
    return out


@check("S-3D-PERF", exts=SRC, surfaces=("ui", "canvas3d"),
       requires=lambda p: any("three" in d or "@react-three" in d for d in p.deps))
def three_perf(f, p):
    """A continuously rendering WebGL canvas pins a GPU core and drains a
    phone battery even when nothing on screen is changing."""
    out = []
    for t in f.tags:
        if t.name != "Canvas":
            continue
        attrs = " ".join(f"{k}={v}" for k, v in t.attrs.items())
        missing = []
        if "frameloop" not in t.attrs:
            missing.append('frameloop="demand" when the scene is not continuously animating')
        if "dpr" not in t.attrs:
            missing.append("a dpr cap such as dpr={[1, 2]} so 3x phones do not render 9x pixels")
        if not missing:
            continue
        out.append(finding("S-3D-PERF", f, t.line, attrs[:120],
                           "3D canvas missing " + "; ".join(missing) +
                           ". Both are measured directly in INP and battery drain "
                           "(PERF-001, NUM-012).", "medium"))
    win = f.text
    if re.search(r"autoRotate|useFrame|OrbitControls", win) and not re.search(
            r"prefers-reduced-motion|useReducedMotion|motion-reduce", win):
        m = re.search(r"autoRotate|useFrame|OrbitControls", win)
        out.append(finding("S-3D-PERF", f, win[:m.start()].count("\n") + 1, m.group(0),
                           "Continuous 3D motion with no reduced-motion path. Constant "
                           "movement is a vestibular trigger; offer a still frame "
                           "(LAY-010, A11Y-010).", "medium"))
    return out


@check("S-MEDIA-CAPTIONS", exts=SRC, surfaces=("ui", "video"))
def video_captions(f, p):
    out = []
    for t in f.tags:
        if t.name.lower() != "video":
            continue
        inner = t.inner or ""
        if "kind=\"captions\"" in inner or "kind='captions'" in inner or "<track" in inner:
            continue
        if t.has("muted") and t.has("loop") and not t.has("controls"):
            continue                    # decorative background loop, no audio to caption
        out.append(finding("S-MEDIA-CAPTIONS", f, t.line, t.raw,
                           "Video with no caption track. Captions are required for "
                           "prerecorded audio content and are what most people use to watch "
                           "in public (A11Y-007).", "high"))
    return out


@check("S-VIDEO-LEGIBILITY", exts=SRC, surfaces=("video",))
def burned_in_text(f, p):
    """Remotion burns text into pixels. There is no browser zoom, no reflow and
    no selection, so the type has to be legible at the delivered resolution and
    on-screen long enough to read."""
    out = []
    for m in re.finditer(r"fontSize\s*:\s*(\d+)", f.text):
        px = int(m.group(1))
        if px >= 28:
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-VIDEO-LEGIBILITY", f, line, m.group(0),
                           f"{px}px in a composition is tiny once the video is scaled down on "
                           "a phone or compressed by a platform. Burned-in text cannot be "
                           "zoomed -- size it for the smallest playback surface.", "medium"))
    for m in re.finditer(r"durationInFrames\s*[:=]\s*(\d+)", f.text):
        frames = int(m.group(1))
        if frames >= 45:
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-VIDEO-LEGIBILITY", f, line, m.group(0),
                           f"{frames} frames is under ~1.5s at 30fps. Viewers cannot read a "
                           "caption that is gone before they finish the first line.", "low"))
    return out
