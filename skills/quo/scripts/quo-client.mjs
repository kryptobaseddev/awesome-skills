#!/usr/bin/env node
/**
 * quo-client.mjs — A tiny, dependency-free client for the Quo (formerly
 * OpenPhone) REST API. Importable in your app AND runnable from the shell.
 *
 * It bakes in the things every Quo integration gets wrong:
 *   • Auth header is the RAW API key — `Authorization: <key>`, never `Bearer`.
 *   • Base URL is https://api.quo.com/v1 (api.openphone.com/v1 is a live alias).
 *   • Rate limit is 10 req/s/key → on 429 it backs off and retries.
 *   • Send is async: POST /v1/messages returns 202, `to` is exactly ONE E.164
 *     recipient, `content` must be 1–1600 non-whitespace chars.
 *   • List endpoints cursor-paginate via maxResults + pageToken → nextPageToken;
 *     `totalItems` is documented as inaccurate, so paginate() loops until the
 *     cursor is null and never trusts totalItems.
 *
 * Usage (import):
 *   import { createQuoClient } from "./quo-client.mjs";
 *   const quo = createQuoClient({ apiKey: process.env.QUO_API_KEY });
 *   await quo.sendMessage({ from: "+15555550100", to: "+15555550111", content: "Hi" });
 *   for await (const m of quo.paginate("/messages", { phoneNumberId, participants: ["+1..."] })) { ... }
 *
 * Usage (CLI):
 *   export QUO_API_KEY=...                       # raw key, no Bearer
 *   node quo-client.mjs numbers                  # GET /v1/phone-numbers
 *   node quo-client.mjs send --from +15555550100 --to +15555550111 --text "Hi"
 *   node quo-client.mjs messages --number PN123 --with +15555550111
 *   node quo-client.mjs get /v1/contacts --query maxResults=10
 *
 * Source: https://www.quo.com/docs/mdx/api-reference/*
 */

const E164 = /^\+[1-9]\d{1,14}$/;

