# Widget Server-to-Server API

The Widget API (separate from the Platform API) gives you quotes, currencies,
limits, payment-method availability, transaction lookups, and basic customer
info. Base host: `https://api.moonpay.com` (staging:
`https://api.moonpay-staging.com`). Source: `dev.moonpay.com/api-reference/widget/*`.

## Auth is NOT uniform — read this first

The Widget API spans several OpenAPI specs with **two different auth schemes**.
This is the #1 cause of 401s here:

| Endpoint group | Auth | Key |
|---|---|---|
| Quotes, currencies, limits, ramp transaction lookups | `apiKey=<key>` **query parameter** | **publishable** (`pk_…`, browser-safe) |
| Get customer, payment-method-config | `Authorization: Api-Key sk_live_…` **header** | **secret** (`sk_…`, server-only) |

It is **`Api-Key <secret>`**, not `Bearer <secret>`, and there is **no
`X-Api-Key`** header in the Widget API (that header belongs to the Platform API).
Verbatim OpenAPI security schemes:

```yaml
# quotes/currencies/limits/ramp-tx: publishable key in the query
apiKey: { type: apiKey, name: apiKey, in: query }

# get customer / payment methods: secret key in the Authorization header
apiKey: { type: apiKey, name: Authorization, in: header }   # value: "Api-Key sk_live_…"
```

## Endpoints

| Method & path | Purpose | Auth |
|---|---|---|
| `GET /v3/currencies` | List supported fiat + crypto currencies | `apiKey` query (pub) |
| `GET /v3/currencies/{code}/buy_quote` | Real-time **buy** quote | `apiKey` query (pub) |
| `GET /v3/currencies/{code}/sell_quote` | Real-time **sell** quote | `apiKey` query (pub) |
| `GET /v3/currencies/{code}/limits` | Min/max buy amounts (incl/excl fees) | `apiKey` query (pub) |
| `GET /payments/v1/payment-method-config` | Available payment methods for a region + tx type | `Authorization: Api-Key sk_…` |
| `GET /v1/customers/{customerId}` | Basic customer info (must have ≥1 session with your key) | `Authorization: Api-Key sk_…` |
| `GET /v1/virtual-accounts/transactions/onramp/{txId}` | On-ramp virtual-account transaction details | `apiKey` query (pub) |
| `GET /v1/virtual-accounts/transactions/offramp/{txId}` | Off-ramp virtual-account transaction details | `apiKey` query (pub) |

### Buy quote

```bash
curl 'https://api.moonpay.com/v3/currencies/eth/buy_quote?baseCurrencyCode=usd&baseCurrencyAmount=200&paymentMethod=credit_debit_card&extraFeePercentage=1&areFeesIncluded=false&walletAddress=0xd75233704795206de38Cc58B77a1f660B5C60896&apiKey=YOUR_PUBLISHABLE_KEY'
```

- Provide `baseCurrencyAmount` (fiat) **or** `quoteCurrencyAmount` (crypto). If
  both are sent, `quoteCurrencyAmount` wins. A `baseCurrencyAmount` below the
  currency minimum is silently treated as invalid.
- `paymentMethod` enum: `ach_bank_transfer`, `credit_debit_card`, `paypal`,
  `gbp_bank_transfer`, `gbp_open_banking_payment`, `pix_instant_payment`,
  `sepa_bank_transfer`.
- `extraFeePercentage` (0–10 integer) is your markup; `areFeesIncluded`
  controls whether amounts include it.

### Sell quote

```
GET https://api.moonpay.com/v3/currencies/eth/sell_quote?quoteCurrencyCode=usd&baseCurrencyAmount=3&payoutMethod=credit_debit_card&extraFeePercentage=1&apiKey=YOUR_PUBLISHABLE_KEY
```

> **Param name differs:** buy uses `paymentMethod`; **sell uses `payoutMethod`**
> (same enum). Copying the buy call verbatim for a sell quote silently ignores
> the method.

Response:

```json
{
  "quoteCurrencyCode": "eur", "baseCurrencyCode": "btc",
  "baseCurrencyAmount": 0.575, "quoteCurrencyAmount": 1521.11,
  "baseCurrencyPrice": 45677.96, "feeAmount": 15.36, "extraFeeAmount": 0,
  "payoutMethod": "credit_debit_card", "signature": "really-long-string",
  "expiresIn": 1800, "expiresAt": "2024-02-23T00:58:26.577Z"
}
```

### `payment-method-config`

```
GET /payments/v1/payment-method-config?transactionType=buy&countryCode=USA&stateOfResidence=NY
Authorization: Api-Key sk_live_…
```

`transactionType` = `buy` | `sell`, `countryCode` = ISO3. `stateOfResidence`
(ISO2) is **required when `countryCode=US`** — omit it and US requests 400 with
"region could not be resolved".

### `GET /v3/currencies` filtering

Without a `show` parameter this returns **dashboard-enabled** currencies
filtered by the request's originating IP geolocation — not "all" currencies.
Pass `show=all` to get everything, `show=enabled` for the enabled set.

## Transaction status lifecycle (virtual-accounts spec)

```
FundsReviewInProgress → ConversionInProgress → PayoutInProgress → Completed
                                                                 ↘ Failed
                          RejectedAml | RejectedFraud | RejectedMinAmount
```

These are the **Virtual Accounts** statuses. The SDK/webhook surfaces use the
flow-specific enums instead — buy: `waitingPayment`/`waitingAuthorization`/
`pending`/`completed`/`failed`; sell: `waitingForDeposit`/`pending`/
`completed`/`failed` (see `references/webhooks.md`).

## Notes

- `GET /v1/customers/{id}` only resolves once that customer has had at least one
  session under your API key.
- Quote `signature` + `expiresAt` come back on quote responses — quotes are
  short-lived; re-fetch when expired rather than reusing a stale quote.
- For the richer Platform API (sessions, quotes, transactions with `stages[]`),
  see `references/platform-frames.md` — it uses `X-Api-Key`, not `Api-Key`.
