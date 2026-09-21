#!/usr/bin/env python3
"""The fixture server. Serves the directory, and delays one endpoint on purpose.

  serve.py [port]

`/slow-data.json` sleeps before answering. Without a genuinely slow response
R-STATE-SLOW cannot be tested: `Network.emulateNetworkConditions` does not throttle
localhost reliably, so a 200-byte local file arrives before the first sample and
the probe correctly -- and uselessly -- reports that there was no waiting state to
judge. A real delay is the only way to prove the failing path as well as the
passing one.
"""
from __future__ import annotations
import sys, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DELAY_S = 2.5


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(Path(__file__).resolve().parent), **kw)

    def do_GET(self):
        if self.path.startswith("/slow-data.json"):
            time.sleep(DELAY_S)
            body = b'{"items":[{"id":1,"name":"First"},{"id":2,"name":"Second"}]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