export function createQuoClient({
  apiKey = process.env.QUO_API_KEY || process.env.OPENPHONE_API_KEY,
  baseUrl = process.env.QUO_BASE_URL || 'https://api.quo.com/v1',
  maxRetries = 4,
  fetchImpl = globalThis.fetch,
} = {}) {
  if (!apiKey) throw new Error('Quo API key required (set QUO_API_KEY or pass { apiKey }).');
  if (/^Bearer\s/i.test(apiKey)) {
    throw new Error('Strip the "Bearer " prefix — Quo uses the RAW key in the Authorization header.');
  }
  const root = baseUrl.replace(/\/+$/, '');

  async function request(method, path, { query, body, headers } = {}) {
    const url = new URL(root + (path.startsWith('/') ? path : `/${path}`));
    for (const [k, v] of Object.entries(query || {})) {
      if (v == null) continue;
      for (const item of Array.isArray(v) ? v : [v]) url.searchParams.append(k, String(item));
    }

    let attempt = 0;
    // Retry on 429 (rate limit, 10 req/s/key) and transient 5xx with backoff+jitter.
    for (;;) {
      const res = await fetchImpl(url, {
        method,
        headers: {
          Authorization: apiKey, // RAW key — NOT `Bearer ${apiKey}`
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...headers,
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });

      if ((res.status === 429 || res.status >= 500) && attempt < maxRetries) {
        const retryAfter = Number(res.headers.get('retry-after'));
        const waitMs = Number.isFinite(retryAfter) && retryAfter > 0
          ? retryAfter * 1000
          : Math.min(2 ** attempt * 250, 8000) + Math.floor(Math.random() * 200);
        await new Promise((r) => setTimeout(r, waitMs));
        attempt += 1;
        continue;
      }

      const text = await res.text();
      const json = text ? safeJson(text) : undefined;
      if (!res.ok) {
        // Quo returns either { error: { message, key } } (gateway) or
        // { message, code, status, errors[] } (documented) — handle both.
        const msg = json?.error?.message || json?.message || res.statusText;
        const code = json?.error?.key || json?.code;
        const err = new Error(`Quo ${method} ${path} → ${res.status} ${msg}${code ? ` [${code}]` : ''}`);
        err.status = res.status;
        err.code = code;
        err.body = json ?? text;
        throw err;
      }
      return { status: res.status, data: json };
    }
  }

  const get = (path, query) => request('GET', path, { query });
  const post = (path, body, query) => request('POST', path, { body, query });
  const patch = (path, body) => request('PATCH', path, { body });
  const del = (path) => request('DELETE', path);

  /** Send a single SMS. `to` is one E.164 recipient (the API caps it at one). */
  async function sendMessage({ from, to, content, userId } = {}) {
    if (!from) throw new Error('sendMessage: "from" is required (an E.164 number or a PN… phoneNumberId).');
    const recipients = Array.isArray(to) ? to : [to];
    if (recipients.length !== 1) throw new Error('sendMessage: "to" must be exactly ONE recipient (API maxItems=1).');
    if (!E164.test(recipients[0])) throw new Error(`sendMessage: "to" must be E.164 (got "${recipients[0]}").`);
    if (!content || !/\S/.test(content)) throw new Error('sendMessage: "content" must be 1–1600 non-whitespace chars.');
    if (content.length > 1600) throw new Error('sendMessage: "content" exceeds 1600 chars.');
    const { data } = await post('/messages', { from, to: recipients, content, ...(userId ? { userId } : {}) });
    return data?.data ?? data; // 202 Accepted; final delivery confirmed via GET /messages/{id} or a webhook
  }

  /**
   * Async-iterate every item of a cursor-paginated list endpoint. Loops on
   * nextPageToken until null — never trusts the (inaccurate) totalItems.
   * `params` are the endpoint's required query args (e.g. phoneNumberId,
   * participants, maxResults).
   */
  async function* paginate(path, params = {}) {
    let pageToken;
    const maxResults = params.maxResults ?? 50;
    do {
      const { data } = await get(path, { ...params, maxResults, ...(pageToken ? { pageToken } : {}) });
      for (const item of data?.data ?? []) yield item;
      pageToken = data?.nextPageToken ?? null;
    } while (pageToken);
  }

  return { request, get, post, patch, del, sendMessage, paginate, baseUrl: root };
}

function safeJson(text) {
  try { return JSON.parse(text); } catch { return undefined; }
}

// ── CLI ───────────────────────────────────────────────────────────────────────
function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) out[key] = true;
      else { out[key] = next; i += 1; }
    } else out._.push(a);
  }
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  const run = async () => {
    const quo = createQuoClient();
    switch (cmd) {
      case 'numbers': {
        const { data } = await quo.get('/phone-numbers');
        console.log(JSON.stringify(data, null, 2));
        break;
      }
      case 'send': {
        const out = await quo.sendMessage({ from: args.from, to: args.to, content: args.text, userId: args.user });
        console.log('202 Accepted — queued. Message:', JSON.stringify(out, null, 2));
        break;
      }
      case 'messages': {
        if (!args.number || !args.with) throw new Error('messages needs --number PN… --with +E164');
        let n = 0;
        for await (const m of quo.paginate('/messages', { phoneNumberId: args.number, participants: [args.with] })) {
          console.log(`${m.createdAt}  ${m.direction}  ${m.status}  ${m.text ?? ''}`);
          if (++n >= Number(args.limit || 25)) break;
        }
        break;
      }
      case 'get': {
        const path = args._[1];
        const query = Object.fromEntries((args.query ? [args.query].flat() : []).map((q) => q.split('=')));
        const { data } = await quo.get(path, query);
        console.log(JSON.stringify(data, null, 2));
        break;
      }
      default:
        console.log('Commands: numbers | send --from --to --text [--user] | messages --number PN… --with +E164 [--limit] | get <path> [--query k=v]');
        process.exit(2);
    }
  };
  run().catch((e) => { console.error(e.message); process.exit(1); });
}
