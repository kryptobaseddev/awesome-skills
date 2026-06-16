---
name: quo
description: "Build, scaffold, and integrate Quo — formerly OpenPhone — telephony into a full-stack app: send & receive SMS/text messages, list and analyze calls (recordings, AI summaries, transcripts, voicemails), manage contacts, conversations, tasks, users, and phone numbers via the Quo REST API (https://api.quo.com/v1), plus signature-verified webhooks. Ships a one-command scaffolder that emits a runnable integration (Express + API client + send-SMS route + a signature-verifying webhook receiver), a preflight checker, a tested webhook verifier (Node + Python), and an importable client. Use whenever the user wants to add, build, or scaffold SMS/text messaging, programmatic calls, an OpenPhone or Quo integration, two-way SMS, call transcripts/summaries, contact sync, or Quo webhooks — even if they only say 'OpenPhone', 'Quo', or 'send a text from my app'. Bakes in the raw-API-key auth gotcha (no Bearer token), A2P 10DLC registration, the 202/one-recipient/E.164 send rules, and the whsec_ webhook signing scheme."
license: MIT
compatibility: >-
  Bundled scripts need Node 18+ (built-in fetch + node:crypto) and/or Python
  3.8+ stdlib, plus bash + curl for preflight. Integrations target any stack
  that makes HTTPS calls (Node/Express, Next.js, Python, Ruby, PHP, Go); the
  scaffolder emits Node/Express + vanilla or React. A Quo (OpenPhone) account
  with workspace owner/admin is needed to generate an API key; US SMS also
  requires A2P 10DLC registration.
inputs:
  - name: QUO_API_KEY
    description: "Quo (OpenPhone) API key — the RAW key, sent verbatim in the Authorization header (NO 'Bearer ' prefix). Generate at Quo workspace → Settings → API (owner/admin only); each key has full account access. The legacy var OPENPHONE_API_KEY is also accepted by the bundled scripts."
    required: true
  - name: QUO_WEBHOOK_KEY
    description: "Beta webhook signing secret, prefixed 'whsec_'. Returned ONLY in the POST https://api.quo.com/webhooks response (data.key) and on rotate — store it immediately. Used solely to verify inbound webhook signatures."
    required: false
  - name: QUO_BASE_URL
    description: "Optional host override. Default https://api.quo.com/v1 (the canonical host per the OpenAPI servers block). https://api.openphone.com/v1 is a live, identical legacy alias."
    required: false
metadata:
  author: github.com/kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-06-15 17:30:00"
  category: communication
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
---

# Quo (formerly OpenPhone) — REST API & Webhooks Integration

Add programmatic phone communications to a site or app: **send and receive
SMS/text messages**, pull **call** history with AI **summaries / transcripts /
recordings / voicemails**, manage **contacts** (and custom fields),
**conversations**, **tasks**, **users**, and **phone numbers**, and react to
events in real time via **webhooks**. Quo is the rebrand of OpenPhone; the two
share one API.

> **Naming:** the product is now **Quo** (`quo.com`), but the REST API, the
> OpenAPI spec, and most existing integrations are unchanged from OpenPhone. The
> canonical host is `https://api.quo.com/v1`; `https://api.openphone.com/v1` is a
> live, byte-identical legacy alias (both verified). Pick one and keep it in a
> single configurable constant.

## Facts that prevent broken work

Read this table first — each row is a real failure integrators hit.

