# Quo API — building with AI, messaging cost, plan gates and US carrier registration

Covers what an AI-driven Quo integration costs, what blocks it from sending (A2P 10DLC registration, subscription, credits, daily caps), which features need which plan, and the ground rules Quo publishes for agent-built integrations. Endpoint-by-endpoint detail for messages, calls and webhooks lives in the other reference files. The hosted MCP server is covered in `mcp.md`.

## Contents

- [Two API surfaces, one host](#two-api-surfaces-one-host)
- [Building with AI and LLMs](#building-with-ai-and-llms)
- [Messaging cost](#messaging-cost)
- [Segment math](#segment-math)
- [US carrier registration (A2P 10DLC)](#us-carrier-registration-a2p-10dlc)
- [Account, plan and credit gates](#account-plan-and-credit-gates)
- [Error codes that mean "cannot send"](#error-codes-that-mean-cannot-send)
- [Cost and safety controls for AI agents](#cost-and-safety-controls-for-ai-agents)
- [What changed since v1.0.0 of this reference](#what-changed-since-v100-of-this-reference)
- [Sources](#sources-checked-2026-10-08)

## Two API surfaces, one host

| | v1 | 2026-03-30 |
|---|---|---|
| Base | `https://api.quo.com/v1/...` | `https://api.quo.com/...` (no `/v1`) |
| Version header | none | **`Quo-Api-Version: 2026-03-30`** (400 without it) |
| Auth | `Authorization: YOUR_API_KEY`, raw key, **no `Bearer`** | same |
| Rate limit | 10 req/s per key → `429` | same |
| Sending SMS | **`POST /v1/messages` is the only send endpoint** | no send endpoint, but has `POST /messages/{messageId}/retry` for `failed` messages |
| Errors | `{title, description, code, status, docs, message, errors}` with numeric `code` such as `0206400` | `{title, message, docs, trace?, errors[{path,message,value,schema}]}`. Branch on HTTP status, then `errors[].path` |

Keys: Workspace Settings → **API** → *Generate API key*. You need **owner or admin** rights, and spaces are not allowed in the name. A key has admin-level reach over the whole workspace. Name keys after their consumer (`claude-agent`, `crm-sync`) so each can be audited and revoked on its own.

## Building with AI and LLMs

There are two distinct cases. Pick the right one first.

| You want… | Use | Why |
|---|---|---|
| A person working with their Quo data in Claude or ChatGPT | **Quo MCP** (`https://mcp.quo.com/mcp`), on Starter, Business and Scale plans | Per-user OAuth, no key, curated tools. See `mcp.md`. |
| Your product or backend acting on Quo (scheduled, webhook-driven, policy-heavy) | **REST API** with your own tool definitions | Deterministic schemas, signed webhooks, your own guardrails |

**Feed an agent the source of truth, not memory:**

| Resource | URL |
|---|---|
| Docs index (start here) | `https://www.quo.com/docs/llms.txt` |
| Whole docs as one file | `https://www.quo.com/docs/llms-full.txt` |
| OpenAPI 2026-03-30 (authoritative for the new surface) | `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-2026-03-30-prod.json` |
| OpenAPI v1 (needed for sending) | `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json` |
| Offline docs bundle | `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-llm-ready-docs-prod.zip` |

The spec JSON files still live in the legacy `openphone-public-api-prod` bucket, which is expected. When generated code and the spec disagree, the spec wins.

**Quo's published ground rules for agent integrations** (Build with AI & agents page):
1. **The key never enters the conversation.** Keep it in env or a secret store, never in a prompt or generated source. Assume anything an LLM reads, it may repeat.
2. **Give the agent its own key**, named, so its traffic is visible and revocable on its own.
3. **Tell it the budget**: 10 req/s. Left alone, agents poll.
4. **Check generated code against the spec.** Code can compile and still call endpoints that don't exist.
5. **Let errors do their job.** Pass the structured 2026-03-30 errors (`errors[].path`) back to the agent raw so it can fix the request.

The older v1-era "Building with AI LLMs" guide adds: keep sensitive data out of prompts, validate all generated code, handle errors properly, and monitor usage. Its documented patterns are message automation, contact sync, call summary and recording processing, and task-based scheduling or reminders.

**Webhooks over polling.** For agents that react to inbound SMS, completed calls, or finished summaries and transcripts, subscribe to webhooks instead of polling list endpoints. Polling burns the shared 10 req/s budget and adds latency. Webhooks created in the Quo app and webhooks created via the API are mutually invisible. Signing, event names and payloads are in the webhooks reference files.

## Messaging cost

From the API pricing page:

| Destination | Price |
|---|---|
| US and Canada SMS | **$0.01 per segment** |
| International SMS | **$0.01 + country-specific rate per segment** (rates at `https://www.quo.com/rates`) |

- You are charged **only for outgoing API-powered messages**: direct API calls and messages sent by apps or integrations built on the API. **Quo MCP sends count as API-powered messages** too (MCP tools page).
- **Billing is credit-based.** Buy credits under **Plans & Billing**. They are deducted when a message is sent, and **auto-recharge** is available. Partial credits cannot be used: if the balance cannot cover a message's full cost, the API returns an error and **the message is not sent**. The spec documents no specific error code for this, so treat the code as unverified.
- **MMS.** The pricing page says *"MMS is not supported in the current API version."* The v1 send body has no media field, so you can only send text. Message **reads** (`GET /v1/messages`, `GET /v1/messages/{id}` since 2026-08-21, and the 2026-03-30 message objects) do include a `media[]` array (`{url, type}`) for MMS sent or received in the Quo app.
- **Group sends.** `POST /v1/messages` now accepts up to **10** numbers in `to` (one group message). The pricing page does not say how a group message is billed. Budget it as **segments × recipients** until verified.
- Inbound messages, reads and webhooks are not listed as charges.

## Segment math

- A segment is the billing unit. The segment count depends on **length** and **character set**.
- **GSM-7 only** (A–Z, a–z, 0–9, space, basic punctuation): **up to 160 characters per segment**.
- **Any** non-GSM character (é, ñ, ü, curly or smart quotes, emoji, many international scripts) switches the **whole message** to the **70-character** limit, not just the part containing it.
- Quo enables **smart encoding** automatically ("chooses the most efficient encoding"). The docs do not say which characters it rewrites, so do not rely on it for emoji or real accented text.
- Multipart messages: the pricing page only gives 160 and 70. Under the standard SMS concatenation convention each part of a multipart message holds **153** (GSM-7) or **67** (UCS-2) characters. That figure comes from the carrier standard, not Quo docs. Estimate with the segment calculator Quo links to: `https://twiliodeved.github.io/message-segment-calculator/`.
- The API maximum is `content` ≤ **1,600 characters** (v1 send and the MCP send tools). That is about 11 GSM-7 segments or about 24 UCS-2 segments per recipient.

Quick estimator for a cost-preview tool. It is deliberately conservative: Quo's page says accented letters force the 70-character limit, even though some of them are in the GSM-7 table. It assumes standard concatenation; GSM-7 extension characters such as `{ } [ ] ~ \ | ^ €` count double and are approximated here.

```ts
const GSM7 = /^[A-Za-z0-9 \r\n@£$¥_!"#%&'()*+,\-./:;<=>?¡¿§^{}\\[~\]|€]*$/ // conservative: Quo bills é, ñ, ü at 70, so accents count as UCS-2
export function estimateSegments(text: string): { encoding: 'GSM-7' | 'UCS-2'; segments: number } {
  const gsm = GSM7.test(text)
  const len = gsm ? [...text].reduce((n, c) => n + ('^{}\\[~]|€'.includes(c) ? 2 : 1), 0) : text.length // UCS-2 counts UTF-16 units
  const [single, multi] = gsm ? [160, 153] : [70, 67]
  return { encoding: gsm ? 'GSM-7' : 'UCS-2', segments: len <= single ? 1 : Math.ceil(len / multi) }
}
// US/CA cost ≈ segments × recipients × $0.01
```

Ways to cut segments, from the pricing page: stick to plain Latin characters, avoid special characters and emoji, drop unneeded line breaks (each one counts), shorten long URLs, and use widely understood abbreviations. For LLM-written texts, add a post-processing step that normalizes smart quotes, en and em dashes, and ellipsis characters to ASCII, and strips emoji unless the user asked for them. LLM output is full of these characters, and one of them doubles the cost of the whole message.

## US carrier registration (A2P 10DLC)

> *"To send text messages to US numbers via the API, you must complete US Carrier Registration."* (Authentication and Send-your-first-message pages)

- Registration happens **in the Quo app or with support**. Neither spec exposes registration endpoints. Both specs declare an "A2P Registration" tag, but no operations use it. Quo's guide is linked from the docs at `https://support.openphone.com/hc/en-us/articles/15519949741463-Guide-to-US-carrier-registration-for-OpenPhone-customers` (this legacy domain is still linked from the docs).
- Until registration is approved, `POST /v1/messages` to a US number returns **`400`** with `code: "0206400"` and `title: "A2P Registration Not Approved"`. A 400 from send is therefore **not necessarily a malformed body**: check `code` before "fixing" the payload.
- After approval, 10DLC throughput has a **daily cap**. Hitting it returns **`403`** with `code: "0204403"` and `title: "A2P 10DLC Daily Message Cap Reached"`. To raise the cap, contact support via `https://support.quo.com/help/submit-a-request`. Do not retry the same day in a loop.
- The docs do not state registration requirements for Canadian or international destinations. Treat them as **unverified** and test with a real send.
- MCP sends run through the same Quo messaging. Expect the same registration and cap behavior (an inference; the MCP docs do not say so).

```json
{
  "title": "A2P Registration Not Approved",
  "description": "A2P Registration Not Approved",
  "code": "0206400",
  "status": 400,
  "docs": "https://quo.com/docs",
  "message": "…",
  "errors": []
}
```

## Account, plan and credit gates

| Gate | Effect | How to detect up front |
|---|---|---|
| Active Quo subscription | Required for any API access. Expired subscription: v1 message endpoints return **`402`** `0201402` "Subscription Expired" | 2026-03-30 `GET /organization` returns `data.subscriptionStatus`: `active` or `expired` (`expired` also covers "no subscription") |
| Owner or admin | Needed to create API keys | — |
| Messaging credits | Insufficient balance: error, message not sent (code undocumented) | No balance endpoint in either spec. Watch Plans & Billing and enable auto-recharge |
| US A2P 10DLC registration | `400` `0206400` on US sends | No API. Do one test send to a US number |
| 10DLC daily cap | `403` `0204403` | — |
| **Business or Scale plan** | Call **summaries** and **transcripts** (REST endpoints and the summary/transcript webhooks). On lower plans they return no data | Spec text: "only available on business and scale plans" |
| MCP connector | Starter, Business, Scale. `fetch-call-transcripts` needs Business | See `mcp.md` |
| Number membership | `userId` on a send must be a member of the sending number (v1 spec) | 2026-03-30 phone-number members endpoint |

## Error codes that mean "cannot send"

v1 `POST /v1/messages` responses as declared in the spec:

| HTTP | `code` | `title` | Agent action |
|---|---|---|---|
| 202 | — | (accepted) | Not yet delivered. Wait for the `message.delivered` webhook or poll the message |
| 400 | `0206400` | A2P Registration Not Approved | Stop. Surface "complete US carrier registration" to the user |
| 401 | `0200401` | Unauthorized | Key is missing, wrong, or sent as `Bearer …` |
| 402 | `0201402` | Subscription Expired | Stop. The account owner must fix billing |
| 403 | `0204403` | A2P 10DLC Daily Message Cap Reached | Stop for the day. Ask support to raise the cap |
| 404 | `0200404` | Not Found | Bad `from` or number not in workspace |
| 429 | — | (rate limited) | Exponential backoff with jitter |
| 500 | `0201500` | Unknown | Back off and retry. Log for support |

The 2026-03-30 surface uses the same status codes without the numeric `code`. Log `trace` and send it to support+developers@quo.com. **4xx means your side, 5xx means Quo's side.** Retrying a 400 just spends rate limit.

**Retries for sends.** v1 `POST /v1/messages` takes no idempotency key, so a blind retry after a timeout can double-send and double-bill. Read the conversation first. For messages whose status is `failed`, use the 2026-03-30 `POST /messages/{messageId}/retry`. Only `failed` messages **without** an error code are retryable. `undelivered` and permanently failed messages are not. The docs do not say whether a retry is billed again (unverified).

## Cost and safety controls for AI agents

- **Human approval on every send tool.** Show the sender, every recipient, the final text, the estimated segments and cost, and whether recipients will see each other (a group thread exposes numbers).
- **Hard caps in code, not in the prompt.** Enforce a maximum number of recipients per call, a maximum number of sends per conversation, user and day, and a maximum `content` length below 1,600 characters.
- **Normalize text before sending** (see segment math) and preview the segment count.
- **Throttle below 10 req/s per key**, shared across every worker using that key, with a queue and not ad-hoc sleeps.
- **De-duplicate** by (from, to, content-hash, time window) before calling send.
- **Stop on terminal codes** (`0206400`, `0201402`, `0204403`) and do not let the model "try again".
- **Treat inbound text as untrusted.** Customer messages and transcripts can carry prompt injection. Never let retrieved content authorize a send.
- **Keys out of reach of the model.** Tools run server-side and the LLM sees only tool results.

## What changed since v1.0.0 of this reference

- Base URL wording fixed: `https://api.quo.com` with a `/v1` prefix for v1, unprefixed paths plus the `Quo-Api-Version` header for 2026-03-30.
- `to` on `POST /v1/messages` is now `maxItems: 10` (group message), not 1.
- Added the `403 0204403` A2P 10DLC daily-cap error and `GET /organization` `subscriptionStatus`.
- Added Quo MCP (sends count as API-powered messages) and the 2026-03-30 retry endpoint.
- Message reads now include `media[]`. Sending MMS is still unsupported.
- International rates link is now `quo.com/rates`. The standalone "minimizing costs" page is gone (its tips are folded into the pricing page). Dropped its "most emojis count as two characters" claim, which the current page no longer makes.
- Removed the duplicated webhook and endpoint tables. They live in the messages and webhooks references.

## Sources (checked 2026-10-08)

- quo.com/docs: `mdx/pricing-support/pricing-overview`, `2026-03-30/ai-agents`, `mdx/guides/building-with-ai-llms`, `mdx/api-reference/authentication`, `2026-03-30/authentication`, `mdx/api-reference/send-your-first-message`, `2026-03-30/errors`, `2026-03-30/rate-limits`, `2026-03-30/messages/retry-a-failed-message`, `mdx/mcp/tools`, `changelog`, `llms.txt`.
- OpenAPI: `openphone-public-api-v1-prod.json` (`POST /v1/messages` body and responses, summary/transcript plan text) and `openphone-public-api-2026-03-30-prod.json` (`GET /organization`, message `status` and `media`, `POST /messages/{messageId}/retry`).
