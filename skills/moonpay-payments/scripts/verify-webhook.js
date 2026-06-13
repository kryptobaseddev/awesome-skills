#!/usr/bin/env node
/**
 * verify-webhook.js — Verify a MoonPay webhook signature (Moonpay-Signature-V2).
 *
 * MoonPay signs every webhook so you can prove the request really came from
 * MoonPay before you act on it (e.g. mark an order paid). Skipping this lets
 * anyone POST a fake "transaction completed" to your endpoint.
 *
 * Scheme (dev.moonpay.com/api-reference/widget/webhooks/signature):
 *   Header:  Moonpay-Signature-V2: t=<unix-ts>,s=<hex-hmac>
 *   signed   = `${t}.${rawBody}`        (POST: raw JSON body; GET: the "?query" string)
 *   expected = hex( HMAC-SHA256( webhookKey, signed ) )
 *   secret   = your account's WEBHOOK key from dashboard.moonpay.com/developers
 *              (this is distinct from the sk_… secret API key)
 *
 * CRITICAL: verify against the RAW request body bytes, exactly as received.
 * If your framework re-serializes parsed JSON (key order, spacing) the HMAC
 * will not match. In Express, capture the raw body:
 *   app.use('/webhooks/moonpay', express.raw({ type: '*\/*' }));
 *
 * As a module:
 *   const { verifyMoonPayWebhook } = require('./verify-webhook.js');
 *   const ok = verifyMoonPayWebhook(req.headers['moonpay-signature-v2'], rawBody,
 *                                   process.env.MOONPAY_WEBHOOK_KEY, { toleranceSeconds: 300 });
 *
 * CLI (for testing a captured request):
 *   MOONPAY_WEBHOOK_KEY=wk_… node verify-webhook.js \
 *     --sig "t=1492774577,s=5257a8…" --body '{"data":{...}}'
 */
'use strict';

const crypto = require('crypto');

function parseSignatureHeader(header) {
  if (!header || typeof header !== 'string') {
    throw new Error('Missing Moonpay-Signature-V2 header.');
  }
  const parts = {};
  for (const segment of header.split(',')) {
    const i = segment.indexOf('=');
    if (i === -1) continue;
    parts[segment.slice(0, i).trim()] = segment.slice(i + 1).trim();
  }
  if (!parts.t || !parts.s) {
    throw new Error('Malformed Moonpay-Signature-V2 header (expected "t=…,s=…").');
  }
  return { timestamp: parts.t, signature: parts.s };
}

/**
 * @param {string} header  The Moonpay-Signature-V2 header value.
 * @param {string|Buffer} rawBody  The EXACT raw request body (or "?query" for GET webhooks).
 * @param {string} webhookKey  Your dashboard webhook signing key.
 * @param {{toleranceSeconds?: number}} [opts]  Reject signatures older than N seconds (replay defense).
 * @returns {boolean} true only if the signature is valid (and fresh, if tolerance set).
 */
function verifyMoonPayWebhook(header, rawBody, webhookKey, opts = {}) {
  if (!webhookKey) throw new Error('Missing webhook signing key.');
  const { timestamp, signature } = parseSignatureHeader(header);
  const body = Buffer.isBuffer(rawBody) ? rawBody.toString('utf8') : String(rawBody);

  const signedPayload = `${timestamp}.${body}`;
  const expected = crypto.createHmac('sha256', webhookKey).update(signedPayload).digest('hex');

  // Constant-time compare to avoid leaking the signature via timing.
  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(signature, 'utf8');
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return false;

  if (opts.toleranceSeconds != null) {
    const ageSeconds = Math.abs(Date.now() / 1000 - Number(timestamp));
    if (!Number.isFinite(ageSeconds) || ageSeconds > opts.toleranceSeconds) return false;
  }
  return true;
}

module.exports = { verifyMoonPayWebhook, parseSignatureHeader };

if (require.main === module) {
  const args = process.argv.slice(2);
  const get = (flag) => {
    const i = args.indexOf(flag);
    return i !== -1 ? args[i + 1] : undefined;
  };
  const sig = get('--sig');
  const body = get('--body') ?? '';
  const key = get('--key') || process.env.MOONPAY_WEBHOOK_KEY;
  if (!sig || !key) {
    console.error('usage: node verify-webhook.js --sig "t=…,s=…" --body \'<raw-body>\' [--key wk_…]');
    console.error('       webhook key falls back to $MOONPAY_WEBHOOK_KEY');
    process.exit(2);
  }
  try {
    const ok = verifyMoonPayWebhook(sig, body, key, { toleranceSeconds: 300 });
    console.log(ok ? 'VALID' : 'INVALID');
    process.exit(ok ? 0 : 1);
  } catch (err) {
    console.error('error:', err.message);
    process.exit(2);
  }
}