| Fact | Consequence |
|---|---|
| **Auth is the RAW API key** in the `Authorization` header. The docs say verbatim *"The Quo API does not use a Bearer token."* | `Authorization: Bearer <key>` → `401 Unauthorized`. Send the key value alone: `Authorization: <key>`. |
| **Base URL** is `https://api.quo.com/v1` (OpenAPI `servers`); `https://api.openphone.com/v1` is an identical alias | Hardcoding one host is fine, but don't mix `/v1` REST with the **un-prefixed** beta webhook host (`https://api.quo.com/webhooks`, no `/v1`). |
| **Sending SMS to US numbers requires A2P 10DLC carrier registration** | Without it, `POST /v1/messages` returns **`400` code `0206400` "A2P Registration Not Approved"** — a 400 here is NOT a malformed body. |
| **Send is async and returns `202`**, not `200` | Treat `202` as *queued*. `to` must be **exactly one** E.164 recipient (`maxItems: 1` — no fan-out per call); `content` is 1–1600 non-whitespace chars; **MMS is not supported**. |
| `from` is an **E.164 number OR a `PN…` phoneNumberId** | The legacy top-level `phoneNumberId` body field is deprecated — use `from`. `GET /v1/phone-numbers` gives you valid senders. |
| **Rate limit: 10 requests/second per API key** → `429` | The docs document **no** `Retry-After` / `RateLimit-*` headers — implement your own exponential backoff (the bundled client already does). |
| **Pagination:** `maxResults` (required, max 100) + `pageToken` → response `nextPageToken` | `totalItems` is **documented as inaccurate** — loop until `nextPageToken` is `null`; never page on `totalItems`. |
| **List messages/calls are scoped, not global** | `GET /v1/messages` and `/v1/calls` require `phoneNumberId` **and** `participants` **and** `maxResults` together. There is no "list everything" call. |
| **Beta webhooks are signed; legacy v1 webhooks are not** | For verifiable authenticity use the **beta** webhook API: HMAC-SHA256 (base64) over `{webhook-id}.{webhook-timestamp}.{raw-body}` with a `whsec_…` secret. Verify the **raw** body before parsing. |
| **Webhook idempotency key is the `webhook-id` HEADER** | Not the envelope `id`. Deliveries retry (8 attempts over ~27h) and arrive out of order — dedupe on `webhook-id`, retain ≥28h, make handlers order-independent. |
| **AI features are plan-gated** | Call **summaries** and **transcripts** (and their webhooks) require a **business or scale** plan; lower plans get `403`/absent. They're also async — poll `processingStatus` until `completed`. |
| **Error envelope is inconsistent** | The live gateway returns `{ "error": { "message", "key", "trace" } }`; the OpenAPI documents `{ "message", "code", "status", "errors": [] }`. Parse defensively: `body.error?.message ?? body.message`. |
| **ID prefixes are load-bearing** | `AC…` activity/message/call · `PN…` phone number · `US…` user · `CN…` conversation · `CT…` contact · `VM…` voicemail. Endpoints validate them by regex. |

## Preflight

Confirm tooling + key before writing code, so the first failure points at config:

```bash
bash scripts/quo-preflight.sh            # node/curl + QUO_API_KEY + Bearer-mistake checks
bash scripts/quo-preflight.sh --probe    # also calls GET /v1/phone-numbers live (real 401 vs 200)
```

It accepts `QUO_API_KEY` (or the legacy `OPENPHONE_API_KEY`), flags a stray
`Bearer ` prefix, and validates key **presence** — a live `200`/`401` from
`--probe` is what proves the key actually works.

## Build an integration in one command (scaffold)

The fastest path to a working integration is to **generate** it, then customize.
`scripts/scaffold-quo.mjs` writes a complete, runnable full-stack app — an
Express backend (API client + send-SMS route + a **signature-verified** beta
webhook receiver) and a frontend — with the client + webhook verifier **inlined**
(the generated project has zero dependency on this skill).

```bash
node scripts/scaffold-quo.mjs --out ./quo-app                 # vanilla JS frontend
node scripts/scaffold-quo.mjs --out ./quo-app --frontend react
node scripts/scaffold-quo.mjs --help                          # flags; --dry-run previews
```

Then: `cd quo-app && npm install && cp .env.example .env` (fill in `QUO_API_KEY`),
`npm start`. Customize the emitted code with the references below — the scaffold
is a correct skeleton, not a black box.

## Quick start by hand — send an SMS

