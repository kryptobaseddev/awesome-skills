#!/usr/bin/env node
/**
 * scaffold-moonpay.mjs — Generate a complete, runnable MoonPay integration into
 * a website/app. This is the "build" half of the skill: instead of hand-copying
 * snippets, it emits a self-contained, correct on-ramp/off-ramp integration —
 * server-side URL signing, the frontend widget, a verified webhook handler, an
 * env template, and a README — wired together and ready to run in the sandbox.
 *
 * The generated code INLINES the HMAC signing + webhook verification (verbatim
 * the algorithms MoonPay documents) so the output project has zero dependency
 * on this skill folder.
 *
 * Usage:
 *   node scaffold-moonpay.mjs [--out DIR] [--product widget|platform]
 *        [--flow buy|sell|both] [--frontend vanilla|react] [--force] [--dry-run]
 *
 * Examples:
 *   node scaffold-moonpay.mjs --out ./moonpay --flow both
 *   node scaffold-moonpay.mjs --product platform --frontend react --out ./pay
 *
 * Defaults: --out ./moonpay-integration --product widget --flow buy --frontend vanilla
 */
import fs from 'node:fs';
import path from 'node:path';

// ── arg parsing ─────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const flag = (name, def) => {
  const i = argv.indexOf(`--${name}`);
  return i !== -1 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : def;
};
const has = (name) => argv.includes(`--${name}`);
if (has('help') || has('h')) {
  console.log(fs.readFileSync(new URL(import.meta.url)).toString().split('\n').slice(1, 24).join('\n').replace(/^ \* ?/gm, ''));
  process.exit(2);
}

const opts = {
  out: flag('out', './moonpay-integration'),
  product: flag('product', 'widget'),     // widget | platform
  flow: flag('flow', 'buy'),              // buy | sell | both (widget only)
  frontend: flag('frontend', 'vanilla'),  // vanilla | react
  force: has('force'),
  dryRun: has('dry-run'),
};
for (const [k, allowed] of Object.entries({
  product: ['widget', 'platform'], flow: ['buy', 'sell', 'both'], frontend: ['vanilla', 'react'],
})) {
  if (!allowed.includes(opts[k])) {
    console.error(`error: --${k} must be one of ${allowed.join(', ')} (got "${opts[k]}")`);
    process.exit(2);
  }
}

// ── shared inlined helpers emitted into the generated project ────────────────
const SIGN_HELPERS = `import crypto from 'node:crypto';

// Sign a MoonPay widget URL: base64(HMAC-SHA256(secretKey, new URL(url).search)).
// Required whenever walletAddress/walletAddresses/email are present. Server-only.
export function signMoonPayUrl(url, secretKey) {
  if (!/^sk_(test|live)_/.test(secretKey || '')) {
    throw new Error('A MoonPay secret key (sk_test_… / sk_live_…) is required to sign.');
  }
  const search = new URL(url).search; // includes the leading "?"
  return crypto.createHmac('sha256', secretKey).update(search).digest('base64');
}

// Verify a webhook: HMAC-SHA256(webhookKey, \`\${t}.\${rawBody}\`) === s, from the
// Moonpay-Signature-V2: t=…,s=… header. Verify the RAW body, not parsed JSON.
export function verifyMoonPayWebhook(header, rawBody, webhookKey, { toleranceSeconds = 300 } = {}) {
  const parts = {};
  for (const seg of String(header || '').split(',')) {
    const i = seg.indexOf('=');
    if (i !== -1) parts[seg.slice(0, i).trim()] = seg.slice(i + 1).trim();
  }
  if (!parts.t || !parts.s || !webhookKey) return false;
  const body = Buffer.isBuffer(rawBody) ? rawBody.toString('utf8') : String(rawBody);
  const expected = crypto.createHmac('sha256', webhookKey).update(\`\${parts.t}.\${body}\`).digest('hex');
  const a = Buffer.from(expected), b = Buffer.from(parts.s);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return false;
  if (Math.abs(Date.now() / 1000 - Number(parts.t)) > toleranceSeconds) return false;
  return true;
}
`;

