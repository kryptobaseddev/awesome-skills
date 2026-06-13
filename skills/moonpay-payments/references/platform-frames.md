# Platform + Frames (headless / co-branded payments + onboarding)

The Platform product lets you build fiat→crypto payments **inside your own UX**:
you own the screens, MoonPay owns compliance, risk, fraud, and the regulated
payment/KYC steps. The UI pieces MoonPay supplies are **Frames** — iframes (web)
or WebViews (mobile) that talk to your app over a typed `postMessage` protocol.
Source: `dev.moonpay.com/platform/*`.

Use this product (over the Widget) when you must render your own buy screen, do
**headless** Apple Pay / Google Pay / card payments, or co-brand the customer
onboarding. Frontend SDK: `@moonpay/platform-sdk-web`.

```bash
npm i @moonpay/platform-sdk-web   # pnpm / bun also fine
```

## Credentials & the session flow

Three short-lived, **memory-only** credentials (never persist to disk/storage):

| Credential | Where it's made | Used for |
|---|---|---|
| **Session token** | Your server, `POST /platform/v1/sessions` with `X-Api-Key` | Bootstraps the SDK / connect flow |
| **Access token** | Returned from the check/connect frame | Client-side REST calls (`Authorization: Bearer …`) |
| **Client token** | Returned from the check/connect frame | Mounting subsequent frames (buy, apple-pay, …) |

The session token is **single-use** and expires in **24h** — mint a fresh one
on each app visit. Test vs live mode is decided by whether you minted the
session with `sk_test_` or `sk_live_`; there is no environment flag on the
client.

```ts
// SERVER — create a session (secret key never leaves the server)
const res = await fetch("https://api.moonpay.com/platform/v1/sessions", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-Api-Key": process.env.MOONPAY_SECRET_KEY },
  body: JSON.stringify({ externalCustomerId: "your_user_id", deviceIp: "203.0.113.1" }),
});
const { sessionToken } = await res.json();   // → send to the frontend
```

`deviceIp` is required; `externalCustomerId` / `email` / `phoneNumber` optional.
`DELETE /platform/v1/sessions` revokes a session (→ 204).

## The SDK client

```ts
import { createClient } from "@moonpay/platform-sdk-web";
const client = createClient({ sessionToken });   // synchronous; the ONLY non-Result method
```

`createClient` takes **only** `sessionToken` (plus optional `apiBaseUrl` /
`frameBaseUrl` that MoonPay support may direct you to set) — there is no `apiKey`
and no `environment` enum. Every other client method returns a
`Result<T,E>` = `{ ok, value?, error? }` (it does **not** throw):

```ts
const result = await someSdkCall();
if (!result.ok) { console.error(result.error); return; }
console.log(result.value);
```

### Connect a customer

```ts
const conn = await client.getConnection();
// → { status: "active", customer: {id}, credentials, capabilities }  (already connected)
// → { status: "connectionRequired", credentials }                    (must run connect)

if (conn.value.status === "connectionRequired") {
  const connectResult = await client.connect({
    container: document.querySelector("#connectContainer"),
    theme: { appearance: "dark" },           // optional
    onEvent: (event) => {                     // ConnectEvent
      switch (event.kind) {
        case "ready":    /* reveal the container */ break;
        case "complete": /* event.payload is the Connection; event.payload.frame.dispose() */ break;
        case "error":    console.error(event.payload); break;
      }
    },
  });
  if (!connectResult.ok) { /* connectResult.error.message */ }
  // connectResult.value.dispose() removes the frame
}
```

> The promise from `connect()` (and the other frame setups) resolves only after
> the customer **completes** the flow — use the `ready` event, not the awaited
> promise, to detect when the UI is mounted.

## Quotes (Platform)

```ts
const quote = await client.getQuote({
  source: { asset: { code: "USD" }, amount: "100.00" },   // fiat in
  destination: { asset: { code: "ETH" } },                // crypto out
  wallet: { address: "0x…" },
  paymentMethod: { type: "apple_pay" },                   // or { type: "card", id: "…" }
});
// quote.value.signature, .executable (true|false), .expiresAt, .fees, .paymentDisclosures
```

A quote is **executable** only when both `wallet.address` and `paymentMethod` are
present (`executable: false` = estimate only). The `signature` is an **opaque
string** — never `JSON.parse` it; pass it verbatim into a frame setup. Quotes
expire; frames emit a `quoteExpired` error → fetch a new quote and call
`setQuote(newSignature)`.

