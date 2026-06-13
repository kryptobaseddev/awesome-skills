---
name: moonpay-payments
description: "Build, scaffold, and integrate MoonPay crypto on-ramp (buy) and off-ramp (sell) payments into a website or app — the embeddable Widget (@moonpay/moonpay-js / -react / -node) and the headless Platform + Frames product (@moonpay/platform-sdk-web). Ships a generator (scripts/scaffold-moonpay.mjs) that emits a complete, runnable integration — server-side URL signing, the frontend widget, a verified webhook handler, env, and README — so you stand up a working on-ramp/off-ramp in one command, then customize. Use whenever the user wants to add, build, generate, or scaffold fiat↔crypto buy/sell, a crypto checkout or 'shopping-style' payment processor, embed a buy/sell widget, integrate MoonPay, do crypto onboarding/KYC, sign a MoonPay widget URL, verify MoonPay webhooks, or build headless/co-branded Apple Pay / Google Pay / card crypto payments — even if they only say 'MoonPay', 'on-ramp', 'off-ramp', or 'buy crypto in my app'. Also bundles tested signing + webhook scripts and source-cited references."
license: MIT
compatibility: >-
  Bundled scripts need Node 18+ (sign-url.js / verify-webhook.js) and/or Python
  3.8+ stdlib (sign_url.py / verify_webhook.py), plus bash + curl for preflight.
  Integrations target any web/mobile stack (vanilla JS, React, React Native,
  iOS, Android, server-side Node/PHP/Python/Ruby). A MoonPay partner account and
  API keys are required — get them at https://dashboard.moonpay.com/developers.
inputs:
  - name: MOONPAY_PUBLISHABLE_KEY
    description: "Publishable key (pk_test_… sandbox / pk_live_… production). Safe in the browser; identifies your account on the widget URL and client API calls."
    required: false
  - name: MOONPAY_SECRET_KEY
    description: "Secret key (sk_test_… / sk_live_…). SERVER-ONLY — signs widget URLs and authenticates server APIs. Never ship it to the client or commit it."
    required: false
  - name: MOONPAY_WEBHOOK_KEY
    description: "Webhook signing key from dashboard → Developers. Used ONLY to verify Moonpay-Signature-V2 on inbound webhooks. Distinct from the secret key."
    required: false
metadata:
  author: github.com/kryptobaseddev
  version: "1.1.0"
  last_updated: "2026-06-12 23:30:00"
  category: payments
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
---

# MoonPay Payments — On-Ramp & Off-Ramp Integration

Add fiat↔crypto payments to a site or app: let customers **buy** crypto with a
card / Apple Pay / Google Pay / bank transfer (on-ramp) and **sell** crypto back
to fiat (off-ramp). MoonPay handles KYC, compliance, fraud, payments, and
payouts; you embed the UI and react to transaction events.

MoonPay ships **two distinct products** — pick one deliberately, because their
SDKs, hosts, auth headers, and mental models differ:

| | **Widget** (`/widget/*` docs) | **Platform + Frames** (`/platform/*` docs) |
|---|---|---|
| What | Hosted, drop-in buy/sell/swap UI you embed or open | Headless / co-branded payments you build into your own UX |
| You control | Pre-fill + theming; MoonPay owns the screens | The whole purchase UX; MoonPay owns compliance/risk only |
| Frontend SDK | `@moonpay/moonpay-js`, `@moonpay/moonpay-react`, `@moonpay/react-native-moonpay-sdk` | `@moonpay/platform-sdk-web` (+ Frames) |
| Server SDK | `@moonpay/moonpay-node` (URL signing) | raw REST (`X-Api-Key`) |
| Client auth | publishable key on the URL + **signed** URL | server-minted **session token** → in-memory access/client tokens |
| Hosts | `buy.moonpay.com` / `sell.moonpay.com` | frames at `blocks.moonpay.com`, API at `api.moonpay.com/platform/v1` |
| Best for | Fastest "buy crypto" button, a checkout-style flow, minimal code | Bespoke, fully-branded, headless Apple/Google/card pay, deep onboarding |

**Default recommendation:** for "a seamless shopping-style payment processor"
where you want speed and don't need to own every pixel, start with the **Widget
on-ramp** (`@moonpay/moonpay-js`). Reach for **Platform + Frames** when you must
render your own buy screen, do headless Apple/Google Pay, or co-brand the
onboarding. The two are not mixed within a single flow.

→ Decision still unclear? Read `references/widget-onramp.md` (Widget) and
`references/platform-frames.md` (Platform) intros, then choose.

## Facts that prevent broken work