The shortest path to "text from my app": one server-side call with the raw-key
header. Use the bundled client so the auth/202/E.164 rules are handled for you.

```ts
import { createQuoClient } from "./scripts/quo-client.mjs";

const quo = createQuoClient({ apiKey: process.env.QUO_API_KEY }); // raw key, no Bearer

const msg = await quo.sendMessage({
  from: "+15555550100",          // one of YOUR Quo numbers (E.164) or its PN… id
  to: "+15555550111",            // exactly ONE E.164 recipient
  content: "Hello from Quo 👋",  // 1–1600 chars
});
// 202 Accepted → queued. Final delivery arrives as a `message.delivered` webhook,
// or poll GET /v1/messages/{id} (status: queued|sent|delivered|undelivered).
```

Raw HTTP equivalent (note the header — **no `Bearer`**):

```bash
curl -X POST https://api.quo.com/v1/messages \
  -H "Authorization: $QUO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"from":"+15555550100","to":["+15555550111"],"content":"Hello from Quo"}'
```

For the CLI: `node scripts/quo-client.mjs send --from +1… --to +1… --text "Hi"`.

## Quick start by hand — receive a verified webhook

Use the **beta** webhook API (it's signed). Create a subscription, save the
`whsec_…` secret, and verify every delivery against the **raw** body:

```ts
import express from "express";
import { verifyQuoWebhook } from "./scripts/verify-webhook.js";

// express.raw — the signature is over the raw bytes; a JSON parser first breaks it.
app.post("/webhooks/quo", express.raw({ type: "*/*" }), (req, res) => {
  if (!verifyQuoWebhook(req.headers, req.body, process.env.QUO_WEBHOOK_KEY)) {
    return res.status(400).send("bad signature");
  }
  const id = req.headers["webhook-id"];       // idempotency key (NOT envelope.id)
  // ...dedupe on `id` (retain ≥28h), then handle:
  const event = JSON.parse(req.body.toString());
  if (event.type === "message.received") {
    console.log("inbound:", event.data.resource.text);
  }
  res.status(200).json({ ok: true });          // ack fast; do slow work async
});
```

Create the subscription (un-prefixed host, version header required):

```bash
curl -X POST https://api.quo.com/webhooks \
  -H "Authorization: $QUO_API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-quo-api-version: 2026-03-30" \
  -d '{"url":"https://YOUR_HOST/webhooks/quo","events":["message.received","message.delivered","call.completed"]}'
# Save data.key (whsec_…) into QUO_WEBHOOK_KEY — it is shown only once.
```

Prove your verifier works without any traffic: `node scripts/verify-webhook.js --selftest`.

## API surface

All REST paths are under `https://api.quo.com/v1`. Beta webhooks live at
`https://api.quo.com/webhooks` (no `/v1`).

| Resource | Endpoints | Reference |
|---|---|---|
| **Messages** | `POST /messages` · `GET /messages` · `GET /messages/{id}` | `references/messages-and-numbers.md` |
| **Phone numbers** | `GET /phone-numbers` · `GET /phone-numbers/{id}` | `references/messages-and-numbers.md` |
| **Calls** | `GET /calls` · `/calls/{id}` · `/call-recordings/{id}` · `/call-summaries/{id}` · `/call-transcripts/{id}` · `/call-voicemails/{id}` | `references/calls.md` |
| **Contacts** | `POST/GET/PATCH/DELETE /contacts` · `GET /contact-custom-fields` | `references/contacts.md` |
| **Conversations** | `GET /conversations` · `POST /conversations/{id}/mark-as-read` | `references/conversations-and-tasks.md` |
| **Tasks** | `GET/POST /tasks` · `/tasks/{id}` (+ complete, reopen, assign, due-date, link actions) | `references/conversations-and-tasks.md` |
| **Users** | `GET /users` · `GET /users/{id}` | `references/webhooks-v1-and-users.md` |
| **Webhooks (beta, signed)** | `POST/GET/PATCH/DELETE /webhooks` (+ rotate, test, deliveries) | `references/webhooks.md` |
| **Webhooks (legacy v1)** | `POST /v1/webhooks/{messages,calls,call-summaries,call-transcripts}` | `references/webhooks-v1-and-users.md` |

## Where to go next

Each reference is self-contained and source-cited (`https://www.quo.com/docs/mdx/...`):

| Task | Reference |
|---|---|
| Auth, base URL, versioning, **error codes**, rate limits, pagination | `references/api-basics.md` |
| Send/list/get messages, phone numbers, the **202 + E.164 + scoping** rules | `references/messages-and-numbers.md` |
| Calls + recordings, summaries, transcripts, voicemails, plan gating, async AI | `references/calls.md` |
| Contacts CRUD, custom fields, the `defaultFields`/`customFields` shape, sync-by-externalId | `references/contacts.md` |
| Conversations + the full **Tasks** lifecycle (no status enum — `completed`/`isDeleted`) | `references/conversations-and-tasks.md` |
| **Beta webhooks**: signature validation, event payload catalog, retries, migration | `references/webhooks.md` |
| Legacy v1 webhooks (unsigned) + Users | `references/webhooks-v1-and-users.md` |
| Building with **AI/LLMs**, A2P 10DLC registration, pricing & cost-minimization | `references/ai-cost-and-registration.md` |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/scaffold-quo.mjs` | **Generate a complete, runnable integration** (Express client + send route + verified beta webhook receiver + frontend + env + README). `--frontend vanilla\|react`. |
| `scripts/quo-client.mjs` | Importable + CLI REST client: raw-key auth, 429 backoff, `sendMessage` (202/E.164 guards), `paginate` (cursor-correct). |
| `scripts/verify-webhook.js` / `verify_webhook.py` | Verify a beta webhook signature (HMAC-SHA256 base64 over `{id}.{ts}.{body}`, `whsec_` secret, replay window, rotation-aware). `--selftest` round-trips offline. Node↔Python parity verified. |
| `scripts/quo-preflight.sh` | Check node/curl, the key, the `Bearer` mistake, and (optional `--probe`) live reachability. |

## Common mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | `Authorization: Bearer <key>` | Send the **raw** key: `Authorization: <key>`. Quo uses no Bearer token. |
| 2 | Treating `202` as failure / assuming sync delivery | `202` = queued. Confirm via `GET /v1/messages/{id}` or a `message.delivered` webhook. |
| 3 | Sending US SMS without A2P registration | Complete US Carrier (A2P 10DLC) registration first, or every send returns `400 0206400`. |
| 4 | Multiple recipients in one send | `to` is `maxItems: 1`. Fan out client-side, under 10 req/s. |
| 5 | Verifying a webhook against parsed JSON | Verify the **raw** body (`express.raw` / Flask `get_data()`); re-serialized JSON won't match the HMAC. |
| 6 | Deduping webhooks on `event.id` | Use the **`webhook-id` header**; retain ≥28h to cover the retry window. |
| 7 | Paginating on `totalItems` | It's documented as inaccurate — loop until `nextPageToken` is `null`. |
| 8 | Expecting summaries/transcripts on any plan | They need a **business/scale** plan and are async — gate on `processingStatus`. |
| 9 | Using the legacy `OpenPhone-Signature` verifier on beta deliveries | Beta uses `webhook-*` headers + `whsec_` — the schemes are not interchangeable. |
| 10 | Polling lists in a loop | Prefer webhooks over polling to conserve the 10 req/s budget. |

## Resources

- API reference: https://www.quo.com/docs/mdx/api-reference/introduction
- Doc index (machine-readable): https://www.quo.com/docs/llms.txt
- OpenAPI spec: https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json
- LLM-ready docs bundle: https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-llm-ready-docs-prod.zip
- Building with AI/LLMs guide: https://www.quo.com/docs/mdx/guides/building-with-ai-llms