const ENV_EXAMPLE = `# MoonPay keys — get them at https://dashboard.moonpay.com/developers/api-keys
# Sandbox keys (pk_test_/sk_test_) run the whole flow for free. The prefix
# selects the environment; there is no separate sandbox host.
MOONPAY_PUBLISHABLE_KEY=pk_test_replace_me   # browser-safe; identifies your account
MOONPAY_SECRET_KEY=sk_test_replace_me        # SERVER-ONLY — signs widget URLs. Never ship to the client.
MOONPAY_WEBHOOK_KEY=replace_me               # dashboard → Developers → Webhooks signing key
PORT=3000
`;

// ── WIDGET product templates ─────────────────────────────────────────────────
function widgetServer() {
  return `import express from 'express';
import { signMoonPayUrl, verifyMoonPayWebhook } from './moonpay-crypto.js';

const router = express.Router();

// Frontend posts the unsigned URL from sdk.generateUrlForSigning(); we sign it
// with the secret key (server-only) and return the RAW signature.
router.post('/api/moonpay/sign', express.json(), (req, res) => {
  try {
    const signature = signMoonPayUrl(req.body.urlForSignature, process.env.MOONPAY_SECRET_KEY);
    res.json({ signature });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// MoonPay calls this when a transaction changes. Verify, de-dupe, then fulfill.
// express.raw is REQUIRED — the signature is over the raw body bytes.
const processed = new Set(); // replace with a real store in production
router.post('/webhooks/moonpay', express.raw({ type: '*/*' }), (req, res) => {
  const ok = verifyMoonPayWebhook(
    req.headers['moonpay-signature-v2'], req.body, process.env.MOONPAY_WEBHOOK_KEY,
  );
  if (!ok) return res.status(400).end();

  const event = JSON.parse(req.body.toString());
  const key = \`\${event.type}:\${event.data?.id}\`;
  if (!processed.has(key)) {
    processed.add(key);
    if (event.type === 'transaction_updated' && event.data.status === 'completed') {
      // ✅ fulfill the order tied to event.data.externalTransactionId (idempotently)
      console.log('Buy completed:', event.data.externalTransactionId, event.data.id);
    }
    if (event.type === 'sell_transaction_created' && event.data.status === 'waitingForDeposit') {
      // The customer (your wallet app) must now send the crypto on-chain within 48h.
      console.log('Sell awaiting deposit:', event.data.id);
    }
  }
  res.status(200).json({ status: 'success' });
});

export default router;
`;
}

function widgetServerEntry() {
  return `import 'dotenv/config';
import express from 'express';
import moonpayRouter from './moonpay-routes.js';

const app = express();
app.use(moonpayRouter);
app.use(express.static(new URL('../web', import.meta.url).pathname));

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(\`MoonPay demo on http://localhost:\${port}\`));
`;
}

