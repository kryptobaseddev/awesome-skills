# Widget SDKs (Web · React · React Native · Node)

MoonPay ships four npm packages for the **Widget** product. They render the same
hosted buy/sell/swap widget; pick the one matching your stack. The secret key
lives only in the Node SDK (or your own backend) — never in a client package.

| Package | Stack | Role |
|---|---|---|
| `@moonpay/moonpay-js` | Vanilla web / TypeScript | `loadMoonPay()` → `moonPay({…})` factory |
| `@moonpay/moonpay-react` | React | `<MoonPayProvider>` + widget components |
| `@moonpay/react-native-moonpay-sdk` | React Native | `useMoonPaySdk` hook |
| `@moonpay/moonpay-node` | Server (Node) | URL signing + widget API calls |

Shared config across client SDKs:
- `flow`: `buy` | `sell` | `swap` | `swapsCustomerSetup`
- `environment`: `sandbox` | `production`
- `variant`: `embedded` | `overlay` | `newTab` | `newWindow`
- `params`: the widget query params (`apiKey` + on/off-ramp params) — see
  `widget-onramp.md` / `widget-offramp.md`
- `useWarnBeforeRefresh` (web): default `true`; set `false` to avoid breaking
  redirects back into mobile WebViews

> Apple Pay / Google Pay are **not** available in the `overlay` variant.
> Use `embedded`/`newTab`, or the Platform `setupApplePay`/`setupGooglePay`.

## `@moonpay/moonpay-js` (web)

```bash
npm install @moonpay/moonpay-js
# or: <script defer src="https://static.moonpay.com/web-sdk/v1/moonpay-web-sdk.min.js"></script>
```

```ts
import { loadMoonPay } from "@moonpay/moonpay-js";
const moonPay = await loadMoonPay();
// via script tag instead: const moonPay = window.MoonPayWebSdk.init;

const widget = moonPay({
  flow: "buy",
  environment: "sandbox",
  variant: "overlay",
  params: { apiKey: "pk_test_123", baseCurrencyCode: "usd", baseCurrencyAmount: "30", defaultCurrencyCode: "eth" },
  handlers: {
    async onTransactionCompleted(props) { console.log(props); },
  },
});
widget.show();
```

The widget object exposes `.show()`, `.generateUrlForSigning()`, and
`.updateSignature(sig)`.

### Signing handoff (web)

```ts
const moonPaySdk = moonPay({ /* …config with walletAddress… */ });
const urlForSignature = moonPaySdk.generateUrlForSigning();

// POST to YOUR backend, which signs with the secret key (scripts/sign-url.js):
const { signature } = await fetch("/sign-url", {
  method: "POST",
  body: JSON.stringify({ urlForSignature }),
}).then((r) => r.json());

moonPaySdk.updateSignature(signature);  // raw signature, not URL-encoded
moonPaySdk.show();
```

## `@moonpay/moonpay-react`

```bash
npm install @moonpay/moonpay-react
```

```tsx
import { MoonPayProvider, MoonPayBuyWidget } from "@moonpay/moonpay-react";

function App() {
  return (
    <MoonPayProvider apiKey="pk_test_…" debug>
      <MoonPayBuyWidget
        variant="overlay"
        baseCurrencyCode="usd"
        baseCurrencyAmount="100"
        defaultCurrencyCode="eth"
        visible={visible}
        onUrlSignatureRequested={async (url) => {
          // call your backend, return the raw signature string
          const { signature } = await fetch(`/sign-url?url=${encodeURIComponent(url)}`).then(r => r.json());
          return signature;
        }}
      />
    </MoonPayProvider>
  );
}
```

Components: `MoonPayBuyWidget`, `MoonPaySellWidget`, `MoonPaySwapWidget`,
`MoonPaySwapsCustomerSetupWidget`. There is **no `flow` prop** — the flow is the
component you choose. `visible` toggles display; `onUrlSignatureRequested` is the
signing callback (`(url: string) => Promise<string>` returning the raw signature).

