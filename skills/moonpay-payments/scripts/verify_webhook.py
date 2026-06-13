#!/usr/bin/env python3
"""verify_webhook.py — Verify a MoonPay webhook signature (Moonpay-Signature-V2).

Python stdlib port of verify-webhook.js. MoonPay signs every webhook so you can
prove the request came from MoonPay before acting on it (e.g. marking an order
paid). Skipping verification lets anyone POST a forged "completed" event.

Scheme (dev.moonpay.com/api-reference/widget/webhooks/signature):
    Header:  Moonpay-Signature-V2: t=<unix-ts>,s=<hex-hmac>
    signed   = f"{t}.{raw_body}"     (POST: raw JSON body; GET: the "?query" string)
    expected = hex( HMAC-SHA256( webhook_key, signed ) )
    secret   = your account's WEBHOOK key from dashboard.moonpay.com/developers
               (distinct from the sk_… secret API key)

CRITICAL: verify against the RAW request body bytes exactly as received. If your
framework re-serializes parsed JSON, the HMAC will not match. In FastAPI/Flask,
read request.body() / request.get_data() — do not re-dump the parsed dict.

As a module:
    from verify_webhook import verify_moonpay_webhook
    ok = verify_moonpay_webhook(
        request.headers["Moonpay-Signature-V2"], raw_body,
        os.environ["MOONPAY_WEBHOOK_KEY"], tolerance_seconds=300,
    )

CLI (for testing a captured request):
    MOONPAY_WEBHOOK_KEY=wk_… python3 verify_webhook.py \
        --sig "t=1492774577,s=5257a8…" --body '{"data":{...}}'
"""
from __future__ import annotations

import hmac
import hashlib
import os
import sys
import time


def parse_signature_header(header: str) -> tuple[str, str]:
    if not header:
        raise ValueError("Missing Moonpay-Signature-V2 header.")
    parts: dict[str, str] = {}
    for segment in header.split(","):
        if "=" not in segment:
            continue
        k, _, v = segment.partition("=")
        parts[k.strip()] = v.strip()
    if "t" not in parts or "s" not in parts:
        raise ValueError('Malformed Moonpay-Signature-V2 header (expected "t=…,s=…").')
    return parts["t"], parts["s"]


def verify_moonpay_webhook(
    header: str,
    raw_body: str | bytes,
    webhook_key: str,
    tolerance_seconds: int | None = None,
) -> bool:
    """Return True only if the signature is valid (and fresh, if tolerance set)."""
    if not webhook_key:
        raise ValueError("Missing webhook signing key.")
    timestamp, signature = parse_signature_header(header)
    body = raw_body.decode() if isinstance(raw_body, (bytes, bytearray)) else str(raw_body)

    signed_payload = f"{timestamp}.{body}"
    expected = hmac.new(webhook_key.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return False

    if tolerance_seconds is not None:
        try:
            age = abs(time.time() - float(timestamp))
        except ValueError:
            return False
        if age > tolerance_seconds:
            return False
    return True


def main(argv: list[str]) -> int:
    def get(flag: str) -> str | None:
        return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None

    sig = get("--sig")
    body = get("--body") or ""
    key = get("--key") or os.environ.get("MOONPAY_WEBHOOK_KEY")
    if not sig or not key:
        print('usage: python3 verify_webhook.py --sig "t=…,s=…" --body \'<raw-body>\' [--key wk_…]', file=sys.stderr)
        print("       webhook key falls back to $MOONPAY_WEBHOOK_KEY", file=sys.stderr)
        return 2
    try:
        ok = verify_moonpay_webhook(sig, body, key, tolerance_seconds=300)
        print("VALID" if ok else "INVALID")
        return 0 if ok else 1
    except Exception as err:  # noqa: BLE001
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