REST equivalent (client-side, with the access token):

```ts
await fetch("https://api.moonpay.com/platform/v1/quotes", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
  body: JSON.stringify({ source: {…}, destination: {…}, wallet: {…}, paymentMethod: {…} }),
});
```

## Executing payment — choose a frame

| Method | Frame | UX |
|---|---|---|
| `client.setupWidget({ quote, container, onEvent })` | full visible MoonPay buy iframe | MoonPay renders the whole purchase |
| `client.setupBuy({ quote, container, externalTransactionId, onEvent })` | **headless** (zero-dimension) buy pipeline | you render the purchase screen, drive via events |
| `client.setupApplePay({ quote, container, onEvent })` | 44px Apple Pay button + headless purchase | express checkout |
| `client.setupGooglePay({ quote, container, onEvent })` | 44px Google Pay button + headless purchase | express checkout |
| `client.setupAddCard({ container, onEvent })` | PCI-hosted card capture | returns a card whose `id` feeds a quote `paymentMethod` |

```ts
const buy = await client.setupBuy({
  quote: quote.value.signature,
  container: document.querySelector("#buyContainer"),
  externalTransactionId: "order_12345",
  onEvent: (event) => {                       // BuyEvent
    switch (event.kind) {
      case "ready":    /* show a spinner */ break;
      case "complete": console.log(event.payload.transaction); break;  // {id, status}
      case "challenge": client.setupChallenge(event.payload.url); break; // see below
      case "error":    console.error(event.payload.code, event.payload.message); break;
    }
  },
});
```

`FrameTransaction` is a discriminated union — on the failure variant
(`status === "failed"`) `id` may be **absent**; check `status` before reading
`transaction.id`. The headless `setupBuy` renders nothing — it's the
pipeline; you build the UI.

## Challenges (3-D Secure / SCA / identity)

When a buy/Apple Pay/Google Pay flow needs extra verification it emits a
`challenge` event with a fully-formed `url`. Render it via `setupChallenge(url)`:

- **Never construct or modify the challenge URL** — use the one in the event
  payload (or the upstream identity call) as-is.
- The challenge frame is **self-driving**: after the handshake you only send
  `ack`; there are no further parent→child messages.
- (Manual integration) generate a fresh `channelId` and append it to the
  provided challenge URL before setting it as the frame `src`.

## Frames protocol (only needed for manual / non-SDK integration)

Frames are served from `https://blocks.moonpay.com/platform/v1/<frame>` (`widget`,
`buy`, `connect`, `add-card`, `apple-pay`, `google-pay`, `challenge`). The SDK
handles all of this; do it yourself only if you wrap your own iframe/WebView.

Envelope (protocol **version 2**), stringified JSON over `postMessage`:

```json
{ "version": 2, "meta": { "channelId": "some_unique_value" }, "kind": "…", "payload": { } }
```

Handshake: app generates a `channelId` → injects it as a frame URL param → frame
sends `handshake` → app replies `ack` → bidirectional channel open. If no
handshake arrives within **5 seconds**, treat it as a load error.

**Security (manual mode):** validate every inbound message with
`event.origin === "https://blocks.moonpay.com"` **and** a matching `channelId`,
or you'll act on spoofed messages.

## Transactions (status tracking)

Platform webhooks are "coming soon"; today you poll:

```ts
const tx = await client.getTransaction(id);     // or GET /platform/v1/transactions/{id} (Bearer)
```

Transaction `status`: `pending` | `completed` | `failed`, plus an optional
`stages[]` array (`kind`: `ordering`, `waiting_payment`, `waiting_authentication`,
`verification`, `processing`, `delivery`, `crypto_hold`; `status`: `not_started`
| `in_progress` | `success` | `failed`). List with cursor pagination
(`pageInfo.nextCursor`). API rate limit: **30 req/sec**. Errors:
`{ code, type, message }`.

## Web embedding requirements

```
Content-Security-Policy: frame-src https://*.moonpay.com/; connect-src https://*.moonpay.com/;
```

Plus register your origin per environment at
`https://dashboard.moonpay.com/developers` — both layers are required or frames
fail with a `frame-ancestors` CSP error. Apple Pay on web needs Apple's manual
domain verification. On iOS WKWebView, set `allowsInlineMediaPlayback = true`
for the Connect frame. See `references/going-live.md`.
