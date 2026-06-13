# Widget On-Ramp (Buy)

The on-ramp is MoonPay's hosted **buy** widget: the customer pays fiat (card,
Apple/Google Pay, bank transfer, PayPal/Venmo) and receives crypto at a wallet
address. You embed or open the widget; MoonPay runs the screens, KYC, payment,
and on-chain delivery. Source: `dev.moonpay.com/widget/on-ramp/*`.

## Hosts & environment

| Environment | Base URL | Key |
|---|---|---|
| Sandbox | `https://buy-sandbox.moonpay.com/` | `pk_test_…` |
| Production | `https://buy.moonpay.com/` | `pk_live_…` |

The publishable key prefix selects the environment — there is no other switch.
`apiKey` is the **only required** parameter; everything else is optional.

## Four ways to integrate

1. **URL / iframe** — build the URL, then `window.open(url, "_blank")`, set an
   `<iframe src>`, or load it in a mobile WebView.
2. **Web SDK** (`@moonpay/moonpay-js`) — recommended for websites; adds events
   and a clean signing handoff. See `widget-sdk.md`.
3. **React / React Native SDK** — `@moonpay/moonpay-react`,
   `@moonpay/react-native-moonpay-sdk`. See `widget-sdk.md`.
4. **Node SDK** (`@moonpay/moonpay-node`) — server-side URL signing + API calls.

### Minimal URL integration

```js
// Sign first if the URL carries walletAddress/email (see "URL signing" below)
const url = "https://buy-sandbox.moonpay.com/?apiKey=pk_test_123"
  + "&defaultCurrencyCode=eth&baseCurrencyCode=usd&baseCurrencyAmount=100";
window.open(url, "_blank");
```

Hex `colorCode` must be URL-encoded (`#7d01ff` → `%237d01ff`), or the `#` is
read as a URL fragment and dropped.

## On-ramp URL parameters

`apiKey` is required; all others optional. Full set (source:
`widget/on-ramp/customization/parameters.md`):

| Parameter | Description | Example |
|---|---|---|
| `apiKey` *(req)* | Publishable key; assigns customers/transactions to your account | `pk_test_123` |
| `currencyCode` | Crypto to buy (locks the selection) | `btc`, `eth`, `usdc_polygon` |
| `defaultCurrencyCode` | Preferred crypto (customer may change) | `eth` |
| `walletAddress` | Destination wallet for the crypto | `0x…` / `tb1q…` |
| `walletAddressTag` | Secondary address memo/tag | `myeostag` |
| `walletAddresses` | JSON map of multiple crypto→address | `{"btc":"…","eth":"0x…"}` |
| `walletAddressTags` | JSON map of address tags | `{"xrp":"0123456789"}` |
| `baseCurrencyCode` | Fiat the customer spends | `usd`, `eur`, `gbp` |
| `baseCurrencyAmount` | Fiat amount (positive number) | `100` |
| `quoteCurrencyAmount` | Crypto amount to buy instead of fiat amount | `0.5` |
| `lockAmount` | `true` locks `baseCurrencyAmount` | `true` |
| `paymentMethod` | Pre-select payment method | `credit_debit_card`, `apple_pay` |
| `email` | Pre-fill customer email (⇒ needs signing) | `user@example.com` |
| `externalTransactionId` | Your order/transaction id (echoed in webhooks) | `order_12345` |
| `externalCustomerId` | Your user id (echoed in webhooks) | `user_789` |
| `redirectURL` | Where to return after completion (https/Universal Link only) | `https://shop.example/done` |
| `theme` | `dark` or `light` | `dark` |
| `colorCode` | Main hex color (URL-encode the `#`) | `%237d01ff` |
| `themeId` | Dashboard-built theme id (tied to API key) | *(generated)* |
| `language` | ISO 639-1 code | `en`, `es`, `fr` |
| `showAllCurrencies` | `true` shows every enabled currency | `true` |
| `showOnlyCurrencies` | Comma-separated allow-list | `btc,eth,matic` |
| `showWalletAddressForm` | Force the wallet-address form | `true` |
| `unsupportedRegionRedirectUrl` | Redirect for unsupported regions | `https://…` |
| `skipUnsupportedRegionScreen` | `true` skips the unsupported-region screen | `true` |
| `contractAddress` | Token contract (DeFi Buy: buy a token by contract) | *(address)* |
| `networkCode` | Network for the token contract (DeFi Buy) | `solana`, `ethereum` |
| `signature` | HMAC signature of the query string (appended last, URL-encoded) | `&signature=…` |