function widgetVanilla() {
  const sell = opts.flow === 'sell' || opts.flow === 'both';
  const buy = opts.flow === 'buy' || opts.flow === 'both';
  return `import { loadMoonPay } from '@moonpay/moonpay-js';

const API_KEY = '${'${'}import.meta.env?.VITE_MOONPAY_PK || window.MOONPAY_PK || "pk_test_replace_me"}';
const ENVIRONMENT = 'sandbox'; // 'production' with a pk_live_ key

async function signViaBackend(sdk) {
  const urlForSignature = sdk.generateUrlForSigning();
  const { signature } = await fetch('/api/moonpay/sign', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urlForSignature }),
  }).then((r) => r.json());
  sdk.updateSignature(signature); // raw signature for the SDK
}
${buy ? `
export async function openBuy({ walletAddress, amount = '100', currency = 'eth' } = {}) {
  const moonPay = await loadMoonPay();
  const sdk = moonPay({
    flow: 'buy', environment: ENVIRONMENT, variant: 'overlay',
    params: {
      apiKey: API_KEY, baseCurrencyCode: 'usd', baseCurrencyAmount: amount,
      defaultCurrencyCode: currency, walletAddress,
      externalTransactionId: 'order_' + Date.now(),
    },
    handlers: {
      async onTransactionCompleted(p) { console.log('completed (UI hint)', p.id, p.status); },
    },
  });
  if (walletAddress) await signViaBackend(sdk); // signing required when walletAddress is set
  sdk.show();
}` : ''}${sell ? `
export async function openSell({ amount = '0.05', currency = 'eth', fiat = 'usd' } = {}) {
  const moonPay = await loadMoonPay();
  const sdk = moonPay({
    flow: 'sell', environment: ENVIRONMENT, variant: 'overlay',
    params: { apiKey: API_KEY, baseCurrencyCode: currency, baseCurrencyAmount: amount, quoteCurrencyCode: fiat },
    handlers: {
      // Your wallet app sends the crypto to props.depositWalletAddress, then returns { depositId }.
      async onInitiateDeposit(props) {
        console.log('send', props.cryptoCurrencyAmount, props.cryptoCurrency.id, 'to', props.depositWalletAddress);
        return { depositId: 'replace-with-your-onchain-deposit-id' };
      },
    },
  });
  sdk.show();
}` : ''}
`;
}

function widgetHtml() {
  const buy = opts.flow === 'buy' || opts.flow === 'both';
  const sell = opts.flow === 'sell' || opts.flow === 'both';
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>MoonPay demo</title>
    <!-- domain must be allowlisted at dashboard.moonpay.com/developers; CSP must allow https://*.moonpay.com/ -->
  </head>
  <body>
    <h1>MoonPay ${opts.flow === 'both' ? 'buy & sell' : opts.flow} demo</h1>
    ${buy ? `<button id="buy">Buy crypto</button>` : ''}
    ${sell ? `<button id="sell">Sell crypto</button>` : ''}
    <script type="module">
      import { openBuy, openSell } from './moonpay-buy.js';
      ${buy ? `document.getElementById('buy').onclick = () => openBuy({ walletAddress: '0xc216eD2D6c295579718dbd4a797845CdA70B3C36' });` : ''}
      ${sell ? `document.getElementById('sell').onclick = () => openSell();` : ''}
    </script>
  </body>
</html>
`;
}

function widgetReact() {
  return `import { MoonPayProvider, MoonPayBuyWidget${opts.flow !== 'buy' ? ', MoonPaySellWidget' : ''} } from '@moonpay/moonpay-react';
import { useState } from 'react';

// Next.js: import these via next/dynamic with { ssr: false } — they touch window.
const PK = process.env.NEXT_PUBLIC_MOONPAY_PK || 'pk_test_replace_me';

async function signViaBackend(url) {
  const { signature } = await fetch('/api/moonpay/sign', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urlForSignature: url }),
  }).then((r) => r.json());
  return signature; // raw signature string
}

export default function MoonPayCheckout({ walletAddress }) {
  const [visible, setVisible] = useState(false);
  return (
    <MoonPayProvider apiKey={PK}>
      <button onClick={() => setVisible(true)}>Buy crypto</button>
      <MoonPayBuyWidget
        variant="overlay"
        baseCurrencyCode="usd"
        baseCurrencyAmount="100"
        defaultCurrencyCode="eth"
        walletAddress={walletAddress}
        visible={visible}
        onUrlSignatureRequested={signViaBackend}
      />
    </MoonPayProvider>
  );
}
`;
}

// ── PLATFORM product templates ───────────────────────────────────────────────
function platformServer() {
  return `import 'dotenv/config';
import express from 'express';

const router = express.Router();

