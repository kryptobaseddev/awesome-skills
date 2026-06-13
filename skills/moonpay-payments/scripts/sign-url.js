#!/usr/bin/env node
/**
 * sign-url.js — Sign a MoonPay widget URL (on-ramp / off-ramp / swap).
 *
 * MoonPay requires a `signature` whenever the widget URL carries sensitive
 * parameters (walletAddress, walletAddresses, email). The signature proves the
 * URL was assembled by YOUR server with YOUR secret key, so an attacker can't
 * swap the destination wallet. Signing MUST happen server-side — never ship a
 * secret key (`sk_live_…` / `sk_test_…`) to the browser.
 *
 * Algorithm (from dev.moonpay.com/widget/on-ramp/customization/url-signing):
 *   signature = base64( HMAC-SHA256( secretKey, new URL(url).search ) )
 * The signed string is the query string INCLUDING the leading "?", and it must
 * NOT already contain a `signature` param. The result is appended as the LAST
 * query parameter, URL-encoded.
 *
 * Usage:
 *   node sign-url.js "https://buy-sandbox.moonpay.com?apiKey=pk_test_x&walletAddress=0x..."
 *       --> prints the full signed URL (signature appended, URL-encoded)
 *
 *   node sign-url.js "<url>" --raw          # print only the raw base64 signature
 *                                            # (use this value with the SDK's updateSignature())
 *   node sign-url.js "<url>" --key sk_test_… # pass the key explicitly
 *
 * Secret key resolution: --key flag, else $MOONPAY_SECRET_KEY env var.
 *
 * As a module:
 *   const { signMoonPayUrl, appendSignature } = require('./sign-url.js');
 *   const signature = signMoonPayUrl(url, process.env.MOONPAY_SECRET_KEY);
 *   const signedUrl  = appendSignature(url, signature);
 */
'use strict';

const crypto = require('crypto');

/**
 * Compute the raw base64 HMAC-SHA256 signature for a MoonPay widget URL.
 * @param {string} url       Full widget URL (must already contain its params).
 * @param {string} secretKey MoonPay secret key (sk_test_… / sk_live_…).
 * @returns {string} base64 signature (NOT URL-encoded).
 */
function signMoonPayUrl(url, secretKey) {
  if (!secretKey) throw new Error('Missing MoonPay secret key (sk_test_… / sk_live_…).');
  if (!/^sk_(test|live)_/.test(secretKey)) {
    throw new Error(`Expected a secret key (sk_test_… / sk_live_…), got "${secretKey.slice(0, 8)}…". `
      + 'Publishable keys (pk_…) cannot sign — and secret keys must never reach the browser.');
  }
  const search = new URL(url).search; // includes the leading "?"
  if (!search) throw new Error('URL has no query string to sign.');
  if (/[?&]signature=/.test(search)) {
    throw new Error('URL already contains a signature param — sign the URL BEFORE appending the signature.');
  }
  return crypto.createHmac('sha256', secretKey).update(search).digest('base64');
}

/**
 * Append a signature to a widget URL as the final, URL-encoded query parameter.
 * Use this for plain URL/iframe integrations. For the @moonpay/moonpay-js SDK,
 * return the RAW signature (from signMoonPayUrl) to updateSignature() instead.
 */
function appendSignature(url, signature) {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}signature=${encodeURIComponent(signature)}`;
}

module.exports = { signMoonPayUrl, appendSignature };

if (require.main === module) {
  const args = process.argv.slice(2);
  const url = args.find((a) => !a.startsWith('--'));
  const raw = args.includes('--raw');
  const keyIdx = args.indexOf('--key');
  const secretKey = keyIdx !== -1 ? args[keyIdx + 1] : process.env.MOONPAY_SECRET_KEY;

  if (!url) {
    console.error('usage: node sign-url.js "<widget-url>" [--raw] [--key sk_test_…]');
    console.error('       secret key falls back to $MOONPAY_SECRET_KEY');
    process.exit(2);
  }
  try {
    const signature = signMoonPayUrl(url, secretKey);
    if (raw) {
      process.stdout.write(signature + '\n'); // feed this to the SDK's updateSignature()
    } else {
      process.stdout.write(appendSignature(url, signature) + '\n');
    }
  } catch (err) {
    console.error('error:', err.message);
    process.exit(1);
  }
}
