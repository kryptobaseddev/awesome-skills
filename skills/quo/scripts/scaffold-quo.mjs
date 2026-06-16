#!/usr/bin/env node
/**
 * scaffold-quo.mjs — Generate a complete, runnable Quo (formerly OpenPhone)
 * full-stack integration. Instead of hand-copying snippets, this emits a
 * self-contained app: an Express backend (Quo API client + send-SMS route +
 * a signature-verified beta webhook receiver) and a small frontend, wired
 * together and ready to run.
 *
 * The generated code INLINES the API client + webhook verifier (verbatim the
 * algorithms Quo documents) so the output project has ZERO dependency on this
 * skill folder.
 *
 * Usage:
 *   node scaffold-quo.mjs [--out DIR] [--frontend vanilla|react] [--force] [--dry-run]
 *
 * Examples:
 *   node scaffold-quo.mjs --out ./quo-app
 *   node scaffold-quo.mjs --frontend react --out ./quo-app
 *
 * Defaults: --out ./quo-integration --frontend vanilla
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
  console.log(fs.readFileSync(new URL(import.meta.url)).toString().split('\n').slice(1, 25).join('\n').replace(/^ \* ?/gm, ''));
  process.exit(2);
}

const opts = {
  out: flag('out', './quo-integration'),
  frontend: flag('frontend', 'vanilla'), // vanilla | react
  force: has('force'),
  dryRun: has('dry-run'),
};
if (!['vanilla', 'react'].includes(opts.frontend)) {
  console.error(`error: --frontend must be vanilla|react (got "${opts.frontend}")`);
  process.exit(2);
}

// ── inlined: Quo API client (server/quo.js) ──────────────────────────────────
const QUO_CLIENT = `// Tiny dependency-free Quo (OpenPhone) REST client. Auth = RAW key (no Bearer).
const E164 = /^\\+[1-9]\\d{1,14}$/;

export function createQuoClient({
  apiKey = process.env.QUO_API_KEY,
  baseUrl = process.env.QUO_BASE_URL || 'https://api.quo.com/v1',
  maxRetries = 4,
} = {}) {
  if (!apiKey) throw new Error('Set QUO_API_KEY (the raw key — no "Bearer ").');
  const root = baseUrl.replace(/\\/+$/, '');

  async function request(method, p, { query, body } = {}) {
    const url = new URL(root + (p.startsWith('/') ? p : '/' + p));
    for (const [k, v] of Object.entries(query || {})) {
      if (v == null) continue;
      for (const it of Array.isArray(v) ? v : [v]) url.searchParams.append(k, String(it));
    }
    for (let attempt = 0; ; attempt++) {
      const res = await fetch(url, {
        method,
        headers: { Authorization: apiKey, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      if ((res.status === 429 || res.status >= 500) && attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, Math.min(2 ** attempt * 250, 8000) + Math.random() * 200));
        continue;
      }
      const text = await res.text();
      const json = text ? (() => { try { return JSON.parse(text); } catch { return undefined; } })() : undefined;
      if (!res.ok) {
        const msg = json?.error?.message || json?.message || res.statusText;
        const err = new Error('Quo ' + method + ' ' + p + ' -> ' + res.status + ' ' + msg);
        err.status = res.status; err.body = json ?? text; throw err;
      }
      return { status: res.status, data: json };
    }
  }

  return {
    get: (p, query) => request('GET', p, { query }),
    post: (p, body) => request('POST', p, { body }),
    async sendMessage({ from, to, content, userId }) {
      const recipients = Array.isArray(to) ? to : [to];
      if (recipients.length !== 1 || !E164.test(recipients[0])) throw new Error('"to" must be exactly one E.164 number.');
      if (!content || !/\\S/.test(content) || content.length > 1600) throw new Error('"content" must be 1-1600 non-whitespace chars.');
      const { data } = await request('POST', '/messages', { body: { from, to: recipients, content, ...(userId ? { userId } : {}) } });
      return data?.data ?? data; // 202 Accepted — delivery is async
    },
    async *paginate(p, params = {}) {
      let pageToken; const maxResults = params.maxResults ?? 50;
      do {
        const { data } = await request('GET', p, { query: { ...params, maxResults, ...(pageToken ? { pageToken } : {}) } });
        for (const item of data?.data ?? []) yield item;
        pageToken = data?.nextPageToken ?? null;
      } while (pageToken);
    },
  };
}
`;

// ── inlined: webhook verifier (server/verify-webhook.js) ─────────────────────
const VERIFIER = `// Verify a Quo BETA webhook (Standard-Webhooks / Svix scheme).
// HMAC-SHA256 base64 over \`\${id}.\${timestamp}.\${rawBody}\`, secret = whsec_… (base64-decoded).
import crypto from 'node:crypto';
const TOLERANCE = 5 * 60;

function keyBytes(secret) {
  const s = String(secret || '');
  return Buffer.from(s.startsWith('whsec_') ? s.slice(6) : s, 'base64');
}
export function verifyQuoWebhook(headers, rawBody, secret, toleranceSeconds = TOLERANCE) {
  const h = (n) => headers[n] ?? headers[n.toLowerCase()];
  const id = h('webhook-id'), ts = h('webhook-timestamp'), sigHeader = h('webhook-signature');
  if (!id || !ts || !sigHeader || !secret) return false;
  const t = Number(ts), now = Math.floor(Date.now() / 1000);
  if (!Number.isFinite(t) || Math.abs(now - t) > toleranceSeconds) return false;
  const body = Buffer.isBuffer(rawBody) ? rawBody.toString('utf8') : String(rawBody);
  const expected = crypto.createHmac('sha256', keyBytes(secret)).update(id + '.' + ts + '.' + body).digest('base64');
  return String(sigHeader).split(' ').map((e) => e.split(',')).filter(([v]) => v === 'v1')
    .map(([, s]) => s).some((s) => {
      const a = Buffer.from(s), b = Buffer.from(expected);
      return a.length === b.length && crypto.timingSafeEqual(a, b);
    });
}
`;

// ── inlined: express server (server/server.js) ───────────────────────────────
const SERVER = `import 'dotenv/config';
import express from 'express';
import { createQuoClient } from './quo.js';
import { verifyQuoWebhook } from './verify-webhook.js';

const app = express();
const quo = createQuoClient(); // reads QUO_API_KEY

// 1) Webhook receiver — MUST see the RAW body, so mount express.raw on this
//    route BEFORE express.json. Verify the signature before trusting anything.
const processed = new Set(); // swap for Redis/DB in production (key on webhook-id, retain >= 28h)
app.post('/webhooks/quo', express.raw({ type: '*/*' }), (req, res) => {
  if (!verifyQuoWebhook(req.headers, req.body, process.env.QUO_WEBHOOK_KEY)) {
    return res.status(400).send('bad signature');
  }
  const deliveryId = req.headers['webhook-id'];
  if (processed.has(deliveryId)) return res.status(200).json({ deduped: true });
  processed.add(deliveryId);

  const event = JSON.parse(req.body.toString('utf8'));
  // Beta envelope: { id, type, data: { resource, context, links } }
  switch (event.type) {
    case 'message.received':
      console.log('📩 inbound:', event.data.resource.text, 'from', event.data.context.senderIdentifier);
      break;
    case 'message.delivered':
      console.log('✅ delivered:', event.data.resource.id);
      break;
    case 'call.completed':
      console.log('📞 call', event.data.resource.status, event.data.resource.duration + 's');
      break;
    default:
      console.log('event:', event.type);
  }
  res.status(200).json({ ok: true }); // ack fast; do slow work async
});