// Mint a single-use session token (server-side, secret key). The frontend SDK
// consumes it via createClient({ sessionToken }). Expires in 24h — fetch fresh
// on each visit.
router.post('/api/moonpay/session', express.json(), async (req, res) => {
  const r = await fetch('https://api.moonpay.com/platform/v1/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Api-Key': process.env.MOONPAY_SECRET_KEY },
    body: JSON.stringify({
      externalCustomerId: req.body.userId,
      deviceIp: req.headers['x-forwarded-for'] || req.socket.remoteAddress,
    }),
  });
  if (!r.ok) return res.status(r.status).json({ error: 'session creation failed' });
  res.json(await r.json()); // { sessionToken }
});

export default router;
`;
}

function platformClient() {
  return `import { createClient } from '@moonpay/platform-sdk-web';

// 1) get a session token from your server, 2) create the client, 3) connect the
// customer, 4) quote, 5) execute via a frame (setupBuy headless / setupWidget /
// setupApplePay). Every method returns { ok, value?, error? } except createClient.
export async function startMoonPay({ userId, container, wallet }) {
  const { sessionToken } = await fetch('/api/moonpay/session', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId }),
  }).then((r) => r.json());

  const client = createClient({ sessionToken });

  const conn = await client.getConnection();
  if (conn.ok && conn.value.status === 'connectionRequired') {
    await client.connect({ container, onEvent: (e) => { if (e.kind === 'error') console.error(e.payload); } });
  }

  const quote = await client.getQuote({
    source: { asset: { code: 'USD' }, amount: '100.00' },
    destination: { asset: { code: 'ETH' } },
    wallet: { address: wallet },
    paymentMethod: { type: 'apple_pay' },
  });
  if (!quote.ok) return console.error(quote.error);

  // Headless buy — you render the purchase UI; drive it via events.
  const buy = await client.setupBuy({
    quote: quote.value.signature, // opaque — pass verbatim, never JSON.parse
    container,
    externalTransactionId: 'order_' + Date.now(),
    onEvent: (e) => {
      if (e.kind === 'complete') console.log('tx', e.payload.transaction);
      if (e.kind === 'challenge') client.setupChallenge(e.payload.url); // 3-D Secure etc.
      if (e.kind === 'error') console.error(e.payload.code, e.payload.message);
    },
  });
  if (!buy.ok) console.error(buy.error);
}
`;
}

function readme() {
  const isWidget = opts.product === 'widget';
  const pkgs = isWidget
    ? (opts.frontend === 'react' ? '@moonpay/moonpay-react react react-dom' : '@moonpay/moonpay-js')
    : '@moonpay/platform-sdk-web';
  return `# MoonPay ${opts.product} integration (${opts.flow})

