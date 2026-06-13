# Widget Off-Ramp (Sell)

The off-ramp is MoonPay's hosted **sell** widget: the customer converts crypto
to fiat and gets paid out (card, ACH, SEPA, GBP/EUR bank transfer, etc.). The
defining difference from on-ramp: **your app sends the crypto on-chain** to a
MoonPay-provided deposit address as part of the flow. Source:
`dev.moonpay.com/widget/off-ramp/*`.

## Hosts & environment

| Environment | Base URL | Key |
|---|---|---|
| Sandbox | `https://sell-sandbox.moonpay.com/` | `pk_test_…` |
| Production | `https://sell.moonpay.com/` | `pk_live_…` |

Integration methods mirror on-ramp: URL/iframe, Web SDK (`flow: "sell"`), React
Native SDK, plus the Node SDK for signing. (Some doc code samples reuse the
on-ramp host `buy-sandbox.moonpay.com` in signing examples — for sell, use the
`sell` host.)

## The sell flow (and the step integrators miss)

1. Customer confirms crypto + fiat + amount, logs in (MFA), picks a payout
   method, completes KYC if new, and confirms the sale.
2. **Your app sends the crypto** to the MoonPay deposit address for that
   transaction. With the SDK this is the `onInitiateDeposit` handler; you sign
   and broadcast the transfer from the customer's wallet, then return the
   deposit identifier.
3. MoonPay receives the deposit, converts it, and pays out fiat.

```ts
const widget = moonPay({
  flow: "sell",
  environment: "sandbox",
  variant: "overlay",
  params: { apiKey: "pk_test_123", baseCurrencyCode: "eth", baseCurrencyAmount: "0.15" },
  handlers: {
    async onInitiateDeposit(props) {
      // props: cryptoCurrency, cryptoCurrencyAmount, depositWalletAddress,
      //        fiatCurrency, fiatCurrencyAmount, transactionId
      const depositId = await sendCryptoFromWallet(
        props.depositWalletAddress,
        props.cryptoCurrencyAmount,
      );
      return { depositId };          // REQUIRED return — this handler must resolve {depositId}
    },
  },
});
widget.show();
```

**48-hour rule:** the on-chain deposit must reach MoonPay within **48 hours** of
the sell transaction being created, or it fails with "Deposit timeout".

If MoonPay supplies a `depositWalletAddressTag` (for memo/tag chains like XRP),
you **must** include that tag with the on-chain transfer or the deposit will not
be credited and the transaction fails.

## Off-ramp URL parameters

`apiKey` required; all others optional (source:
`widget/off-ramp/customization/parameters.md`):

| Parameter | Description | Example |
|---|---|---|
| `apiKey` *(req)* | Publishable key | `pk_test_123` |
| `baseCurrencyCode` | Crypto the customer sells (locks selection) | `eth`, `btc` |
| `defaultBaseCurrencyCode` | Preferred crypto to sell (changeable) | `eth` |
| `quoteCurrencyCode` | Fiat the customer is paid in | `usd`, `eur`, `gbp` |
| `baseCurrencyAmount` | Amount of crypto to sell | `0.15` |
| `quoteCurrencyAmount` | Fiat-equivalent target amount | `500` |
| `lockAmount` | `true` locks `baseCurrencyAmount` | `true` |
| `refundWalletAddress` | Where to refund crypto if a refund is needed | `0x…` |
| `refundWalletAddresses` | JSON map crypto→refund address (takes precedence) | `{"eth":"0x…"}` |
| `paymentMethod` | Pre-select payout method | `credit_debit_card`, `ach_bank_transfer`, `gbp_bank_transfer` |
| `email` | Pre-fill email (⇒ needs signing) | `user@example.com` |
| `externalTransactionId` | Your transaction id (echoed back) | `order_…` |
| `externalCustomerId` | Your user id (echoed back) | `user_…` |
| `redirectURL` | Return URL after the flow (https / Universal Link only) | `https://…` |
| `theme` / `colorCode` / `themeId` / `language` | Same theming controls as on-ramp | `dark` / `%237d01ff` |
| `showAllCurrencies` | `true` shows all enabled currencies | `true` |
| `showWalletAddressForm` | Force the wallet-address form | `true` |
| `unsupportedRegionRedirectUrl` / `skipUnsupportedRegionScreen` | Unsupported-region handling | `https://…` / `true` |
| `signature` | HMAC of the query string (appended last) | `&signature=…` |

> **Naming subtlety:** the off-ramp parameter table calls the sensitive wallet
> fields `refundWalletAddress` / `refundWalletAddresses`, while the shared
> url-signing page refers to `walletAddress` / `walletAddresses`. Either way,
> sign the URL whenever a wallet address or email is present.
>
> `redirectURL` only accepts HTTPS or Universal/App Link URLs — custom-scheme
> deep links (`myapp://…`) are not supported.
>
> When `refundWalletAddresses` is set, only the cryptos with a supplied address
> are shown unless `showAllCurrencies=true` is also set.

## URL signing

Identical algorithm to on-ramp — `base64(HMAC-SHA256(secretKey, new URL(url).search))`,
secret key, append `&signature=` (URL-encoded) or `updateSignature(rawSig)` for
the SDK. Use `scripts/sign-url.js`. See `widget-onramp.md` for the full rules
and gotchas; they apply unchanged here.

## Requote webhooks

Off-ramp prices can move between quote and execution. The
`sell_transaction_requote_required` webhook lets you surface an in-app requote
prompt so the customer can accept the new price:

```json
{
  "type": "sell_transaction_requote_required",
  "data": {
    "id": "transaction_id",
    "status": "requoteRequired",
    "baseCurrencyAmount": 1000.0,
    "quoteCurrencyAmount": 950.0,
    "baseCurrency": "usdc",
    "quoteCurrency": "usd",
    "externalCustomerId": "customer_123",
    "walletAddress": "0x…",
    "externalTransactionId": "your_transaction_id"
  }
}
```

Sell lifecycle webhooks (`sell_transaction_created` → `sell_transaction_updated`
→ `sell_transaction_failed`) and verification details are in
`references/webhooks.md`. The created event arrives with status
`waitingForDeposit` — that is your cue that the customer (your app) must send
the crypto.
