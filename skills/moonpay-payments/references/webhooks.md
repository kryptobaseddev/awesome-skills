# Webhooks

Webhooks are how you reliably learn a transaction's outcome. Treat them — not
the client-side `onTransactionCompleted` event — as the source of truth for
fulfillment. Configure endpoint URLs in the dashboard → Developers → Webhooks.
Source: `dev.moonpay.com/api-reference/widget/webhooks/*`.

## Signature verification (do this before trusting any payload)

Every webhook carries an HMAC signature so you can prove it came from MoonPay.

- Header: **`Moonpay-Signature-V2`** (a legacy `moonpay-signature` header is
  also sent — ignore it; it uses a different scheme). Format:
  `Moonpay-Signature-V2: t=1492774577,s=5257a869…`
- Algorithm: `HMAC-SHA256`, hex digest.
- Signed payload = `timestamp` + `"."` + body, where body is:
  - **POST** → the raw request body bytes (the JSON exactly as received)
  - **GET** → the search string, e.g. `?externalCustomerId=adbb317d-…`
- Secret = your account's **webhook API key** from
  `https://dashboard.moonpay.com/developers/` — **not** the `sk_` secret key.
- Compare the computed hex to `s` (use a timing-safe compare).

The docs describe this in prose with no code sample. Use the bundled
`scripts/verify-webhook.js` (or `verify_webhook.py`), which also enforces a
replay-protection time window:

```ts
import { verifyMoonPayWebhook } from "../scripts/verify-webhook.js";

app.post("/webhooks/moonpay", express.raw({ type: "*/*" }), (req, res) => {
  const ok = verifyMoonPayWebhook(
    req.headers["moonpay-signature-v2"],
    req.body,                                  // raw Buffer — see gotcha below
    process.env.MOONPAY_WEBHOOK_KEY,
    { toleranceSeconds: 300 },
  );
  if (!ok) return res.status(400).end();
  // … handle req.body (parse only after verifying) …
  res.status(200).json({ status: "success" });
});
```

**Critical gotcha — verify the RAW body.** If your framework parses JSON and you
re-serialize it, key order / spacing change and the HMAC won't match. Capture
raw bytes: `express.raw(...)` in Express, `await request.body()` in
FastAPI/Starlette, `request.get_data()` in Flask, `request.body.read` in
Sinatra. Verify first, then `JSON.parse`.

## Event types & payloads

Envelope shape: `{ "data": { … }, "type": "<event>", "externalCustomerId": "…" }`.
Note **buy** carries `externalCustomerId` at the envelope root; **sell** carries
it only inside `data`.

| Product | Events | Statuses (`data.status`) |
|---|---|---|
| **Buy** | `transaction_created`, `transaction_updated`, `transaction_failed` | `waitingPayment`, `waitingAuthorization`, `pending`, `completed`, `failed` |
| **Sell** | `sell_transaction_created`, `sell_transaction_updated`, `sell_transaction_failed`, `sell_transaction_requote_required` | `waitingForDeposit`, `pending`, `completed`, `failed`, `requoteRequired` |
| **Swap** | `swap_transaction_created`, `swap_deposit_wallet_created`, `swap_deposit_received`, `swap_asset_delivery_initiated`, `swap_transaction_completed`, `swap_transaction_failed`, `swap_quote_expired`, `swap_quote_invalid`, `swap_refund_asset_delivery_initiated`, `swap_refund_completed` | — |
| **Identity** | `identity_check_updated` | — |

### Buy `transaction_updated` (completed) — key fields

```json
{
  "data": {
    "id": "bda09e91-559f-4e7a-807a-cdec1a903d9d",
    "status": "completed",
    "baseCurrencyAmount": 295.45,
    "quoteCurrencyAmount": 0.1819,
    "feeAmount": 3.99, "networkFeeAmount": 0.56, "areFeesIncluded": true,
    "walletAddress": "0xc216eD2D…",
    "cryptoTransactionId": "0x6751c8fce2…",
    "paymentMethod": "credit_debit_card",
    "failureReason": null,
    "stages": [ { "stage": "stage_one_ordering", "status": "success" }, … ],
    "externalCustomerId": "27346528354888"
  },
  "type": "transaction_updated",
  "externalCustomerId": "27346528354888"
}
```

On failure, `status` is `failed` and `failureReason` is populated (e.g.
`"Failed testnet withdrawal"`); the `stages[]` array shows which stage failed.

### Sell `sell_transaction_created` (waitingForDeposit)

```json
{
  "data": {
    "id": "b8606f16-…", "status": "waitingForDeposit",
    "baseCurrencyAmount": 500, "quoteCurrencyAmount": 38.79,
    "payoutMethod": "ach_bank_transfer",
    "customerId": "66eed1c8-…", "country": "USA", "state": "NJ",
    "quoteExpiresAt": "2023-05-12T17:50:50.389Z", "failureReason": null
  },
  "type": "sell_transaction_created"
}
```

`waitingForDeposit` is your signal that the customer (your app) must send the
crypto on-chain — see `references/widget-offramp.md`. The requote payload is
documented there too.

## Delivery semantics

- **Events can be duplicated and can arrive out of order.** De-duplicate on
  `data.id` + `type`, and don't assume `created` precedes `updated`. Make
  fulfillment idempotent.
- Respond `200` quickly; do slow work async. A non-200 will be retried.
- Match transactions back to your orders via `externalTransactionId` /
  `externalCustomerId` (the values you passed into the widget).

## Platform product note

The Platform product currently tracks transaction status via polling
(`client.getTransaction(id)` / `GET /platform/v1/transactions/{id}`); platform
webhooks are marked "coming soon." See `references/platform-frames.md`.
