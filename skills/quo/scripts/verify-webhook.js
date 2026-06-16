#!/usr/bin/env node
/**
 * verify-webhook.js — Verify a Quo (formerly OpenPhone) BETA webhook signature.
 *
 * Quo's beta webhooks are Standard-Webhooks / Svix-compatible. Each delivery
 * carries three headers:
 *   webhook-id          a stable delivery id (use it for idempotency)
 *   webhook-timestamp   unix seconds when Quo signed the request
 *   webhook-signature   space-separated list of "v1,<base64sig>" entries
 *
 * The signature is HMAC-SHA256, base64-encoded, over the EXACT string
 *   `${webhook-id}.${webhook-timestamp}.${rawBody}`
 * keyed by the per-webhook signing secret returned (as `data.key`, prefixed
 * `whsec_`) when you create or rotate the webhook. For manual verification you
 * strip the `whsec_` prefix and base64-DECODE the remainder to get the key
 * bytes. (The Svix SDK takes `whsec_…` verbatim instead.)
 *
 * CRITICAL: verify against the RAW request body bytes, before any JSON parse.
 * If a body-parser re-serializes the JSON first, the HMAC will not match.
 *
 * Usage:
 *   import { verifyQuoWebhook } from "./verify-webhook.js";
 *   const ok = verifyQuoWebhook(req.headers, rawBodyBuffer, process.env.QUO_WEBHOOK_KEY);
 *
 *   node verify-webhook.js --selftest    # round-trip the algorithm (no network)
 *
 * Source: https://www.quo.com/docs/mdx/beta/webhooks-signature-validation.md
 */
import crypto from 'node:crypto';

const DEFAULT_TOLERANCE_SECONDS = 5 * 60; // reject deliveries older/newer than this (replay protection)

/** Turn a `whsec_…` (or bare base64) secret into raw HMAC key bytes. */
export function quoSecretToKeyBytes(secret) {
  const s = String(secret || '');
  const b64 = s.startsWith('whsec_') ? s.slice('whsec_'.length) : s;
  return Buffer.from(b64, 'base64');
}

/** Compute the canonical base64 HMAC-SHA256 signature for a delivery. */
export function signQuoWebhook({ id, timestamp, body }, secret) {
  const keyBytes = quoSecretToKeyBytes(secret);
  const rawBody = Buffer.isBuffer(body) ? body.toString('utf8') : String(body);
  const signedContent = `${id}.${timestamp}.${rawBody}`;
  return crypto.createHmac('sha256', keyBytes).update(signedContent).digest('base64');
}

/** Pull `webhook-*` values out of a headers object (case-insensitive). */
function readHeaders(headers) {
  const get = (name) => {
    if (!headers) return undefined;
    if (typeof headers.get === 'function') return headers.get(name); // Fetch/Headers
    const lower = name.toLowerCase();
    const hit = Object.keys(headers).find((k) => k.toLowerCase() === lower);
    return hit ? headers[hit] : undefined;
  };
  return {
    id: get('webhook-id'),
    timestamp: get('webhook-timestamp'),
    signature: get('webhook-signature'),
  };
}

/** Extract the base64 signatures from a "v1,<sig> v1,<sig>" header value. */
function parseSignatureHeader(value) {
  return String(value || '')
    .split(' ')
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const comma = entry.indexOf(',');
      const version = comma === -1 ? '' : entry.slice(0, comma);
      const sig = comma === -1 ? entry : entry.slice(comma + 1);
      return version === 'v1' ? sig : undefined;
    })
    .filter(Boolean);
}

function timingSafeEqualStr(a, b) {
  const ba = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  return ba.length === bb.length && crypto.timingSafeEqual(ba, bb);
}

/**
 * Verify a Quo beta webhook. Returns true only if a provided signature matches
 * AND the timestamp is within tolerance.
 *
 * @param headers  the inbound headers (Node req.headers, a plain object, or a
 *                 Fetch Headers instance), OR a {id,timestamp,signature} object.
 * @param rawBody  the EXACT raw request body (Buffer or string).
 * @param secret   the `whsec_…` signing secret from create/rotate.
 * @param opts     { toleranceSeconds = 300 }
 */
export function verifyQuoWebhook(headers, rawBody, secret, opts = {}) {
  const tolerance = opts.toleranceSeconds ?? DEFAULT_TOLERANCE_SECONDS;
  const { id, timestamp, signature } =
    headers && headers.signature !== undefined && headers.id !== undefined
      ? headers
      : readHeaders(headers);

  if (!id || !timestamp || !signature || !secret) return false;

  const ts = Number(timestamp);
  const now = Math.floor(Date.now() / 1000);
  if (!Number.isFinite(ts) || Math.abs(now - ts) > tolerance) return false;

  const expected = signQuoWebhook({ id, timestamp, body: rawBody }, secret);
  const provided = parseSignatureHeader(signature);
  return provided.some((sig) => timingSafeEqualStr(sig, expected));
}

// ── CLI self-test: prove the algorithm round-trips without any network ────────
if (import.meta.url === `file://${process.argv[1]}`) {
  const arg = process.argv[2];
  if (arg === '--selftest') {
    const secret = 'whsec_' + Buffer.from('quo-selftest-key-0123456789').toString('base64');
    const id = 'msg_2abcDEFghiJKLmnoPQRstu';
    const timestamp = String(Math.floor(Date.now() / 1000));
    const body = JSON.stringify({ id: 'EV123', type: 'message.received', data: { resource: { text: 'hi' } } });
    const sig = signQuoWebhook({ id, timestamp, body }, secret);
    const headers = { 'webhook-id': id, 'webhook-timestamp': timestamp, 'webhook-signature': `v1,${sig}` };

    const good = verifyQuoWebhook(headers, body, secret);
    const tampered = verifyQuoWebhook(headers, body + ' ', secret);
    const wrongKey = verifyQuoWebhook(headers, body, 'whsec_' + Buffer.from('other').toString('base64'));
    const rotation = verifyQuoWebhook(
      { ...headers, 'webhook-signature': `v1,deadbeef v1,${sig}` }, body, secret,
    );
    const stale = verifyQuoWebhook(
      { ...headers, 'webhook-timestamp': String(Number(timestamp) - 999) }, body, secret,
    );

    const pass = good && rotation && !tampered && !wrongKey && !stale;
    console.log(`valid signature      -> ${good}        (expect true)`);
    console.log(`accepts in rotation  -> ${rotation}        (expect true — multiple v1, entries)`);
    console.log(`tampered body        -> ${tampered}       (expect false)`);
    console.log(`wrong secret         -> ${wrongKey}       (expect false)`);
    console.log(`stale timestamp      -> ${stale}       (expect false)`);
    console.log(pass ? '\n✓ self-test passed' : '\n✗ self-test FAILED');
    process.exit(pass ? 0 : 1);
  } else {
    console.log('Usage: node verify-webhook.js --selftest');
    console.log('  Or import { verifyQuoWebhook } from "./verify-webhook.js"');
    process.exit(2);
  }
}
