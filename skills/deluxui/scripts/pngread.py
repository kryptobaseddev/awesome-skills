"""An 8-bit non-interlaced PNG decoder, stdlib only.

agent-browser writes exactly this form (colour type 2 or 6, depth 8, no
interlacing), which is why a full decoder is unnecessary. Anything else returns
None and the caller reports what it found rather than guessing at the bytes.

Kept in its own module because two things read pixels now -- R-PIXEL-CONTRAST in
ux_report.py and comp_spec.py -- and a second copy of a filter loop is a second
place for the Paeth predictor to be subtly wrong.
"""
from __future__ import annotations
import struct, sys, zlib
from pathlib import Path

sys.dont_write_bytecode = True


def rows(path: Path):
    """(width, height, channels, bytearray of samples) or None."""
    try:
        d = Path(path).read_bytes()
    except OSError:
        return None
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, w, h, ctype, idat = 8, 0, 0, 0, bytearray()
    while pos + 8 <= len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        typ = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype, _c, _f, inter = struct.unpack(">IIBBBBB", body[:13])
            if depth != 8 or ctype not in (2, 6) or inter != 0:
                return None
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if not w or not idat:
        return None
    ch = 3 if ctype == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = w * ch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    i = 0
    for y in range(h):
        ft = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        if ft == 1:
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 0xFF
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif ft == 3:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif ft == 4:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return (w, h, ch, out)


def text_chunks(path: Path) -> dict:
    """Any tEXt keyword/value pairs in the file -- where provenance lives."""
    try:
        d = Path(path).read_bytes()
    except OSError:
        return {}
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return {}
    out, pos = {}, 8
    while pos + 8 <= len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        typ = d[pos + 4:pos + 8]
        if typ == b"tEXt":
            body = d[pos + 8:pos + 8 + ln]
            k, _, v = body.partition(b"\x00")
            out[k.decode("latin-1")] = v.decode("latin-1")
        elif typ == b"iTXt":
            body = d[pos + 8:pos + 8 + ln]
            parts = body.split(b"\x00", 5)
            if len(parts) >= 6:
                out[parts[0].decode("latin-1")] = parts[5].decode("utf-8", "replace")
        elif typ == b"IEND":
            break
        pos += 12 + ln
    return out


def add_text(path: Path, key: str, value: str) -> bool:
    """Write a tEXt chunk before IEND, preserving everything else.

    Generation context is part of the asset. A prompt recorded in a sidecar gets
    separated from its image the first time somebody moves a file; a prompt inside
    the PNG travels with it.
    """
    p = Path(path)
    try:
        d = p.read_bytes()
    except OSError:
        return False
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    payload = key.encode("latin-1", "replace") + b"\x00" + value.encode("latin-1", "replace")
    chunk = (struct.pack(">I", len(payload)) + b"tEXt" + payload
             + struct.pack(">I", zlib.crc32(b"tEXt" + payload) & 0xFFFFFFFF))
    idx = d.rfind(b"\x00\x00\x00\x00IEND")
    if idx < 0:
        return False
    p.write_bytes(d[:idx] + chunk + d[idx:])
    return True
