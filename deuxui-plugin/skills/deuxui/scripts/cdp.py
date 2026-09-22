#!/usr/bin/env python3
"""A minimal Chrome DevTools Protocol client, stdlib only.

  cdp.py --list
  cdp.py --call Emulation.setEmulatedMedia --params '{"features":[...]}'
  cdp.py --eval 'document.title'
  cdp.py --forced-colors active --probe scripts/checks/browser/forcedcolors.js

Why this exists. agent-browser drives everything deuxui needs except two things,
and both are CDP-only: `Emulation.setEmulatedMedia` with a `forced-colors`
feature, and loading a script into the page from a file. R-FORCED-COLORS was
declared unimplemented with the reason "the driver cannot emulate forced-colors",
which was true of the driver and not true of the browser behind it -- agent-browser
publishes its own CDP endpoint through `get cdp-url`, so the capability was
reachable the whole time. A detector reporting NOT_RUN because nobody looked for
the mechanism is the same defect as a documented mechanism with nothing behind it,
seen from the other side.

WebSocket is implemented here rather than imported because the skill's dependency
floor is python3 + pyyaml and a detector is not worth raising it for. This speaks
exactly as much of RFC 6455 as CDP needs: a client handshake, masked text frames,
and reassembly of server frames including continuations and control frames.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, socket, struct, sys, urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WS:
    """Just enough RFC 6455 for CDP: text frames, client-masked, no extensions."""

    def __init__(self, url: str, timeout: float = 20.0):
        if not url.startswith("ws://"):
            raise ValueError(f"only ws:// is supported here, got {url!r}")
        rest = url[len("ws://"):]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
               f"Sec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("the server closed during the handshake")
            buf += chunk
        head, _, tail = buf.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise ConnectionError(f"handshake refused: {head.split(chr(13).encode())[0]!r}")
        expect = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        if expect.lower().encode() not in head.lower():
            raise ConnectionError("Sec-WebSocket-Accept did not match the key we sent")
        self._buf = bytearray(tail)
        self._next_id = 0

    # ---------------------------------------------------------------- framing
    def _send_frame(self, payload: bytes, opcode: int = 0x1):
        mask = os.urandom(4)
        n = len(payload)
        hdr = bytearray([0x80 | opcode])
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        hdr += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(hdr) + masked)

    def _fill(self, n: int):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("connection closed mid-frame")
            self._buf += chunk

    def _read_frame(self):
        self._fill(2)
        b0, b1 = self._buf[0], self._buf[1]
        fin, opcode = b0 & 0x80, b0 & 0x0F
        ln = b1 & 0x7F
        off = 2
        if ln == 126:
            self._fill(4)
            ln = struct.unpack(">H", self._buf[2:4])[0]
            off = 4
        elif ln == 127:
            self._fill(10)
            ln = struct.unpack(">Q", self._buf[2:10])[0]
            off = 10
        if b1 & 0x80:                      # a server frame must not be masked
            self._fill(off + 4)
            off += 4
        self._fill(off + ln)
        payload = bytes(self._buf[off:off + ln])
        del self._buf[:off + ln]
        return fin, opcode, payload

    def recv(self) -> str:
        """One complete text message, skipping control frames and joining
        continuations. CDP sends large Runtime.evaluate results fragmented, and a
        reader that assumed one frame per message truncated them."""
        parts = bytearray()
        while True:
            fin, opcode, payload = self._read_frame()
            if opcode == 0x8:
                raise ConnectionError("server sent close")
            if opcode == 0x9:              # ping -> pong, same payload
                self._send_frame(payload, 0xA)
                continue
            if opcode == 0xA:
                continue
            parts += payload
            if fin:
                return parts.decode("utf-8", "replace")

    # -------------------------------------------------------------------- CDP
    def call(self, method: str, params: dict | None = None, session=None) -> dict:
        self._next_id += 1
        mid = self._next_id
        msg = {"id": mid, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self._send_frame(json.dumps(msg).encode())
        while True:
            d = json.loads(self.recv())
            if d.get("id") == mid:
                if "error" in d:
                    raise RuntimeError(f"{method}: {d['error'].get('message')}")
                return d.get("result", {})
            # anything else is an event; CDP interleaves them freely

    def close(self):
        try:
            self._send_frame(b"", 0x8)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# ------------------------------------------------------------------ discovery
def browser_url() -> str | None:
    """The CDP endpoint agent-browser is already driving, via its own CLI."""
    import subprocess
    try:
        r = subprocess.run(["agent-browser", "get", "cdp-url"], capture_output=True,
                           text=True, timeout=60)
    except Exception:
        return None
    u = (r.stdout or "").strip().strip('"')
    return u if u.startswith("ws://") else None


def page_target(port: int, want: str | None = None) -> dict | None:
    """The page under test.

    `want` is the URL the caller was told to measure. Without it this returns the
    first non-chrome page, which is fine with one tab open and quietly wrong with
    several -- a probe reporting on whichever tab happened to be first is the
    exact dishonesty the rest of this tool exists to prevent. With `want`, only a
    matching target is returned, and no match returns None so the caller can say
    NOT_RUN instead of measuring something else."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as f:
            targets = json.loads(f.read())
    except Exception:
        return None
    pages = [t for t in targets if t.get("type") == "page"
             and not str(t.get("url", "")).startswith(("chrome://", "chrome-untrusted://",
                                                       "devtools://", "about:"))]
    if not want:
        return pages[0] if pages else None
    norm = want.rstrip("/")
    exact = [t for t in pages if str(t.get("url", "")).rstrip("/") == norm]
    if exact:
        return exact[0]
    # Same origin is close enough: a driver may have followed a redirect or added
    # a trailing path, and that is still the page under test.
    try:
        origin = "://".join(norm.split("://")[:1] + [norm.split("://", 1)[1].split("/")[0]])
    except IndexError:
        origin = norm
    same = [t for t in pages if str(t.get("url", "")).startswith(origin)]
    return same[0] if same else None