// 2) JSON API routes (after the raw webhook route).
app.use(express.json());

app.post('/api/quo/send', async (req, res) => {
  try {
    const msg = await quo.sendMessage(req.body); // { from, to, content, userId? }
    res.status(202).json(msg); // 202 Accepted — final status arrives via webhook
  } catch (e) {
    res.status(e.status || 400).json({ error: e.message });
  }
});

app.get('/api/quo/numbers', async (_req, res) => {
  try { res.json((await quo.get('/phone-numbers')).data); }
  catch (e) { res.status(e.status || 500).json({ error: e.message }); }
});

app.use(express.static(new URL('../web', import.meta.url).pathname));

const port = process.env.PORT || 3000;
app.listen(port, () => console.log('Quo demo on http://localhost:' + port));
`;

// ── frontend templates ───────────────────────────────────────────────────────
const WEB_HTML = `<!doctype html>
<html lang="en">
  <head><meta charset="utf-8" /><title>Quo demo</title>
    <style>body{font-family:system-ui;max-width:32rem;margin:3rem auto}input,textarea,button{display:block;width:100%;margin:.4rem 0;padding:.5rem}</style>
  </head>
  <body>
    <h1>Send an SMS via Quo</h1>
    <input id="from" placeholder="From (+15555550100 or PN… id)" />
    <input id="to" placeholder="To (+15555550111, E.164)" />
    <textarea id="content" placeholder="Message (1–1600 chars)"></textarea>
    <button id="send">Send</button>
    <pre id="out"></pre>
    <script type="module" src="./app.js"></script>
  </body>
