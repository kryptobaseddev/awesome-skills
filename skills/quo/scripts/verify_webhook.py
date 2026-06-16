#!/usr/bin/env python3
"""verify_webhook.py — Verify a Quo (formerly OpenPhone) BETA webhook signature.

Quo's beta webhooks are Standard-Webhooks / Svix-compatible. Each delivery sends
three headers:
    webhook-id          a stable delivery id (use it for idempotency)
    webhook-timestamp   unix seconds when Quo signed the request
    webhook-signature   space-separated list of "v1,<base64sig>" entries

The signature is HMAC-SHA256, base64-encoded, over the EXACT string
    f"{webhook_id}.{webhook_timestamp}.{raw_body}"
keyed by the per-webhook secret returned (as data.key, prefixed "whsec_") when
you create or rotate the webhook. For manual verification, strip the "whsec_"
prefix and base64-DECODE the remainder to get the key bytes.

CRITICAL: verify against the RAW request body bytes, before any JSON parse —
e.g. Flask `request.get_data()` (NOT `request.get_json()`),
FastAPI `await request.body()`.

Usage:
    from verify_webhook import verify_quo_webhook
    ok = verify_quo_webhook(request.headers, raw_body_bytes, os.environ["QUO_WEBHOOK_KEY"])

    python3 verify_webhook.py --selftest   # round-trip the algorithm (no network)

Source: https://www.quo.com/docs/mdx/beta/webhooks-signature-validation.md
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

DEFAULT_TOLERANCE_SECONDS = 5 * 60  # replay protection window


def quo_secret_to_key_bytes(secret: str) -> bytes:
    """Turn a 'whsec_…' (or bare base64) secret into raw HMAC key bytes."""
    s = secret or ""
    b64 = s[len("whsec_"):] if s.startswith("whsec_") else s
    return base64.b64decode(b64)


def sign_quo_webhook(webhook_id: str, timestamp, body, secret: str) -> str:
    """Compute the canonical base64 HMAC-SHA256 signature for a delivery."""
    raw = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)
    signed_content = f"{webhook_id}.{timestamp}.{raw}".encode("utf-8")
    key = quo_secret_to_key_bytes(secret)
    digest = hmac.new(key, signed_content, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _get_header(headers, name: str):
    if headers is None:
        return None
    # Works for dicts and framework header objects (case-insensitive get).
    getter = getattr(headers, "get", None)
    if callable(getter):
        val = headers.get(name)
        if val is not None:
            return val
    lower = name.lower()
    try:
        for k, v in headers.items():
            if k.lower() == lower:
                return v
    except AttributeError:
        pass
    return None


def _parse_signature_header(value: str):
    sigs = []
    for entry in str(value or "").split(" "):
        entry = entry.strip()
        if not entry:
            continue
        version, _, sig = entry.partition(",")
        if version == "v1" and sig:
            sigs.append(sig)
    return sigs


def verify_quo_webhook(headers, raw_body, secret: str,
                       tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS) -> bool:
    """Verify a Quo beta webhook. True only if a signature matches AND the
    timestamp is within tolerance.

    `headers` may be a dict, a framework headers object, or a tuple/dict already
    holding {id, timestamp, signature}.
    """
    if isinstance(headers, dict) and {"id", "timestamp", "signature"} <= set(headers):
        webhook_id = headers["id"]
        timestamp = headers["timestamp"]
        signature = headers["signature"]
    else:
        webhook_id = _get_header(headers, "webhook-id")
        timestamp = _get_header(headers, "webhook-timestamp")
        signature = _get_header(headers, "webhook-signature")

    if not (webhook_id and timestamp and signature and secret):
        return False

    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - ts) > tolerance_seconds:
        return False

    expected = sign_quo_webhook(webhook_id, timestamp, raw_body, secret)
    for sig in _parse_signature_header(signature):
        if hmac.compare_digest(sig, expected):
            return True
    return False


def _selftest() -> int:
    secret = "whsec_" + base64.b64encode(b"quo-selftest-key-0123456789").decode()
    wid = "msg_2abcDEFghiJKLmnoPQRstu"
    ts = str(int(time.time()))
    body = '{"id":"EV123","type":"message.received","data":{"resource":{"text":"hi"}}}'
    sig = sign_quo_webhook(wid, ts, body, secret)
    headers = {"webhook-id": wid, "webhook-timestamp": ts, "webhook-signature": f"v1,{sig}"}

    good = verify_quo_webhook(headers, body, secret)
    rotation = verify_quo_webhook({**headers, "webhook-signature": f"v1,deadbeef v1,{sig}"}, body, secret)
    tampered = verify_quo_webhook(headers, body + " ", secret)
    wrong_key = verify_quo_webhook(headers, body, "whsec_" + base64.b64encode(b"other").decode())
    stale = verify_quo_webhook({**headers, "webhook-timestamp": str(int(ts) - 999)}, body, secret)

    ok = good and rotation and not tampered and not wrong_key and not stale
    print(f"valid signature      -> {good}        (expect True)")
    print(f"accepts in rotation  -> {rotation}        (expect True — multiple v1, entries)")
    print(f"tampered body        -> {tampered}       (expect False)")
    print(f"wrong secret         -> {wrong_key}       (expect False)")
    print(f"stale timestamp      -> {stale}       (expect False)")
    print("\n✓ self-test passed" if ok else "\n✗ self-test FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        raise SystemExit(_selftest())
    print("Usage: python3 verify_webhook.py --selftest")
    print('  Or: from verify_webhook import verify_quo_webhook')
    raise SystemExit(2)