Generated by the \`moonpay-payments\` skill scaffolder. ${isWidget
    ? 'Embeddable Widget' : 'Headless Platform + Frames'} integration with server-side ${isWidget
    ? 'URL signing + webhook verification' : 'session minting'}.

## 1. Install

\`\`\`bash
cd ${path.basename(opts.out)}
npm init -y
npm install express dotenv ${pkgs}
cp .env.example .env   # then fill in your sandbox keys
\`\`\`

## 2. Configure your MoonPay dashboard (https://dashboard.moonpay.com/developers)

- Copy your **sandbox** keys (\`pk_test_…\`, \`sk_test_…\`) into \`.env\`.
${isWidget ? `- Add a **webhook** endpoint → \`https://YOUR_HOST/webhooks/moonpay\`, copy its signing key into \`MOONPAY_WEBHOOK_KEY\`.\n` : ''}- **Allowlist your domain** (e.g. \`http://localhost:3000\`) so MoonPay can embed.
- Set a page CSP allowing \`https://*.moonpay.com/\` for \`frame-src\` and \`connect-src\`.

## 3. Run

\`\`\`bash
node server/server.js          # http://localhost:3000
\`\`\`

## 4. Test (sandbox)

Use the test cards from the skill's \`references/going-live.md\` (e.g. UK Visa
\`4242 4242 4242 4242\`, exp \`12/2030\`, CVC \`123\`). KYC is simulated; OTP needs a
real email/phone; SSN can be \`123456789\`.

## Going live

Swap \`pk_test_\`/\`sk_test_\` for \`pk_live_\`/\`sk_live_\`, re-allowlist the production
domain, and meet the go-live gate (Powered-by-MoonPay attribution, the seven fee
line items, exact total match, geo disclosures) — see \`references/going-live.md\`.

## Files

${isWidget ? `- \`server/server.js\` — Express app (serves \`web/\` + mounts routes)
- \`server/moonpay-routes.js\` — POST /api/moonpay/sign, POST /webhooks/moonpay
- \`server/moonpay-crypto.js\` — inlined HMAC signing + webhook verification
- \`web/moonpay-buy.${opts.frontend === 'react' ? 'jsx' : 'js'}\` — frontend widget integration
${opts.frontend === 'vanilla' ? '- `web/index.html` — demo page\n' : ''}` : `- \`server/server.js\` — Express app: POST /api/moonpay/session
- \`web/moonpay-platform.js\` — createClient → connect → getQuote → setupBuy
`}- \`.env.example\` — the three MoonPay keys
`;
}

// ── assemble file list ───────────────────────────────────────────────────────
const files = [];
files.push(['.env.example', ENV_EXAMPLE]);
files.push(['README.md', readme()]);

if (opts.product === 'widget') {
  files.push(['server/moonpay-crypto.js', SIGN_HELPERS]);
  files.push(['server/moonpay-routes.js', widgetServer()]);
  files.push(['server/server.js', widgetServerEntry()]);
  if (opts.frontend === 'react') {
    files.push(['web/moonpay-buy.jsx', widgetReact()]);
  } else {
    files.push(['web/moonpay-buy.js', widgetVanilla()]);
    files.push(['web/index.html', widgetHtml()]);
  }
} else {
  files.push(['server/server.js', `import platformRouter from './moonpay-platform-routes.js';\nimport express from 'express';\nconst app = express();\napp.use(platformRouter);\napp.use(express.static(new URL('../web', import.meta.url).pathname));\napp.listen(process.env.PORT || 3000, () => console.log('MoonPay platform demo on http://localhost:3000'));\n`]);
  files.push(['server/moonpay-platform-routes.js', platformServer()]);
  files.push(['web/moonpay-platform.js', platformClient()]);
}

// ── write ────────────────────────────────────────────────────────────────────
const root = path.resolve(opts.out);
let wrote = 0, skipped = 0;
console.log(`MoonPay scaffolder → ${root}  (product=${opts.product} flow=${opts.flow} frontend=${opts.frontend})${opts.dryRun ? '  [dry-run]' : ''}`);
for (const [rel, content] of files) {
  const dest = path.join(root, rel);
  const exists = fs.existsSync(dest);
  if (exists && !opts.force) {
    console.log(`  skip   ${rel} (exists — use --force)`);
    skipped++;
    continue;
  }
  if (opts.dryRun) {
    console.log(`  would  ${rel} (${content.length} bytes)`);
    wrote++;
    continue;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, content);
  console.log(`  ${exists ? 'over' : 'write'}  ${rel}`);
  wrote++;
}
console.log(`Done: ${wrote} file(s)${skipped ? `, ${skipped} skipped` : ''}.`);
if (!opts.dryRun) console.log(`Next: cd ${opts.out} && npm init -y && npm install express dotenv ${opts.product === 'widget' ? (opts.frontend === 'react' ? '@moonpay/moonpay-react react react-dom' : '@moonpay/moonpay-js') : '@moonpay/platform-sdk-web'} && cp .env.example .env`);