## URL signing (required for sensitive params)

Signing proves your server built the URL, so an attacker can't rewrite the
destination wallet. **Required whenever `walletAddress`, `walletAddresses`, or
`email` are present.**

```
signature = base64( HMAC-SHA256( secretKey, new URL(url).search ) )
```

- Key = your **secret** key (`sk_test_…`/`sk_live_…`) — never the publishable key.
- Message = the query string **including the leading `?`** (`new URL(url).search`).
- URL-encode each parameter **value** when you build the URL (do this *before*
  signing), then URL-encode the resulting base64 signature when you append it.
- **URL integration:** append `&signature=${encodeURIComponent(signature)}` last.
- **SDK integration:** pass the **raw** (un-encoded) signature to
  `updateSignature()` — the SDK owns the URL.

Use the bundled `scripts/sign-url.js` (or `sign_url.py`) — it implements exactly
this and refuses a `pk_` key. Verbatim reference implementation from the docs:

```ts
import crypto from "crypto";
const signature = crypto
  .createHmac("sha256", "sk_test_key")     // your SECRET key, server-side only
  .update(new URL(originalUrl).search)     // the query string portion
  .digest("base64");
const urlWithSignature = `${originalUrl}&signature=${encodeURIComponent(signature)}`;
```

**Gotcha:** some cloud API gateways reorder query parameters in transit; the
signature is computed over the exact string, so reordering between signing and
delivery breaks validation. Sign as late as possible and pass the URL through
unchanged.

## Web SDK events

The SDK's `handlers` object receives nine lifecycle events (full payloads in
`widget-sdk.md`):

| Event | Fires when |
|---|---|
| `onReady` | SDK comm layer is up and the widget has loaded |
| `onLogin` | Customer logs in (or auth refreshed — `props.isRefresh`) |
| `onTransactionCreated` | Just before redirecting to the transaction tracker |
| `onTransactionCompleted` | A transaction is detected completed |
| `onClose` | Widget is closing |
| `onUnsupportedRegion` | Unsupported-region screen triggered |
| `onInitiateDeposit` | (Integrated **sell**) customer must deposit crypto → return `{ depositId }` |
| `onAuthToken` | (Swaps only) shares a swaps-scoped auth token |
| `onSwapsCustomerSetupComplete` | Swaps customer setup finished |

Transaction status enums in event payloads:
- **Buy** (`TransactionStatus`): `completed` | `failed` | `pending` |
  `waitingAuthorization` | `waitingPayment`
- **Sell** (`SellTransactionStatus`): `completed` | `failed` | `pending` |
  `waitingForDeposit`

`onTransactionCompleted` is a **UI hint**, not proof of fulfillment — confirm
via the webhook (`references/webhooks.md`). The browser can close before the
event fires.

## Theming

- `theme=dark|light` for the built-in light/dark modes.
- `colorCode` for the main accent color (hex, URL-encoded).
- Rich custom themes (logos, loader, full palette) are built in the dashboard
  theme builder at `https://dashboard.moonpay.com/theme`, tied to your API key;
  set one as default to apply it automatically, or pass its `themeId`.

## Common pitfalls

- Forgetting to sign once `walletAddress` is added → the widget rejects the URL.
- Using the `overlay` variant with Apple/Google Pay → not supported; use
  `embedded`/`newTab` or the Platform frames.
- Treating `onTransactionCompleted` as fulfillment → use webhooks, idempotently.
- Un-encoded `#` in `colorCode` → color silently dropped.