def connect_page(want: str | None = None):
    """(WS, target) for the page under test, or (None, reason)."""
    bu = browser_url()
    if not bu:
        return None, ("agent-browser is not running or did not report a CDP URL, so "
                      "nothing can be emulated. Open a page first.")
    try:
        port = int(bu.split("//")[1].split(":")[1].split("/")[0])
    except Exception:
        return None, f"could not read a port out of {bu!r}"
    t = page_target(port, want)
    if not t or not t.get("webSocketDebuggerUrl"):
        if want:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list",
                                            timeout=10) as f:
                    open_urls = [str(x.get("url", ""))[:70] for x in json.loads(f.read())
                                 if x.get("type") == "page"]
            except Exception:
                open_urls = []
            return None, (f"{want} is not open in the browser. Open tabs: "
                          + (", ".join(open_urls[:4]) or "none")
                          + ". Nothing was measured -- reporting on whichever tab "
                            "happened to be first would be a result about the wrong "
                            "page.")
        return None, ("no page target is open on the browser's CDP endpoint -- only "
                      "chrome:// tabs. Open the page under test first.")
    try:
        return WS(t["webSocketDebuggerUrl"]), t
    except Exception as e:
        return None, f"could not attach to the page target: {type(e).__name__}: {e}"


def evaluate(ws: WS, js: str):
    """The value of `js`, JSON-decoded when it is a JSON string."""
    r = ws.call("Runtime.evaluate", {"expression": js, "returnByValue": True,
                                     "awaitPromise": True})
    res = r.get("result", {})
    if r.get("exceptionDetails"):
        raise RuntimeError(res.get("description")
                           or r["exceptionDetails"].get("text", "evaluation threw"))
    v = res.get("value")
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def set_media(ws: WS, features: list[tuple[str, str]], media: str = ""):
    ws.call("Emulation.setEmulatedMedia",
            {"media": media,
             "features": [{"name": n, "value": v} for n, v in features]})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="page targets, as JSON")
    ap.add_argument("--call", help="a CDP method to call")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--eval", dest="js", help="JavaScript to evaluate in the page")
    ap.add_argument("--forced-colors", choices=["active", "none"],
                    help="emulate forced-colors before the probe, and reset after")
    ap.add_argument("--probe", help="a probe file to evaluate in the page")
    a = ap.parse_args(argv)

    if a.list:
        bu = browser_url()
        if not bu:
            sys.stderr.write("agent-browser reported no CDP URL\n")
            return 1
        port = int(bu.split("//")[1].split(":")[1].split("/")[0])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as f:
            print(json.dumps(json.loads(f.read()), indent=1))
        return 0

    ws, info = connect_page()
    if ws is None:
        sys.stderr.write(f"{info}\n")
        return 1
    try:
        if a.forced_colors:
            set_media(ws, [("forced-colors", a.forced_colors)])
        if a.call:
            print(json.dumps(ws.call(a.call, json.loads(a.params)), indent=1))
        if a.js:
            print(json.dumps(evaluate(ws, a.js), indent=1))
        if a.probe:
            print(json.dumps(evaluate(ws, Path(a.probe).read_text()), indent=1))
        if a.forced_colors:
            set_media(ws, [])              # never leave the page emulated
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