**Next.js:** the provider and widgets touch `window`, so import them dynamically
with `ssr: false` or you get `ReferenceError: window is not defined`:

```ts
import dynamic from "next/dynamic";
const MoonPayProvider = dynamic(
  () => import("@moonpay/moonpay-react").then((m) => m.MoonPayProvider),
  { ssr: false },
);
const MoonPayBuyWidget = dynamic(
  () => import("@moonpay/moonpay-react").then((m) => m.MoonPayBuyWidget),
  { ssr: false },
);
```

## `@moonpay/react-native-moonpay-sdk`

```bash
npm install @moonpay/react-native-moonpay-sdk react-native-webview
# recommended: react-native-url-polyfill (for new URL().search)
```

`useMoonPaySdk(sdkConfig, browserOpener?)` returns either a `MoonPayWebView`
component or `openWithInAppBrowser` plus `generateUrlForSigning` /
`updateSignature`. React Native no longer bundles an in-app browser — supply
your own `browserOpener` with an `open(url)` method (e.g. wrapping
`expo-web-browser` or `react-native-inappbrowser`). Sign via your backend exactly
as on web.

## `@moonpay/moonpay-node` (server)

Server-only — instantiate with the **secret** key and sign/verify URLs or call
the widget API:

```ts
import { MoonPay } from "@moonpay/moonpay-node";
const moonPay = new MoonPay(process.env.MOONPAY_SECRET_KEY); // sk_test_… / sk_live_…

const signature = moonPay.url.generateSignature(unsignedUrl);          // raw signature
const signedUrl = moonPay.url.generateSignature(unsignedUrl, { returnFullURL: true });
const valid     = moonPay.url.isSignatureValid(signedUrl);
```

If you prefer zero MoonPay deps on the server, the bundled `scripts/sign-url.js`
/ `sign_url.py` do the identical HMAC and work in any runtime.

## Events & payloads (web/React)

Nine widget events fire via `handlers` (web) or component callbacks (React):
`onReady`, `onLogin`, `onTransactionCreated`, `onTransactionCompleted`,
`onClose`, `onUnsupportedRegion`, `onInitiateDeposit`, `onAuthToken`,
`onSwapsCustomerSetupComplete`.

Key payloads (source: `…/integration-methods/sdks/event-properties.md`):

- **`onTransactionCompleted`** (`OnTransactionCompletedProps`): `id`, `status`,
  `baseCurrency` `{code,id,name}`, `baseCurrencyAmount`, `quoteCurrency`
  `{chainId,code,coinType,contractAddress,id,name,networkCode}`,
  `quoteCurrencyAmount`, `walletAddress`, `walletAddressTag`, `feeAmount`,
  `extraFeeAmount`, `networkFeeAmount`, `areFeesIncluded`, `createdAt`.
- **`onTransactionCreated`** (`OnTransactionCreatedProps`): `id`, `status`,
  `baseCurrency`, `baseCurrencyAmount`.
- **`onLogin`** (`OnLoginProps`): `isRefresh` — if `true`, auth was refreshed,
  not a fresh login.
- **`onInitiateDeposit`** (`OnInitiateDepositProps`, integrated sell): provides
  `cryptoCurrency`, `cryptoCurrencyAmount`, `cryptoCurrencyAmountSmallestDenomination`,
  `depositWalletAddress`, `fiatCurrency`, `fiatCurrencyAmount`, `transactionId`,
  and expects you to **return `{ depositId }`**.
- **`onAuthToken`** (`OnAuthTokenProps`, swaps only): `token`, `csrfToken`; pass
  `token` as `Authorization: Bearer {token}` for swaps requests on the
  customer's behalf.

`onTransactionCompleted` is for UX only — fulfill orders from the webhook
(`references/webhooks.md`), idempotently.
