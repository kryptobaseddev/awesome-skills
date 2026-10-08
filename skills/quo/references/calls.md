# Calls API (Quo, formerly OpenPhone)

Calls are **read-only** on the public REST API. You can list calls, fetch one call, and read its recordings, transcripts, AI summary and voicemail. You cannot place, end, transfer or modify a call through these endpoints. Two API surfaces serve calls on the same host, `https://api.quo.com`:

- **v1**: paths start with `/v1/`, no version header, envelope `{data, totalItems, nextPageToken}`.
- **2026-03-30**: paths have no prefix (`/calls`) and need the header `Quo-Api-Version: 2026-03-30` (requests without it get a `400`). Envelope is `{data, nextCursor}`.

Both surfaces authenticate with the **raw API key** in `Authorization` (`Authorization: YOUR_KEY`, no `Bearer ` prefix). One API key may make **10 requests per second** across both surfaces. Over that you get `429`. There is no daily quota.

## Contents

- [Which surface to use](#which-surface-to-use)
- [Shared enums and ID prefixes](#shared-enums-and-id-prefixes)
- [2026-03-30 endpoints](#2026-03-30-endpoints)
  - [GET /calls](#get-calls)
  - [GET /calls/{callId}](#get-callscallid)
  - [GET /calls/{callId}/recordings](#get-callscallidrecordings)
  - [GET /calls/{callId}/transcripts](#get-callscallidtranscripts)
  - [Summary and voicemail objects (include=)](#summary-and-voicemail-objects-include)
- [v1 endpoints](#v1-endpoints)
- [Async processing: poll or use webhooks](#async-processing-poll-or-use-webhooks)
- [Plan gating](#plan-gating)
- [Call analytics recipe](#call-analytics-recipe)
- [Migrating v1 to 2026-03-30](#migrating-v1-to-2026-03-30)
- [Errors](#errors)
- [Sources](#sources-checked-2026-10-08)

## Which surface to use

| Need | 2026-03-30 | v1 | Use |
|---|---|---|---|
| List all calls in the workspace, a date range, or by status or direction | `GET /calls`, every filter optional | Not possible. v1 needs one Quo number **and** exactly one participant | **2026-03-30** |
| Group calls and AI-agent calls | Included. `participants` lists every party, `actorId` can be an `SYU…` system actor | 1:1 only, `participants` at most 2 strings | **2026-03-30** |
| A call plus its summary and voicemail | One request: `?include=summary,voicemail` | Three requests (`/v1/calls/{id}`, `/v1/call-summaries/{id}`, `/v1/call-voicemails/{id}`) | **2026-03-30** |
| Recordings | `GET /calls/{callId}/recordings`, paginated | `GET /v1/call-recordings/{callId}` | **2026-03-30** |
| Transcripts | `GET /calls/{callId}/transcripts`, one per recorded segment | `GET /v1/call-transcripts/{id}`, one merged transcript | **2026-03-30**, or v1 if you want a single merged dialogue |
| Summary or voicemail on its own | No standalone endpoint. Use `include=` on the call | `/v1/call-summaries/{callId}`, `/v1/call-voicemails/{callId}` | 2026-03-30 `include=` |
| Place or control a call | Not in either API | Not in either API | Not available |

Use 2026-03-30 for any new calls integration. v1 has no call capability that 2026-03-30 lacks, apart from the standalone summary and voicemail routes, and `include=` covers those.

## Shared enums and ID prefixes

| Prefix | Entity | Notes |
|---|---|---|
| `AC` | Call | `^AC(.*)$`. Every call endpoint takes this ID |
| `PN` | Quo phone number | `phoneNumberId` |
| `US` | Quo user | |
| `SYU` | System actor, such as an AI agent (Sona) | 2026-03-30 only. Appears in `actorId`, `answeredBy`, `initiatedBy` |
| `CR` | Call recording | Pattern enforced in 2026-03-30. v1 does not enforce it |
| `VM` | Voicemail | |

Treat every ID as an opaque string. Read the prefix, but don't parse anything past it or assume a length.

**Call `status`** (same 13 values on both surfaces): `queued`, `initiated`, `ringing`, `in-progress`, `completed`, `busy`, `failed`, `no-answer`, `canceled`, `missed`, `answered`, `forwarded`, `abandoned`. Live calls go through `queued`/`initiated`/`ringing`/`in-progress`. All the other values are terminal.

**`direction`**: `incoming` | `outgoing`, relative to the Quo number.

**AI, routing and forwarding fields** (on the call object, both surfaces):

| Field | Meaning |
|---|---|
| `aiHandled` | `"ai-agent"` when an AI agent (Sona) answered the call, `null` when a human handled it. Filter on this field to separate AI calls from human calls. |
| `callRoute` | `"phone-number"` (direct dial) or `"phone-menu"` (routed through an IVR). `null` for outbound calls. |
| `forwardedFrom` / `forwardedTo` | `null` unless the call was forwarded. When forwarded, holds an E.164 number, a `PN…` or `US…` ID, `anonymous`/`blocked`/`restricted`, or a 3–6-digit service number such as `911`. |
| `answeredBy` | User or system actor that answered an incoming call. `null` for outgoing calls and for unanswered ones. |
| `initiatedBy` | User or system actor that placed an outgoing call. `null` for incoming calls. |

## 2026-03-30 endpoints

Every request below needs these headers:

```
Authorization: YOUR_API_KEY
Quo-Api-Version: 2026-03-30
```

### GET /calls

`operationId: listCalls`. Returns calls in the workspace, **newest first**. Every filter is optional, and group calls are included.

| Query param | Type | Notes |
|---|---|---|
| `phoneNumberId` | string `PN…` | Only calls on this Quo number. |
| `actorId` | string `US…` or `SYU…` | Only calls that belong to this user or system actor. Pass an AI agent's `SYU` ID to get its calls. |
| `participant` | E.164 string, or `participant[in]=` with a comma list | Matches the call's **own originating or receiving number** only. A third party who joined a group call shows up in the response's `participants` but does not match this filter. |
| `direction` | `incoming` \| `outgoing` | |
| `status` | one status enum value, or `status[in]=` with a comma list | e.g. `status[in]=missed,no-answer` |
| `createdAt[gte]` / `createdAt[lte]` | ISO 8601 date-time | Both bounds are **inclusive**. Only `gte` and `lte` exist on this endpoint (no `gt`/`lt`). |
| `include` | `summary`, `voicemail`, or `summary,voicemail` | Comma-separated, at most 2 values, no duplicates. Sections you leave out are absent from the response. `voicemail` is also absent on calls where no voicemail was left. |
| `limit` | integer 1–50, default 10 | Use `50` for bulk reads. |
| `after` | string | The `nextCursor` value from the previous page. Pass it back exactly as received. |

```bash
curl -G 'https://api.quo.com/calls' \
  -H "Authorization: $QUO_API_KEY" -H 'Quo-Api-Version: 2026-03-30' \
  --data-urlencode 'createdAt[gte]=2026-10-07T00:00:00Z' \
  --data-urlencode 'createdAt[lte]=2026-10-07T23:59:59Z' \
  --data-urlencode 'status[in]=missed,no-answer' \
  --data-urlencode 'include=summary,voicemail' \
  --data-urlencode 'limit=50'
```

Response `200`:

```json
{
  "data": [
    {
      "id": "AC123abc",
      "phoneNumberId": "PN123abc",
      "actorId": "US123abc",
      "direction": "incoming",
      "status": "completed",
      "participants": [
        { "phoneNumber": "+15555555555", "actorId": "US123abc" },
        { "phoneNumber": "+15555555555", "actorId": "US456def" },
        { "phoneNumber": "+15555555556", "actorId": null }
      ],
      "answeredAt": "2026-10-07T15:00:05Z",
      "answeredBy": "US123abc",
      "initiatedBy": null,
      "completedAt": "2026-10-07T15:04:05Z",
      "createdAt": "2026-10-07T15:00:00Z",
      "updatedAt": "2026-10-07T15:04:06Z",
      "callRoute": "phone-number",
      "duration": 240,
      "forwardedFrom": null,
      "forwardedTo": null,
      "aiHandled": null,
      "summary": {
        "status": "completed",
        "type": "human",
        "summary": ["Customer asked about invoice #1042."],
        "nextSteps": ["Email the corrected invoice."],
        "jobs": null,
        "title": null
      }
    }
  ],
  "nextCursor": "eyJsYXN0SWQiOiJVU211a09NaXBhIn0"
}
```

Call object fields (all are always present; nullable means the value can be `null`):

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `AC…` | no | |
| `phoneNumberId` | `PN…` | **yes** | `null` when the call is not attached to a Quo number. v1 never returns null here. |
| `actorId` | `US…` \| `SYU…` | no | The user or system actor associated with the call. Replaces v1 `userId`. |
| `direction`, `status` | enum | no | See [enums](#shared-enums-and-id-prefixes). |
| `participants` | array of `{phoneNumber, actorId}` | no | **Every party, including the Quo number.** Group calls can have more than 2 entries. The same number can appear more than once when several users joined on it, told apart by `actorId`. `phoneNumber` is E.164, `anonymous`/`blocked`/`restricted`, or a 3–8-digit short code. `actorId` is `null` for numbers outside the workspace. |
| `answeredAt`, `completedAt`, `updatedAt` | date-time | yes | |
| `createdAt` | date-time | no | |
| `answeredBy`, `initiatedBy` | `US…` \| `SYU…` | yes | |
| `callRoute`, `forwardedFrom`, `forwardedTo`, `aiHandled` | string | yes | See the table above. |
| `duration` | integer seconds | no | |
| `summary` | object | only with `include=summary` | [Summary object](#summary-and-voicemail-objects-include). |
| `voicemail` | object | only with `include=voicemail` and only when a voicemail was left | [Voicemail object](#summary-and-voicemail-objects-include). |

Gotchas:
- Keep requesting pages until `nextCursor` is `null`. There is no `totalItems`. Cursors are short-lived, so don't store them; to resume later, start again from a `createdAt` bound.
- Don't let a filter on `participant` stand in for "every call this person was on". It misses people added to a group call.
- `status=completed` alone misses most finished calls, because terminal states also include `answered`, `missed`, `no-answer`, `forwarded`, `abandoned`, `busy`, `canceled` and `failed`. Use `status[in]=` with a list, or leave the filter off and bucket the results client-side.
- Treat the response as open: new optional fields can appear without a version bump, so ignore keys you don't recognize. Tool and output schemas should not set `additionalProperties: false` on the response.

### GET /calls/{callId}

`operationId: getCallById`. Path `callId` (`AC…`, required). Query `include` works the same way as on the list endpoint. Returns `{ "data": {…call} }` with the same fields as above. Errors: `400`, `401`, `403`, `404` (also returned when the ID belongs to another workspace), `500`.

```bash
curl 'https://api.quo.com/calls/AC123abc?include=summary,voicemail' \
  -H "Authorization: $QUO_API_KEY" -H 'Quo-Api-Version: 2026-03-30'
```

Use this endpoint to re-check one call whose summary or voicemail was still `in-progress` when you listed it.

### GET /calls/{callId}/recordings

`operationId: getCallRecordings`. Path `callId` (`AC…`). Query `limit` (1–50, default 10) and `after`. Results are sorted by **`startTime` ascending (oldest segment first)**, the opposite of most list endpoints. A call that was paused and resumed has one recording per recorded segment.

```json
{
  "data": [
    {
      "id": "CRwRVK2qBq",
      "status": "completed",
      "startTime": "2026-10-07T15:00:06Z",
      "duration": 120,
      "url": "https://examplestorage.com/a643d4d3e1484fcc8b721627284eda5e.mp3",
      "type": "audio/mpeg"
    }
  ],
  "nextCursor": null
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `CR…` | no | |
| `status` | enum | no | `absent`, `completed`, `deleted`, `failed`, `in-progress`, `paused`, `processing`, `stopped`, `stopping` |
| `startTime` | date-time | no | Sort key. Can be `null` in v1. |
| `duration` | integer seconds | yes | `null` until the length is known. |
| `url` | uri-reference | yes | **Signed URL**, `null` until `status` is `completed`. |
| `type` | MIME string | yes | `null` whenever `url` is `null`. |

Gotchas: download the audio promptly and store the file, not the URL, because signed URLs expire. A call with no recording returns `data: []`. Use `limit=50` so that one request almost always returns every segment.

### GET /calls/{callId}/transcripts

`operationId: getCallTranscripts`. Path `callId` (`AC…`). Query `limit` (1–50, default 10) and `after`. **One transcript per recording segment**, sorted by `startTime` ascending.

```json
{
  "data": [
    {
      "recordingId": "CRwRVK2qBq",
      "status": "completed",
      "startTime": "2026-10-07T15:00:06Z",
      "createdAt": "2026-10-07T15:05:10Z",
      "duration": 118.4,
      "dialogue": [
        { "content": "Hi, this is Dana from Acme.", "start": 0.42, "end": 2.9,
          "identifier": "+15555555555", "actorId": "US123abc" },
        { "content": "Hey, I had a question about my invoice.", "start": 3.1, "end": 6.0,
          "identifier": "+15555555556", "actorId": null }
      ]
    }
  ],
  "nextCursor": null
}
```

| Field | Type | Notes |
|---|---|---|
| `recordingId` | `CR…` | Joins to the recording with the same ID. |
| `status` | `absent` \| `in-progress` \| `completed` \| `failed` | `absent` means a transcript will never be produced (for example, transcription is off or the plan is not eligible). `dialogue` is only populated when the status is `completed`. |
| `startTime`, `createdAt` | date-time | `startTime` is when the source recording started. `createdAt` is when the transcript was produced. |
| `duration` | number (float seconds) | |
| `dialogue[]` | array | `content` (string), `start` and `end` (float seconds **from the start of this segment's recording**, not from the start of the call), `identifier` (speaker phone number, nullable), `actorId` (`US…`/`SYU…`, `null` for external speakers or when the speaker is unknown). |

Gotcha: to build one timeline for the whole call, offset each segment by its `startTime` relative to the first segment. v1 returns a single transcript with offsets measured from the start of the call.

### Summary and voicemail objects (include=)

2026-03-30 has no `/call-summaries` or `/call-voicemails` route. Ask for these sections inline with `include=` on `GET /calls` or `GET /calls/{callId}`.

**`summary`** (present whenever `include=summary` is requested):

| Field | Type | Notes |
|---|---|---|
| `status` | `absent` \| `in-progress` \| `completed` \| `failed` | `absent` means a summary will never be generated. The content fields are populated only when the status is `completed`. |
| `type` | `human` \| `agent` \| null | `null` until a summary exists. `agent` means the call was handled by an AI agent. |
| `summary` | string[] \| null | Key points, one string per bullet. |
| `nextSteps` | string[] \| null | Set only for `human` summaries. |
| `jobs` | array \| null | Set only for `agent` summaries. Each job is `{icon, name, result: {data: [{name, value}]}}`, where `value` is a string, number or boolean. These are structured Q&A or task results that the AI agent collected. |
| `title` | string \| null | Set only for `agent` summaries, e.g. `"Pricing enquiry"`. |

**`voicemail`** (present only when a voicemail was left):

| Field | Type | Notes |
|---|---|---|
| `id` | `VM…` | |
| `status` | `completed` \| `in-progress` | No `failed` or `absent` values exist for voicemails. |
| `duration` | integer \| null | Usually known before processing finishes. |
| `recordingUrl` | uri \| null | `null` until the status is `completed`. |
| `transcript` | string \| null | `null` until the status is `completed`, and stays `null` when transcription is turned off for the number that took the call. |

## v1 endpoints

No version header. Error bodies carry a numeric-string `code` (listed below). Prefer 2026-03-30 for new code; this section is for existing integrations.

| Endpoint | Path params / required query | `data` shape | Error code prefix |
|---|---|---|---|
| `GET /v1/calls` | `phoneNumberId`, `participants`, `maxResults` all **required** | array | `0101…`/`0100…` |
| `GET /v1/calls/{callId}` | `callId` | call object | `0101…`/`0100…` |
| `GET /v1/call-recordings/{callId}` | `callId` | array of recordings, oldest first, not paginated | `0900…` |
| `GET /v1/call-summaries/{callId}` | `callId` | summary | `0500…` |
| `GET /v1/call-transcripts/{id}` | **`id`** (an `AC…` call ID; this route names the param differently from the others) | transcript | `0600…` |
| `GET /v1/call-voicemails/{callId}` | `callId` | voicemail | `1200…` |

**`GET /v1/calls` query:**

| Param | Type | Notes |
|---|---|---|
| `phoneNumberId` | `PN…`, required | |
| `participants` | array, required, `maxItems: 1` | The other party's E.164 number, excluding your Quo number. Send it **without brackets**: `participants=%2B15555555555`. More than one value returns `400 Too Many Participants` (`0101400`). An empty value returns `400`. |
| `maxResults` | integer 1–100, required (default 10) | Always send it. |
| `userId` | `US…`, optional | Limits results to calls this user can access. The spec says it defaults to the workspace owner; a 2024 changelog fix says it defaults to the phone number owner. Pass it explicitly. |
| `createdAfter` / `createdBefore` | date-time | |
| `since` | date-time | **Deprecated.** It behaves like `createdBefore`, so don't use it. |
| `pageToken` | string | The `nextPageToken` from the previous page. |

The v1 response is `{data, totalItems, nextPageToken}`. `totalItems` is documented as inaccurate, so keep paging until `nextPageToken` is `null`. A `403 Not Phone Number User` (`0101403`) means the user (supplied or default) is not a member of that number.

**v1 call object:** `id`, `phoneNumberId` (never null), `userId` (`US…`), `direction`, `status`, `participants` (**array of E.164 strings, including the Quo number, at most 2**), `answeredAt`, `answeredBy`, `initiatedBy`, `completedAt`, `createdAt`, `updatedAt`, `callRoute`, `duration`, `forwardedFrom` (E.164 or `US…`), `forwardedTo` (E.164, `PN…` or `US…`), `aiHandled`.

**v1 recordings:** `{id, status, startTime, duration, url, type}`. Same status enum as 2026-03-30, but here `status` and `startTime` can also be `null`.

**v1 summary** (`/v1/call-summaries/{callId}`): `{callId, status, summary: string[]|null, nextSteps: string[]|null, jobs?: [...]|null}`. It has no `type` or `title` field. `status` is `absent`, `in-progress`, `completed` or `failed`. Business and Scale plans only.

**v1 transcript** (`/v1/call-transcripts/{id}`): `{callId, createdAt, duration, status, dialogue: [...]|null}`. Each dialogue item is `{content, start, end, identifier, userId}`, where `start`/`end` are measured from the **beginning of the call** and `userId` is `null` for external speakers. This is a single object, not a per-segment list. Business and Scale plans only.

**v1 voicemail** (`/v1/call-voicemails/{callId}`): `{id, status: completed|in-progress, duration, transcript, recordingUrl}`. While processing, `duration`, `transcript` and `recordingUrl` are `null`.

```bash
curl 'https://api.quo.com/v1/calls?phoneNumberId=PN123abc&participants=%2B15555555555&maxResults=50' \
  -H "Authorization: $QUO_API_KEY"
```

## Async processing: poll or use webhooks

Recordings, transcripts, summaries and voicemails all finish **after** the call ends, often minutes later, and a summary can take longer still. Transcript and summary complete independently and in either order.

| Artifact | Not ready yet | Ready | Will never exist |
|---|---|---|---|
| Recording | `processing`, `in-progress`, `stopping`, `paused`; `url: null` | `completed` | `absent`, `deleted`, `failed` |
| Transcript | `in-progress` | `completed` | `absent`, `failed` |
| Summary | `in-progress` | `completed` | `absent`, `failed` |
| Voicemail | `in-progress` (no URL or transcript yet) | `completed` | no `voicemail` key in the response |

**Prefer webhooks to polling.** Subscribe to these call events (2026-03-30 `POST /webhooks`; see the webhooks reference):

| Event | Use |
|---|---|
| `call.completed` | Call ended. Carries the final `status`, `duration` and `hasVoicemail`. **Its status enum differs from the REST one**: `answered`, `unanswered`, `failed`, `forwarded`, `abandoned`, `ai-handled`, `unknown`. |
| `call.recording.completed` | Recording ready. Can arrive after `call.completed`. |
| `call.transcript.completed` | Transcript ready. |
| `call.summary.completed` | Summary ready. Read `resource.processingStatus` and don't infer readiness from when the event arrived. The payload already includes `summary`, `nextSteps`, `jobs` and `handledByAiAgent`. |
| `call.voicemail.completed` | Voicemail processed. Correlate it to the call with `resource.callId`. |
| `call.ringing`, `call.answered`, `call.missed`, `call.forwarded`, `call.menu.selected` | Live lifecycle and IVR events. |

When you have to poll, poll each call individually with a backoff schedule (for example 30 s, 1 min, 2 min, 5 min, 10 min) and stop once the status is `completed`, `absent` or `failed`. Never write a tight loop: every poll counts against the 10 req/s budget that the rest of the integration shares.

## Plan gating

- **Call summaries and call transcripts:** the v1 docs say they are available on **Business and Scale plans only**. The 2026-03-30 spec doesn't repeat the restriction, but the feature is the same, so expect the same gate. On a plan that isn't eligible, or a number with transcription turned off, expect `status: "absent"` (or a `403` on the v1 standalone routes). Handle both, and treat `absent` as a normal state rather than an error.
- **AI agent (Sona) calls:** these have `aiHandled: "ai-agent"`, a `SYU…` actor, and an `agent` summary that includes `jobs` and `title`.
- Recordings depend on the workspace's call-recording settings, not on an API flag. Expect an empty `data` array when nothing was recorded.

## Call analytics recipe

Goal: get every call for one day, with summaries and voicemails, using as few requests as possible and staying under 10 req/s.

1. **Choose the day in UTC.** The API works only in UTC. For a local day, convert local midnight to UTC (e.g. `America/New_York` 2026-10-07 is `2026-10-07T04:00:00Z` to `2026-10-08T03:59:59Z`). Both bounds are inclusive, so set `lte` to one second before the next day's start, and dedupe by `id` if you're stitching days together.
2. **List the calls, bringing summaries and voicemails inline:** `GET /calls?createdAt[gte]=…&createdAt[lte]=…&include=summary,voicemail&limit=50`, then follow `after` until `nextCursor` is `null`. This costs **⌈calls/50⌉ requests in total**: 400 calls is 8 requests, not the 1,200 that v1 needs (call, summary and voicemail for each call). Add `phoneNumberId`, `actorId`, `direction` or `status[in]` to narrow the set on the server.
3. **Compute metrics client-side** from the list: counts by `status`/`direction`, answer rate (`answeredAt != null`), missed calls (`status in [missed, no-answer, abandoned]`), AI share (`aiHandled == "ai-agent"`), forwarded calls, total and average `duration`, per-agent totals by `answeredBy`/`initiatedBy`, IVR share (`callRoute == "phone-menu"`).
4. **Fetch transcripts only when you need them**: one `GET /calls/{id}/transcripts?limit=50` per call, and only for calls with `answeredAt != null` and `duration > 0`. Skip this step if `summary.summary` is enough.
5. **Re-check stragglers later.** For calls where `summary.status == "in-progress"` or `voicemail.status == "in-progress"`, either wait for the `call.summary.completed` / `call.voicemail.completed` webhooks or re-fetch with `GET /calls/{id}?include=summary,voicemail` on a backoff. Running the report for *yesterday* rather than today avoids most of these.
6. **Throttle on the client.** Allow about 8 requests per second per key, which leaves headroom for other traffic on the same key. Process requests from a single shared queue so that parallel workers are covered by the one limit. On `429` or `5xx`, back off exponentially with jitter. Never retry a `400`.

```ts
const BASE = "https://api.quo.com";
const H = { Authorization: process.env.QUO_API_KEY!, "Quo-Api-Version": "2026-03-30" };

// Minimal shared throttle: at most 8 requests per rolling second.
const stamps: number[] = [];
async function throttle() {
  for (;;) {
    const now = Date.now();
    while (stamps.length && now - stamps[0] >= 1000) stamps.shift();
    if (stamps.length < 8) { stamps.push(now); return; }
    await new Promise((r) => setTimeout(r, 1000 - (now - stamps[0])));
  }
}

async function quoGet(path: string, params: Record<string, string> = {}, attempt = 0): Promise<any> {
  await throttle();
  const url = new URL(path, BASE);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url, { headers: H });
  if ((res.status === 429 || res.status >= 500) && attempt < 5) {
    await new Promise((r) => setTimeout(r, 2 ** attempt * 500 + Math.random() * 250));
    return quoGet(path, params, attempt + 1);
  }
  if (!res.ok) throw new Error(`${res.status} ${JSON.stringify(await res.json())}`);
  return res.json();
}

export async function callsForDay(gteIso: string, lteIso: string) {
  const calls: any[] = [];
  let after: string | null = null;
  do {
    const page = await quoGet("/calls", {
      "createdAt[gte]": gteIso,
      "createdAt[lte]": lteIso,
      include: "summary,voicemail",
      limit: "50",
      ...(after ? { after } : {}),
    });
    calls.push(...page.data);
    after = page.nextCursor;
  } while (after);
  const pending = calls.filter(
    (c) => c.summary?.status === "in-progress" || c.voicemail?.status === "in-progress",
  );
  return { calls, pending }; // re-check `pending` later or wait for webhooks
}
```

For LLM tool calls (for example with TanStack AI), expose **one** `list_calls` tool with typed optional filters (`phoneNumberId`, `actorId`, `participant`, `direction`, `status` as an enum array, `createdAfter`/`createdBefore`, `includeSummary`) and have the server translate them into `createdAt[gte]`, `status[in]` and `include=`. Pass through a bounded `limit` and an opaque cursor. Keep the throttle in the server-side tool executor, not in the prompt.

## Migrating v1 to 2026-03-30

| v1 | 2026-03-30 |
|---|---|
| `GET /v1/calls?phoneNumberId&participants&maxResults` (all required) | `GET /calls`, all filters optional |
| `participants=+1…` (one other party) | `participant=+1…` or `participant[in]=a,b` |
| `userId` filter | `actorId` filter (`US…` or `SYU…`) |
| `createdAfter` / `createdBefore` (exclusive wording) | `createdAt[gte]` / `createdAt[lte]` (inclusive) |
| `maxResults` 1–100, `pageToken` / `nextPageToken`, `totalItems` | `limit` 1–50, `after` / `nextCursor`, no total |
| Call `userId` | Call `actorId` |
| Call `participants: ["+1…", "+1…"]` | `participants: [{phoneNumber, actorId}]`, every party including group calls |
| `phoneNumberId` always set | `phoneNumberId` nullable |
| `/v1/call-summaries/{callId}` | `include=summary` (adds `type`, `title`) |
| `/v1/call-voicemails/{callId}` | `include=voicemail` (left out when there is no voicemail) |
| `/v1/call-recordings/{callId}` (unpaginated) | `/calls/{callId}/recordings` (paginated, `CR` IDs, `startTime` non-null) |
| `/v1/call-transcripts/{id}`: one transcript, offsets from call start, `userId` | `/calls/{callId}/transcripts`: one per segment with `recordingId`, offsets from segment start, `actorId`, `dialogue` never null |
| Error `{message, code, status, docs, title, trace?, errors?}` | Error `{title, message, docs, trace?, errors?[{path, message, value, schema}]}` with no `code` |
| No header | `Quo-Api-Version: 2026-03-30` required |

## Errors

2026-03-30 example:

```json
{
  "message": "The input was invalid",
  "docs": "https://quo.com/docs",
  "title": "Bad Request",
  "errors": [{ "path": "/callId", "message": "Expected string to match '^AC(.*)$'",
               "value": "abc123", "schema": { "type": "TemplateLiteral", "pattern": "^AC(.*)$" } }]
}
```

| Status | Meaning | Retry? |
|---|---|---|
| `400` | Bad parameter, or a missing `Quo-Api-Version` header. `errors[].path` names the field. | No |
| `401` | Bad or missing key, or a `Bearer ` prefix. | No |
| `403` | The key is valid, but permissions, a workspace setting or the plan don't allow the action. | Not until something changes |
| `404` | The call doesn't exist or belongs to another workspace. | No |
| `429` | More than 10 req/s on this key. | Yes, with backoff and jitter |
| `500` | Server-side failure. Log the `trace`. | Yes, with backoff |

## Sources (checked 2026-10-08)

- OpenAPI specs: `openphone-public-api-2026-03-30-prod.json` (`/calls`, `/calls/{callId}`, `/calls/{callId}/recordings`, `/calls/{callId}/transcripts`) and `openphone-public-api-v1-prod.json` (`/v1/calls`, `/v1/calls/{callId}`, `/v1/call-recordings/{callId}`, `/v1/call-summaries/{callId}`, `/v1/call-transcripts/{id}`, `/v1/call-voicemails/{callId}`)
- quo.com/docs/2026-03-30: calls/list-calls, calls/get-a-call-by-id, calls/list-recordings-for-a-call, calls/list-transcripts-for-a-call, requests, errors, rate-limits, webhooks-event-payloads
- quo.com/docs/mdx/api-reference/calls: list-calls, get-a-call-by-id, get-recordings-for-a-call, get-a-summary-for-a-call, get-a-transcription-for-a-call, get-a-voicemail-for-a-call
- quo.com/docs changelog (2026-09-29 calls release; v1 `since` deprecation and `userId`-default fix)