| Fact | Consequence |
|---|---|
| **Three key types**: `pk_…` publishable (browser-safe), `sk_…` secret (server-only), and a separate **webhook key** | Signing with `pk_`, verifying webhooks with `sk_`, or leaking `sk_` to the client are the most common failures |
| Environment is the **key prefix**, not a different URL: `*_test_*`→sandbox, `*_live_*`→production | A live key on a "sandbox-looking" `buy.moonpay.com` URL charges real money; test data silently fails on a live key |
| **Widget URL signing** = `base64(HMAC-SHA256(secretKey, new URL(url).search))`, appended as `&signature=` | Required whenever `walletAddress`/`walletAddresses`/`email` are present; sign **server-side** — use `scripts/sign-url.js` |
| Widget server API auth: `Authorization: Api-Key sk_…` **header** (or `apiKey=pk_…` query for public reads) | It is **not** `Bearer` and **not** `X-Api-Key`. Copying a Platform call here returns 401 |
| Platform API auth: `X-Api-Key: sk_…` (server) then `Authorization: Bearer <accessToken>` (client) | Different product, different headers — see the table above |
| Webhooks: verify the **`Moonpay-Signature-V2`** header (`t=…,s=…`) as `HMAC-SHA256(webhookKey, "t.rawBody")` | Verify against the **raw** body, with the **webhook key** — use `scripts/verify-webhook.js`. Events can duplicate / arrive out of order → de-dupe |
| Off-ramp (sell): **your app sends the crypto** to MoonPay's deposit address, then returns `{ depositId }` | Deposit must land within **48h** or the sell fails with "Deposit timeout". This is the step integrators miss |
| Apple Pay / Google Pay are **not** supported in the Widget `overlay` variant | Use `embedded`/`newTab`, or the Platform `setupApplePay`/`setupGooglePay` frames |
| Embedding needs both **domain allowlisting** (dashboard → Developers) **and** a page CSP allowing `https://*.moonpay.com/` (`frame-src`, `connect-src`) | Missing either → frames silently refuse to load with a `frame-ancestors` CSP error |
| The quote `signature` (Platform) is an **opaque** string | Never `JSON.parse` it — pass it verbatim to `setupBuy`/`setupWidget` |

## Preflight

Run once to confirm tooling + keys before writing code:

```bash
bash scripts/moonpay-preflight.sh            # local checks
bash scripts/moonpay-preflight.sh --probe    # also pings the widget API
```

It checks node/python/curl, finds `MOONPAY_*` keys, validates prefixes, and
flags the classic mistakes (mixed test/live keys, a secret key in a
frontend-exposed var). It validates key **format**, not validity — a 401 on the
first real call is what proves a key is live and enabled.

## Build an integration in one command (scaffold)

The fastest way to stand up a working on-ramp/off-ramp is to **generate** it,
then customize. `scripts/scaffold-moonpay.mjs` writes a complete, runnable
project — server-side signing, the frontend widget, a verified webhook handler,
an `.env` template, and a README — with the HMAC signing + webhook verification
**inlined** (the generated project has no dependency on this skill).

```bash
# Widget buy+sell into ./moonpay-integration (vanilla JS frontend)
node scripts/scaffold-moonpay.mjs --out ./moonpay-integration --flow both

# React frontend, buy only
node scripts/scaffold-moonpay.mjs --flow buy --frontend react --out ./pay

# Headless Platform + Frames (custom UI, Apple/Google Pay, onboarding)
node scripts/scaffold-moonpay.mjs --product platform --frontend react --out ./pay

node scripts/scaffold-moonpay.mjs --help     # all flags; --dry-run previews
```

Flags: `--product widget|platform`, `--flow buy|sell|both` (widget),
`--frontend vanilla|react`, `--out DIR`, `--force`, `--dry-run`. It refuses to
overwrite without `--force`. After generating: `cd <dir>`, `npm install` the
printed deps, `cp .env.example .env`, fill in sandbox keys, `node server/server.js`.

Then **customize** the emitted code using the references below — the scaffold is
a correct starting skeleton, not a black box. Tailor the params, theming, order
fulfillment, and (for sell) the on-chain deposit step to your app.

## Quick start — Widget on-ramp (understand the moving parts)

If you'd rather wire it by hand (or need to graft MoonPay into an existing app),
here's the shortest path to "buy crypto" on a website: a server endpoint that
signs the URL with your secret key, the SDK on the frontend, and a webhook that
marks the order paid. Sandbox keys (`pk_test_`/`sk_test_`) run the whole thing
for free. (This is exactly what the scaffolder emits.)

**1 — Frontend: render the buy widget** (`npm install @moonpay/moonpay-js`)

