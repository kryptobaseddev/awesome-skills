#!/usr/bin/env python3
"""sign_url.py — Sign a MoonPay widget URL (on-ramp / off-ramp / swap).

Python stdlib port of sign-url.js. MoonPay requires a `signature` whenever the
widget URL carries sensitive parameters (walletAddress, walletAddresses, email):
it proves the URL was built by YOUR server with YOUR secret key, so an attacker
cannot rewrite the destination wallet. Sign server-side ONLY — a secret key
(sk_live_… / sk_test_…) must never reach the browser.

Algorithm (dev.moonpay.com/widget/on-ramp/customization/url-signing):
    signature = base64( HMAC-SHA256( secret_key, urlparse(url).query_with_leading_? ) )
The signed string is the query string INCLUDING the leading "?", with no
existing `signature` param. The result is appended as the LAST query param,
URL-encoded.

Usage:
    python3 sign_url.py "https://buy-sandbox.moonpay.com?apiKey=pk_test_x&walletAddress=0x..."
        -> prints the full signed URL
    python3 sign_url.py "<url>" --raw            # print only raw base64 signature (for SDK updateSignature())
    python3 sign_url.py "<url>" --key sk_test_…  # pass the key explicitly

Secret key resolution: --key flag, else $MOONPAY_SECRET_KEY.

As a module:
    from sign_url import sign_moonpay_url, append_signature
    sig = sign_moonpay_url(url, os.environ["MOONPAY_SECRET_KEY"])
    signed = append_signature(url, sig)
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import os
import sys
from urllib.parse import urlsplit, quote


def sign_moonpay_url(url: str, secret_key: str) -> str:
    """Return the raw base64 HMAC-SHA256 signature (NOT URL-encoded)."""
    if not secret_key:
        raise ValueError("Missing MoonPay secret key (sk_test_… / sk_live_…).")
    if not (secret_key.startswith("sk_test_") or secret_key.startswith("sk_live_")):
        raise ValueError(
            f'Expected a secret key (sk_test_… / sk_live_…), got "{secret_key[:8]}…". '
            "Publishable keys (pk_…) cannot sign — and secret keys must never reach the browser."
        )
    query = urlsplit(url).query
    if not query:
        raise ValueError("URL has no query string to sign.")
    if "signature=" in query:
        raise ValueError("URL already contains a signature param — sign BEFORE appending it.")
    # MoonPay signs the query string INCLUDING the leading "?".
    signed_string = "?" + query
    digest = hmac.new(secret_key.encode(), signed_string.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def append_signature(url: str, signature: str) -> str:
    """Append a URL-encoded signature as the final query parameter (URL/iframe integrations)."""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}signature={quote(signature, safe='')}"


def main(argv: list[str]) -> int:
    positional = [a for a in argv if not a.startswith("--")]
    raw = "--raw" in argv
    secret_key = None
    if "--key" in argv:
        i = argv.index("--key")
        if i + 1 < len(argv):
            secret_key = argv[i + 1]
    secret_key = secret_key or os.environ.get("MOONPAY_SECRET_KEY")

    if not positional:
        print('usage: python3 sign_url.py "<widget-url>" [--raw] [--key sk_test_…]', file=sys.stderr)
        print("       secret key falls back to $MOONPAY_SECRET_KEY", file=sys.stderr)
        return 2
    url = positional[0]
    try:
        signature = sign_moonpay_url(url, secret_key)
        print(signature if raw else append_signature(url, signature))
        return 0
    except Exception as err:  # noqa: BLE001 - surface a clean CLI error
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
