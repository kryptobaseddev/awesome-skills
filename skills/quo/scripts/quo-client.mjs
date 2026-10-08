#!/usr/bin/env node
/**
 * quo-client.mjs — A tiny, dependency-free client for the Quo (formerly
 * OpenPhone) REST API. Importable in your app AND runnable from the shell.
 * (TypeScript + TanStack AI tools: see assets/tanstack-ai/quo-client.ts.)
 *
 * Two live API surfaces share the host https://api.quo.com:
 *   • v1          — `/v1/...` paths, no version header. The ONLY way to send SMS.
 *   • 2026-03-30  — unprefixed paths, `Quo-Api-Version: 2026-03-30` header REQUIRED,
 *                   `{ data, nextCursor }` envelope, `limit` (1–50) + `after`,
 *                   bracket filters (`createdAt[gte]=...`, `status[in]=a,b`).
 *
 * It bakes in the things every Quo integration gets wrong:
 *   • Auth header is the RAW API key — `Authorization: <key>`, never `Bearer`.
 *   • Rate limit is 10 req/s/key → on 429 it backs off and retries.
 *   • Only GETs are retried automatically. A POST (especially a send) that times
 *     out or 5xx's may still have been applied — never blind-retry a send.
 *   • Send returns 202 (queued). `to` takes 1–10 E.164 numbers, but >1 creates ONE
 *     shared GROUP thread (everyone sees everyone) — so sendMessage requires
 *     `group: true` for multiple recipients. For private bulk sends, loop.
 *   • v1 lists paginate via maxResults + pageToken → nextPageToken (`totalItems`
 *     is unreliable); 2026-03-30 lists via limit + after → nextCursor.
 *
 * Usage (import):
 *   import { createQuoClient } from "./quo-client.mjs";
 *   const quo = createQuoClient({ apiKey: process.env.QUO_API_KEY });
 *   await quo.sendMessage({ from: "+15555550100", to: "+15555550111", content: "Hi" });
 *   const calls = await quo.v2("GET", "/calls", { query: { "status[in]": "missed,no-answer", include: "summary,voicemail" } });
 *   for await (const c of quo.paginateV2("/contacts", { "externalId[in]": "crm-1,crm-2" })) { ... }
 *   for await (const m of quo.paginate("/messages", { phoneNumberId, participants: ["+1..."] })) { ... }  // v1
 *
 * Usage (CLI):
 *   export QUO_API_KEY=...                       # raw key, no Bearer
 *   node quo-client.mjs numbers                  # GET /phone-numbers (2026-03-30)
 *   node quo-client.mjs send --from +15555550100 --to +15555550111 --text "Hi"
 *   node quo-client.mjs messages --number PN123 --with +15555550111
 *   node quo-client.mjs get /v1/contacts --query maxResults=10        # v1 path
 *   node quo-client.mjs get /calls --query limit=5                    # 2026-03-30 path
 *
 * Source: https://www.quo.com/docs/llms.txt (v1: /docs/mdx/api-reference/*, 2026-03-30: /docs/2026-03-30/*)
 */

const E164 = /^\+[1-9]\d{1,14}$/;
export const QUO_API_VERSION = '2026-03-30';