```ts
import { loadMoonPay } from "@moonpay/moonpay-js";

const moonPay = await loadMoonPay();
const widget = moonPay({
  flow: "buy",
  environment: "sandbox",          // "production" with a pk_live_ key
  variant: "overlay",              // embedded | overlay | newTab | newWindow
  params: {
    apiKey: "pk_test_…",
    baseCurrencyCode: "usd",       // fiat the customer pays
    baseCurrencyAmount: "100",
    defaultCurrencyCode: "eth",    // crypto they receive
    walletAddress: "0x…",          // ⇒ this makes the URL require a signature
    externalTransactionId: "order_12345",  // tie it to your order
  },
  handlers: {
    async onTransactionCompleted(props) {
      // UI hint only — treat the WEBHOOK as the source of truth for fulfillment
      console.log("completed", props.id, props.status);
    },
  },
});

// Because walletAddress is set, sign before showing:
const urlForSignature = widget.generateUrlForSigning();
const { signature } = await fetch("/api/moonpay/sign", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ urlForSignature }),
}).then((r) => r.json());
widget.updateSignature(signature);   // raw signature, NOT url-encoded, for the SDK

widget.show();
```

**2 — Server: sign the URL** (secret key stays here, never reaches the browser)

```ts
// POST /api/moonpay/sign   — Express handler
import { signMoonPayUrl } from "../skills/moonpay-payments/scripts/sign-url.js";

app.post("/api/moonpay/sign", express.json(), (req, res) => {
  const signature = signMoonPayUrl(req.body.urlForSignature, process.env.MOONPAY_SECRET_KEY);
  res.json({ signature });               // return the raw signature to updateSignature()
});
```

Or from the shell: `node scripts/sign-url.js "<full-widget-url>" --raw`.
For a plain iframe/URL integration (no SDK), append it yourself:
`node scripts/sign-url.js "<url>"` prints the URL with `&signature=` URL-encoded.

**3 — Server: confirm payment via webhook** (the real source of truth)

```ts
// POST /webhooks/moonpay — capture the RAW body for signature verification
import { verifyMoonPayWebhook } from "../skills/moonpay-payments/scripts/verify-webhook.js";

app.post("/webhooks/moonpay", express.raw({ type: "*/*" }), (req, res) => {
  const ok = verifyMoonPayWebhook(
    req.headers["moonpay-signature-v2"],
    req.body,                              // raw Buffer — do NOT use parsed JSON
    process.env.MOONPAY_WEBHOOK_KEY,
    { toleranceSeconds: 300 },
  );
  if (!ok) return res.status(400).end();

  const event = JSON.parse(req.body.toString());
  if (event.type === "transaction_updated" && event.data.status === "completed") {
    // fulfill event.data.externalTransactionId — idempotently (events can repeat)
  }
  res.status(200).json({ status: "success" });
});
```

That is a complete on-ramp. Configure the webhook URL and allowlist your domain
at https://dashboard.moonpay.com/developers, then test with the sandbox cards in
`references/going-live.md`.

## Where to go next

Read the reference that matches the task — each is self-contained and source-cited:

| Task | Reference |
|---|---|
| Buy widget: params, SDK init, events, theming, DeFi | `references/widget-onramp.md` |
| Sell widget: the send-crypto deposit flow, refunds, requotes, 48h rule | `references/widget-offramp.md` |
| All four widget SDKs (web/react/react-native/node) + signing wiring | `references/widget-sdk.md` |
| Server-to-server widget API: quotes, currencies, limits, transactions, customers | `references/widget-api.md` |
| Webhook events, payload shapes, statuses, signature verification, de-dup | `references/webhooks.md` |
| Platform headless payments + Frames (sessions, connect, setupBuy/Widget/ApplePay, challenges, REST) | `references/platform-frames.md` |
| Sandbox/test mode, test cards & wallets, going-live gate, disclosures, CSP | `references/going-live.md` |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/scaffold-moonpay.mjs` | **Generate a complete, runnable integration** (server signing + frontend widget + webhook + env + README). Widget or Platform; buy/sell/both; vanilla/React. |
| `scripts/sign-url.js` / `sign_url.py` | HMAC-SHA256 sign a widget URL (importable + CLI). Verified Node↔Python parity. |
| `scripts/verify-webhook.js` / `verify_webhook.py` | Verify `Moonpay-Signature-V2`, with replay-window tolerance + timing-safe compare. |
| `scripts/moonpay-preflight.sh` | Check tooling, keys, prefixes, and the mixed-env / leaked-secret mistakes. |

When fetching live MoonPay docs, every page has a clean Markdown twin — append
`.md` to any `dev.moonpay.com` URL (e.g. `…/widget/on-ramp/quickstart.md`). The
full index is `https://dev.moonpay.com/llms.txt`.