</html>
`;

const WEB_JS = `const $ = (id) => document.getElementById(id);
$('send').onclick = async () => {
  $('out').textContent = 'sending…';
  const r = await fetch('/api/quo/send', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: $('from').value, to: $('to').value, content: $('content').value }),
  });
  const body = await r.json();
  // 202 = queued. Delivery (message.delivered) lands on your webhook, not here.
  $('out').textContent = (r.status === 202 ? '202 Accepted (queued)\\n' : 'Error ' + r.status + '\\n') + JSON.stringify(body, null, 2);
};
`;

const WEB_JSX = `import { useState } from 'react';

// Drop into any React app. The API key NEVER touches the browser — the
// /api/quo/send call goes to your server, which holds QUO_API_KEY.
export default function SendSms() {
  const [form, setForm] = useState({ from: '', to: '', content: '' });
  const [out, setOut] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function send() {
    setOut('sending…');
    const r = await fetch('/api/quo/send', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
    });
    const body = await r.json();
    setOut((r.status === 202 ? '202 Accepted (queued)\\n' : 'Error ' + r.status + '\\n') + JSON.stringify(body, null, 2));
  }

  return (
    <div style={{ maxWidth: '32rem', margin: '3rem auto', fontFamily: 'system-ui' }}>
      <h1>Send an SMS via Quo</h1>
      <input placeholder="From (+15555550100 or PN… id)" value={form.from} onChange={set('from')} />
      <input placeholder="To (+15555550111, E.164)" value={form.to} onChange={set('to')} />
      <textarea placeholder="Message (1–1600 chars)" value={form.content} onChange={set('content')} />
      <button onClick={send}>Send</button>
      <pre>{out}</pre>
    </div>
  );
}
`;

const ENV_EXAMPLE = `# Quo (formerly OpenPhone) credentials.
# Generate an API key: Quo workspace → Settings → API (owner/admin only).
# The value is the RAW key — do NOT add a "Bearer " prefix.
QUO_API_KEY=replace_me

# Beta webhook signing secret — the "whsec_…" value returned by
# POST https://api.quo.com/webhooks (data.key). Only used to verify inbound
# webhook signatures. Returned ONLY at create/rotate time — store it now.
QUO_WEBHOOK_KEY=whsec_replace_me

# Optional: override the host (api.openphone.com/v1 is an identical alias).
# QUO_BASE_URL=https://api.quo.com/v1
PORT=3000
`;

const PKG = JSON.stringify({
  name: path.basename(opts.out),
  private: true,
  type: 'module',
  scripts: { start: 'node server/server.js' },
  dependencies: { express: '^4.19.2', dotenv: '^16.4.5' },
}, null, 2) + '\n';

const README = `# Quo (OpenPhone) integration (${opts.frontend} frontend)

