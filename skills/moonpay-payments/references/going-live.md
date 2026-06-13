# Sandbox, Test Mode & Going Live

How to develop for free against the sandbox, what test data to use, and the
hard gate MoonPay applies before you can charge real money. Sources:
`dev.moonpay.com/platform/overview/test-mode.md`, `…/going-live.md`,
`…/requirements.md`, `dev.moonpay.com/widget/sandbox-testing.md`.

## Test mode = test keys

There is no separate sandbox host to point at — **the key prefix decides the
environment**. `pk_test_` / `sk_test_` run in sandbox/test mode;
`pk_live_` / `sk_live_` run in production. For the Platform product, the mode is
fixed by which key minted the session token. Keys live at
`https://dashboard.moonpay.com/developers/api-keys`.

Sandbox specifics:
- **KYC is simulated** (documents aren't verified). Use a **US or UK address** —
  they work best with the test cards. A "Skip document submission" button is
  offered.
- **OTP uses a real email + phone** — there are no bypass codes. Emails can't be
  reused across customers (use `you+test1@example.com`, `you+test2@…`); a phone
  number binds to one customer at a time.
- **SSN**: never use a real one — use a fake `123456789`.
- **Testnets only**: Bitcoin Testnet3, Ethereum/ERC-20 Sepolia, Solana, BNB,
  TON, Stellar, Litecoin testnets. Quotes for assets unavailable in test mode
  fail with `400 invalid_request` — test with `SOL` or `ETH`. ERC-20 transfers
  use MoonPay's test token at `0x9550949c46e27761b57f5391a25a7725444a938b`.
- **New York is NOT supported in sandbox** (it is in production) — a NY address
  yields a false "Your Region is Not Supported".
- Rate limits ("You've made too many actions") clear after ~20 minutes. A
  production MoonPay account used in sandbox shows "Account is restricted or
  blocked". An empty shared testnet wallet causes "Transaction processing
  failed" — top up via a faucet.

### Force challenges in test mode (Platform)

Set the buy amount to an exact value to trigger a verification path:

| Amount | Challenge | Applies to |
|---|---|---|
| `48` | Wallet ownership | Apple Pay + card |
| `49` | CVV re-entry | Card |

Must match exactly (`49.01` does nothing) and only works with a test key.

In test mode the Apple Pay frame is a **mock button** driven by
`window.confirm` (OK = success, Cancel = fail). If it's inside a sandboxed
iframe, add `allow-modals` to the `sandbox` attribute or the dialog never fires.

## Test cards

| Customer | Card | Exp | CVV |
|---|---|---|---|
| US Visa Credit | `4000 0200 0000 0000` | 12/2030 | 100 |
| US Mastercard Credit | `5436 0310 3060 6378` | 12/2030 | 100 |
| US Amex | `3456 7890 1234 564` | 12/2030 | 1000 |
| UK Visa | `4242 4242 4242 4242` | 12/2030 | 100 |
| EU Visa Debit (FR) | `4010 0617 0000 0021` | 12/2030 | 100 |

Decline cards (test failure handling): `4544 2491 6767 3670` (insufficient
funds), `4897 4535 6848 5113` (suspected fraud), `4818 9242 5013 1070`
(restricted card), `4095 2548 0264 2505` (timeout / internal error). Off-ramp
payout test card: `4000 0209 5159 5032`.

Return testnet coins after sell testing to MoonPay's published faucet addresses
(e.g. ETH `0xc216eD2D6c295579718dbd4a797845CdA70B3C36`); see the widget
sandbox-testing page for the full list per chain.

## Embedding requirements (both environments)

```
Content-Security-Policy: frame-src https://*.moonpay.com/; connect-src https://*.moonpay.com/;
```

- **Allowlist your domain per environment** at
  `https://dashboard.moonpay.com/developers`. Missing this → `frame-ancestors`
  CSP error and the frame silently refuses to load.
- **Apple Pay on web** requires Apple's manual domain verification.
- **iOS WKWebView**: set `allowsInlineMediaPlayback = true` for the Connect
  frame; mobile uses WKWebView (iOS) / WebView (Android).

## The going-live gate

MoonPay **verifies all acceptance criteria before enabling production** and may
update them with reasonable written notice. Account/credential and partner
(KYB-style) setup is handled directly with MoonPay ("during the preview, we will
work with you directly to set up your account and credentials"). The
programmatic, testable criteria for card payments:

1. **"Powered by MoonPay"** attribution on the Buy screen.
2. **Show all seven fee line items** before the customer completes the purchase,
   in order: *You pay · Network fee · Ecosystem fee · MoonPay fee · Amount used
   to buy [token] · At the exchange rate · Total crypto you'll get.*
3. **Waived fees still appear** with a value of `$0.00` — never omit a line item.
4. **The displayed total must exactly match the amount charged.** Any
   quoted-vs-charged discrepancy (even rounding) blocks approval.

### Disclosures (geo-tagged, data-driven)

Which legal disclosure to render is driven by the `paymentDisclosures` array on
the quote response — render exactly what it asks for, visible without
interaction (not behind a tooltip/menu), with a tappable Terms of Use link and
full untruncated text.

| `paymentDisclosures` id | Render |
|---|---|
| `eea-crypto-asset-risk` | EEA standard crypto-asset disclosure |
| `eea-unregulated-stablecoin-risk` | EEA non-MiCA stablecoin disclosure (e.g. USDT, DAI, PYUSD) |
| *(both present)* | render both |

US NY/WA require the exact Apple Pay disclosure above the frame. Apple Pay fees
need not be pre-displayed (the Apple Pay sheet shows them) — but the displayed
total must still match the charge. The exact disclosure wording is on
`dev.moonpay.com/platform/overview/going-live.md`; copy it verbatim.

## Pre-launch checklist

- [ ] Sandbox flow works end-to-end (buy and/or sell) with test cards.
- [ ] URL signing verified server-side (or quote/connect flow for Platform).
- [ ] Webhook endpoint verifies `Moonpay-Signature-V2`, de-dupes, is idempotent.
- [ ] Production domain allowlisted; CSP allows `https://*.moonpay.com/`.
- [ ] Apple Pay domain verified (if used); WKWebView inline playback set (mobile).
- [ ] Fee line items, $0.00 waived fees, exact total, and geo disclosures present.
- [ ] Swap `pk_test_`/`sk_test_` for `pk_live_`/`sk_live_` and re-test once approved.