export function createQuoClient({
  apiKey = process.env.QUO_API_KEY || process.env.OPENPHONE_API_KEY,
  baseUrl = process.env.QUO_BASE_URL || 'https://api.quo.com',
  maxRetries = 4,
  fetchImpl = globalThis.fetch,
} = {}) {
  if (!apiKey) throw new Error('Quo API key required (set QUO_API_KEY or pass { apiKey }).');
  if (/^Bearer\s/i.test(apiKey)) {
    throw new Error('Strip the "Bearer " prefix — Quo uses the RAW key in the Authorization header.');
  }
  // Accept a legacy ".../v1" base and normalise to the bare host.
  const host = baseUrl.replace(/\/+$/, '').replace(/\/v1$/, '');

  /**
   * Low-level request. `surface` is 'v1' (path must start with /v1/) or '2026-03-30'.
   * Arrays in `query` repeat the key (v1 style); pass pre-joined strings for
   * 2026-03-30 bracket filters, e.g. { "status[in]": "missed,no-answer" }.
   */
  async function request(method, path, { query, body, headers, surface, retry } = {}) {
    const p = path.startsWith('/') ? path : `/${path}`;
    const s = surface ?? (p.startsWith('/v1/') ? 'v1' : QUO_API_VERSION);
    const url = new URL(host + p);
    for (const [k, v] of Object.entries(query || {})) {
      if (v == null) continue;
      for (const item of Array.isArray(v) ? v : [v]) url.searchParams.append(k, String(item));
    }
    const canRetry = retry ?? method === 'GET';

    let attempt = 0;
    for (;;) {
      const res = await fetchImpl(url, {
        method,
        headers: {
          Authorization: apiKey, // RAW key — NOT `Bearer ${apiKey}`
          ...(s === 'v1' ? {} : { 'Quo-Api-Version': s }),
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...headers,
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });

      // Retry idempotent requests on 429 (10 req/s/key) and transient 5xx, with backoff+jitter.
      if (canRetry && (res.status === 429 || res.status >= 500) && attempt < maxRetries) {
        const retryAfter = Number(res.headers.get('retry-after'));
        const waitMs = Number.isFinite(retryAfter) && retryAfter > 0
          ? retryAfter * 1000
          : Math.min(2 ** attempt * 1000, 16000) + Math.floor(Math.random() * 400);
        await new Promise((r) => setTimeout(r, waitMs));
        attempt += 1;
        continue;
      }

      const text = await res.text();
      const json = text ? safeJson(text) : undefined;
      if (!res.ok) {
        // 2026-03-30: { title, message, docs, trace?, errors?: [{ path, message, value, schema }] }
        // v1 / gateway: { message, code, status, errors[] } or { error: { message, key, trace } }
        const msg = json?.message || json?.error?.message || res.statusText;
        const code = json?.code || json?.error?.key;
        const trace = json?.trace || json?.error?.trace;
        const fields = Array.isArray(json?.errors)
          ? ' ' + json.errors.map((e) => `${e.path ?? ''} ${e.message ?? ''}`.trim()).join('; ')
          : '';
        const err = new Error(`Quo ${method} ${p} → ${res.status} ${msg}${code ? ` [${code}]` : ''}${fields}${trace ? ` (trace ${trace})` : ''}`);
        err.status = res.status;
        err.code = code;
        err.trace = trace;
        err.body = json ?? text;
        throw err;
      }
      return { status: res.status, data: json };
    }
  }

  // v1 helpers: paths are relative to /v1 for backwards compatibility ("/messages" → "/v1/messages").
  const v1path = (path) => (path.startsWith('/v1/') ? path : `/v1${path.startsWith('/') ? '' : '/'}${path}`);
  const get = (path, query) => request('GET', v1path(path), { query });
  const post = (path, body, query) => request('POST', v1path(path), { body, query });
  const patch = (path, body) => request('PATCH', v1path(path), { body });
  const del = (path) => request('DELETE', v1path(path));

  /** 2026-03-30 request; returns the parsed body ({ data } or { data, nextCursor }). */
  async function v2(method, path, { query, body, retry } = {}) {
    if (path.startsWith('/v1/')) throw new Error('v2() paths have no /v1 prefix');
    const { data } = await request(method, path, { query, body, retry, surface: QUO_API_VERSION });
    return data;
  }

  /**
   * Send an SMS (v1 — sending is not on 2026-03-30). 202 = queued.
   * Multiple recipients create ONE group thread; pass `group: true` to confirm that intent.
   */
  async function sendMessage({ from, to, content, userId, group = false, setInboxStatus } = {}) {
    if (!from) throw new Error('sendMessage: "from" is required (an E.164 number or a PN… phoneNumberId).');
    const recipients = Array.isArray(to) ? to : [to];
    if (recipients.length < 1 || recipients.length > 10) throw new Error('sendMessage: "to" takes 1–10 recipients.');
    if (recipients.length > 1 && !group) {
      throw new Error('sendMessage: several recipients create ONE shared group thread. Pass { group: true } if that is intended; for private messages send one at a time.');
    }
    for (const r of recipients) if (!E164.test(r)) throw new Error(`sendMessage: "to" must be E.164 (got "${r}").`);
    if (!content || !/\S/.test(content)) throw new Error('sendMessage: "content" must be 1–1600 non-whitespace chars.');
    if (content.length > 1600) throw new Error('sendMessage: "content" exceeds 1600 chars.');
    const { data } = await request('POST', '/v1/messages', {
      body: { from, to: recipients, content, ...(userId ? { userId } : {}), ...(setInboxStatus ? { setInboxStatus } : {}) },
      retry: false, // never auto-retry a send: a 5xx/timeout may still have sent it
    });
    return data?.data ?? data; // 202 Accepted; delivery confirmed via message.delivered webhook or GET
  }

  /**
   * v1: async-iterate a list endpoint. Loops on nextPageToken until null — never
   * trusts totalItems. `params` are the endpoint's required query args.
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

  /** 2026-03-30: async-iterate a list endpoint via limit + after → nextCursor. */
  async function* paginateV2(path, query = {}) {
    let after = null;
    do {
      const page = await v2('GET', path, { query: { ...query, limit: query.limit ?? 50, ...(after ? { after } : {}) } });
      for (const item of page?.data ?? []) yield item;
      after = page?.nextCursor ?? null;
    } while (after);
  }

  return { request, get, post, patch, del, v2, sendMessage, paginate, paginateV2, baseUrl: host };
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
        const data = await quo.v2('GET', '/phone-numbers', { query: { limit: 50 } });
        console.log(JSON.stringify(data, null, 2));
        break;
      }
      case 'send': {
        const to = String(args.to || '').split(',').filter(Boolean);
        const out = await quo.sendMessage({ from: args.from, to, content: args.text, userId: args.user, group: Boolean(args.group) });
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
        const { data } = await quo.request('GET', path, { query });
        console.log(JSON.stringify(data, null, 2));
        break;
      }
      default:
        console.log('Commands: numbers | send --from --to +1..[,+1..] --text [--user] [--group] | messages --number PN… --with +E164 [--limit] | get </v1/path or /path> [--query k=v]');
        process.exit(2);
    }
  };
  run().catch((e) => { console.error(e.message); process.exit(1); });
}