Generated by the \`quo\` skill scaffolder. An Express backend that sends SMS via
the Quo API and receives **signature-verified** beta webhooks, plus a ${opts.frontend}
frontend. The Quo client + webhook verifier are inlined — no dependency on the skill.

## 1. Install & configure

\`\`\`bash
cd ${path.basename(opts.out)}
npm install
cp .env.example .env      # then fill in QUO_API_KEY (raw key, no "Bearer")
\`\`\`

- **API key:** Quo workspace → Settings → API (owner/admin). Spaces aren't allowed in the name.
- **US SMS:** sending to US numbers requires completed **A2P 10DLC carrier registration**, or
  \`POST /v1/messages\` returns \`400\` code \`0206400\` "A2P Registration Not Approved".

## 2. Run

\`\`\`bash
npm start                 # http://localhost:3000
\`\`\`

Open the page, enter a \`from\` (one of your Quo numbers, E.164 or \`PN…\` id), a \`to\`
(E.164), and a message. A successful send returns **202 Accepted** — the message is
*queued*; final delivery arrives as a \`message.delivered\` webhook, not in the response.

## 3. Receive webhooks (beta)

Expose your server (e.g. \`ngrok http 3000\`) and create a beta webhook pointing at
\`https://YOUR_HOST/webhooks/quo\`:

\`\`\`bash
curl https://api.quo.com/webhooks -X POST \\
  -H "Authorization: $QUO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -H "x-quo-api-version: 2026-03-30" \\
  -d '{"url":"https://YOUR_HOST/webhooks/quo","events":["message.received","message.delivered","call.completed"]}'
\`\`\`

Save the returned \`data.key\` (\`whsec_…\`) into \`QUO_WEBHOOK_KEY\` — it's shown only
once. Then fire a test delivery: \`POST /webhooks/{id}/events/test\`. The receiver
verifies the \`webhook-signature\` over the **raw** body and de-dupes on \`webhook-id\`.

## Files

- \`server/server.js\` — Express: \`/api/quo/send\`, \`/api/quo/numbers\`, \`/webhooks/quo\`
- \`server/quo.js\` — inlined REST client (raw-key auth, 429 backoff, sendMessage, paginate)
- \`server/verify-webhook.js\` — inlined beta webhook signature verifier
- \`web/${opts.frontend === 'react' ? 'SendSms.jsx' : 'index.html + app.js'}\` — the frontend
- \`.env.example\` — QUO_API_KEY + QUO_WEBHOOK_KEY

## Gotchas baked in

- Auth header is the **raw** key, never \`Bearer\`. Rate limit 10 req/s/key (the client backs off on 429).
- \`to\` is exactly **one** E.164 recipient per send; \`content\` 1–1600 non-whitespace chars; MMS unsupported.
- The webhook route mounts \`express.raw\` **before** \`express.json\` so the signature verifies against raw bytes.
`;

// ── assemble file list ───────────────────────────────────────────────────────
const files = [
  ['.env.example', ENV_EXAMPLE],
  ['package.json', PKG],
  ['README.md', README],
  ['server/server.js', SERVER],
  ['server/quo.js', QUO_CLIENT],
  ['server/verify-webhook.js', VERIFIER],
];
if (opts.frontend === 'react') {
  files.push(['web/SendSms.jsx', WEB_JSX]);
} else {
  files.push(['web/index.html', WEB_HTML]);
  files.push(['web/app.js', WEB_JS]);
}

// ── write ──────────────────────────────────────────────────────────────────────
const root = path.resolve(opts.out);
let wrote = 0, skipped = 0;
console.log(`Quo scaffolder → ${root}  (frontend=${opts.frontend})${opts.dryRun ? '  [dry-run]' : ''}`);
for (const [rel, content] of files) {
  const dest = path.join(root, rel);
  if (fs.existsSync(dest) && !opts.force) { console.log(`  skip   ${rel} (exists — use --force)`); skipped++; continue; }
  if (opts.dryRun) { console.log(`  would  ${rel} (${content.length} bytes)`); wrote++; continue; }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, content);
  console.log(`  write  ${rel}`);
  wrote++;
}
console.log(`Done: ${wrote} file(s)${skipped ? `, ${skipped} skipped` : ''}.`);
if (!opts.dryRun) console.log(`Next: cd ${opts.out} && npm install && cp .env.example .env && npm start`);
