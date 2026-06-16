## Calls API (Quo / formerly OpenPhone)

All call endpoints live under the v1 REST API. Six read-only (`GET`) endpoints are documented for this domain: list calls, get a call by ID, get recordings, get summary, get transcription, and get voicemail. There are no `POST`/`PUT`/`DELETE` operations for calls in the public API — you cannot place or mutate calls via this API, only read call data.

> Source pages (clean markdown twins):
> - https://www.quo.com/docs/mdx/api-reference/calls/list-calls.md
> - https://www.quo.com/docs/mdx/api-reference/calls/get-a-call-by-id.md
> - https://www.quo.com/docs/mdx/api-reference/calls/get-recordings-for-a-call.md
> - https://www.quo.com/docs/mdx/api-reference/calls/get-a-summary-for-a-call.md
> - https://www.quo.com/docs/mdx/api-reference/calls/get-a-transcription-for-a-call.md
> - https://www.quo.com/docs/mdx/api-reference/calls/get-a-voicemail-for-a-call.md

### Authentication & Base URL (read this first)

- **Auth header is a RAW API key — NOT a Bearer token.** Every endpoint's embedded OpenAPI declares `securitySchemes.apiKey` as `type: apiKey`, `in: header`, `name: Authorization`. So you send `Authorization: <your-api-key>` with the key value directly. Do **not** prefix it with `Bearer `.
- **Host note:** This product rebranded OpenPhone → Quo. The canonical host is `https://api.quo.com/v1` (the OpenAPI `servers` block on every docs page reads `url: https://api.quo.com`; paths are `/v1/...`). `https://api.openphone.com/v1` is a live legacy alias targeting the same v1 API. The curl examples below use `https://api.quo.com/v1`; keep the host in one configurable constant and confirm which host your key is provisioned against before shipping.
- All timestamps are ISO 8601 (e.g. `2022-01-01T00:00:00Z`).
- All error responses share the shape: `{ message, code, status, docs, title, trace?, errors?[] }` where `docs` is the constant `https://quo.com/docs` and `code` is a per-endpoint string like `"0101400"`.

### ID prefix conventions (verbatim from the `pattern` regexes)

| Entity | Prefix pattern | Example |
|---|---|---|
| Call | `^AC(.*)$` | `ACsampleActivity01` |
| Quo phone number | `^PN(.*)$` | `PN123abc` |
| Quo user | `^US(.*)$` | `US123abc` |
| Call recording | (none enforced) | `CRwRVK2qBq` |
| Voicemail | `^VM(.*)$` | `VMsampleVoicemail01` |

---

### List calls

```
GET https://api.quo.com/v1/calls
```

Fetch a paginated list of calls associated with a specific Quo number and another number. (`operationId: listCalls_v1`)

| name | in | type | required | notes |
|---|---|---|---|---|
| `phoneNumberId` | query | string (`^PN(.*)$`) | **yes** | The unique identifier of the Quo number associated with the call. E.g. `PN123abc`. |
| `participants` | query | array of string | **yes** | Phone numbers of participants involved in the call, **excluding your Quo number**. E.164 with country code. `maxItems: 1` — **currently limited to one-to-one (1:1) conversations only.** E.g. `+15555555555`. |
| `maxResults` | query | integer | **yes** | Max results per page. `default: 10`, `minimum: 1`, `maximum: 100`. |
| `userId` | query | string (`^US(.*)$`) | no | The Quo user who placed or received the call. **Defaults to the workspace owner** if omitted. E.g. `US123abc`. |
| `createdAfter` | query | string (date-time) | no | Only calls created after this ISO 8601 instant. |
| `createdBefore` | query | string (date-time) | no | Only calls created before this ISO 8601 instant. |
| `since` | query | string (date-time) | no | **DEPRECATED** — use `createdAfter`/`createdBefore` instead. Note: `since` incorrectly behaves as `createdBefore` and will be removed in an upcoming release. |
| `pageToken` | query | string | no | Opaque cursor for the next page. Pass back the `nextPageToken` from the previous response. |

Request body: _none (GET)._

Response (`200`):

```json
{
  "data": [
    {
      "answeredAt": "2022-01-01T00:00:00Z",
      "answeredBy": "USlHhXmRMz",
      "initiatedBy": null,
      "direction": "incoming",
      "status": "completed",
      "completedAt": "2022-01-01T00:00:00Z",
      "createdAt": "2022-01-01T00:00:00Z",
      "callRoute": "phone-number",
      "duration": 60,
      "forwardedFrom": null,
      "forwardedTo": null,
      "aiHandled": null,
      "id": "AC123abc",
      "phoneNumberId": "PN123abc",
      "participants": ["+15555555555"],
      "updatedAt": "2022-01-01T00:00:00Z",
      "userId": "US123abc"
    }
  ],
  "totalItems": 1,
  "nextPageToken": null
}
```

Call object field reference (all fields are in the `required` list of the response schema; `anyOf … null` marks nullable fields):

| field | type | nullable | notes |
|---|---|---|---|
| `answeredAt` | string (date-time) | yes | When the call was answered. Null if not answered. |
| `answeredBy` | string (`US…`) | yes | Quo user who answered the incoming call. Null for outgoing or unanswered incoming. |
| `initiatedBy` | string (`US…`) | yes | Quo user who initiated the outgoing call. Null for incoming. |
| `direction` | enum string | no | `incoming` \| `outgoing`. Relative to the Quo number. |
| `status` | enum string | no | One of: `queued`, `initiated`, `ringing`, `in-progress`, `completed`, `busy`, `failed`, `no-answer`, `canceled`, `missed`, `answered`, `forwarded`, `abandoned`. |
| `completedAt` | string (date-time) | yes | When the call ended. Null if ongoing/not completed. |
| `createdAt` | string (date-time) | no | When the call record was created. |
| `callRoute` | string | yes | `phone-number` (direct dial) or `phone-menu` (routed via menu). **Null for outbound calls.** |
| `duration` | integer | no | Total call duration in **seconds**. |
| `forwardedFrom` | string (E.164 `^\+[1-9]\d{1,14}$` or `US…`) | yes | Phone number or Quo user ID the call was forwarded from. Null if not forwarded. |
| `forwardedTo` | string (E.164 or `US…`) | yes | Phone number or Quo user ID the call was forwarded to. Null if not forwarded. |
| `aiHandled` | string | yes | Type of AI that answered: `ai-agent` for AI responses, or **null for human responses**. |
| `id` | string (`AC…`) | no | Unique identifier of the call. |
| `phoneNumberId` | string (`PN…`) | no | Quo number associated with the call. |
| `participants` | array of E.164 string | no | `maxItems: 2`. Phone numbers in E.164. |
| `updatedAt` | string (date-time) | yes | When the record was last updated. Null if never updated. |
| `userId` | string (`US…`) | no | Quo user account associated with the call. |

Top-level envelope fields: `data` (array), `totalItems` (integer), `nextPageToken` (string or null).

**Gotchas — List calls**
- `phoneNumberId`, `participants`, AND `maxResults` are all `required`. Omitting any will fail validation. (`maxResults` has a default of 10 in the schema but is still flagged required — always send it.)
- `participants` is an array capped at **1 item** (`maxItems: 1`). Multi-party / group calls are not listable here — only 1:1. Supplying more than one triggers HTTP `400 Too Many Participants` (`code: "0101400"`).
- `participants` must **exclude your own Quo number** and must be E.164 (`+` and country code).
- `totalItems` is documented as inaccurate: "⚠️ `totalItems` is not accurately returning the total number of items that can be paginated. We are working on fixing this issue." **Do not** rely on it for paging math — paginate until `nextPageToken` is `null`.
- `since` is deprecated and buggy (behaves like `createdBefore`). Use `createdAfter`/`createdBefore`.
- `403 Not Phone Number User` (`code: "0101403"`) is returned if the (default or supplied) user is not a member of that phone number.

Example:

```bash
curl --request GET \
  --url 'https://api.quo.com/v1/calls?phoneNumberId=PN123abc&participants[]=%2B15555555555&maxResults=10' \
  --header 'Authorization: YOUR_RAW_API_KEY'
```

---

### Get a call by ID

```
GET https://api.quo.com/v1/calls/{callId}
```

Get a single call by its unique identifier. (`operationId: getCallById_v1`)

| name | in | type | required | notes |
|---|---|---|---|---|
| `callId` | path | string (`^AC(.*)$`) | **yes** | Unique identifier of the call. E.g. `ACsampleActivity01`. |

Request body: _none (GET)._

Response (`200`) — same call object as List calls, wrapped in a single `data` object (not an array):

```json
{
  "data": {
    "answeredAt": "2022-01-01T00:00:00Z",
    "answeredBy": "USlHhXmRMz",
    "initiatedBy": null,
    "direction": "incoming",
    "status": "completed",
    "completedAt": "2022-01-01T00:00:00Z",
    "createdAt": "2022-01-01T00:00:00Z",
    "callRoute": "phone-number",
    "duration": 60,
    "forwardedFrom": null,
    "forwardedTo": null,
    "aiHandled": null,
    "id": "AC123abc",
    "phoneNumberId": "PN123abc",
    "participants": ["+15555555555"],
    "updatedAt": "2022-01-01T00:00:00Z",
    "userId": "US123abc"
  }
}
```

**Gotchas — Get a call by ID**
- `data` here is a single object, whereas List calls returns `data` as an array. Handle both shapes.
- Same field set and nullability rules as the List calls call object (see that table).
- Error codes for this endpoint: `400 Too Many Participants` (`0101400`), `401 Unauthorized` (`0100401`), `403 Not Phone Number User` (`0101403`), `404 Not Found` (`0100404`), `500 Unknown` (`0101500`).

Example:

```bash
curl --request GET \
  --url 'https://api.quo.com/v1/calls/ACsampleActivity01' \
  --header 'Authorization: YOUR_RAW_API_KEY'
```

---

### Get recordings for a call

```
GET https://api.quo.com/v1/call-recordings/{callId}
```

Retrieve a list of recordings associated with a specific call. Results are sorted chronologically, **oldest recording segment first**. (`operationId: getCallRecordings_v1`)

| name | in | type | required | notes |
|---|---|---|---|---|
| `callId` | path | string (`^AC(.*)$`) | **yes** | The call for which recordings are retrieved. E.g. `ACsampleActivity02`. |

Request body: _none (GET)._

Response (`200`) — `data` is an **array** of recording segments:

```json
{
  "data": [
    {
      "duration": 60,
      "id": "CRwRVK2qBq",
      "startTime": "2022-01-01T00:00:00Z",
      "status": "completed",
      "type": "audio/mpeg",
      "url": "https://examplestorage.com/a643d4d3e1484fcc8b721627284eda5e.mp3"
    }
  ]
}
```

Recording object fields (all `required`; each is nullable via `anyOf … null` except `id`):

| field | type | nullable | notes |
|---|---|---|---|
| `duration` | integer | yes | Recording length in seconds. Null if not completed or unknown. |
| `id` | string | no | Unique recording ID (e.g. `CRwRVK2qBq`). No enforced prefix pattern. |
| `startTime` | string (date-time) | yes | When the recording began. Null if not started/unknown. |
| `status` | enum string | yes | One of: `absent`, `completed`, `deleted`, `failed`, `in-progress`, `paused`, `processing`, `stopped`, `stopping`. |
| `type` | string (MIME) | yes | File type, e.g. `audio/mpeg`. Null if unspecified/unknown. |
| `url` | string (uri-reference) | yes | Download/access URL for the recording audio. **Null if not available or recording inaccessible.** |

**Gotchas — Recordings**
- `data` is a **list** — a single call can have multiple recording segments (e.g. recording paused/resumed). Iterate; segments are oldest-first.
- The `url` is nullable and the `status` can be `processing`/`in-progress`/`absent`/`failed` — guard against `url: null` and statuses other than `completed` before downloading.
- The download `url` points at external storage (e.g. `examplestorage.com`); such signed URLs are typically time-limited — fetch promptly, don't cache the URL long-term.
- A call with no recording returns `data: []` (or recording objects with `status: "absent"`), not a 404.
- Error codes: `400` (`0900400`), `401` (`0900401`), `403` (`0900403`), `404` (`0900404`), `500` (`0901500`).

Example:

```bash
curl --request GET \
  --url 'https://api.quo.com/v1/call-recordings/ACsampleActivity02' \
  --header 'Authorization: YOUR_RAW_API_KEY'
```

---

### Get a summary for a call

```
GET https://api.quo.com/v1/call-summaries/{callId}
```

Retrieve a detailed summary of a specific call. Supports summaries for both regular calls and calls handled by Sona. **Call summaries are only available on business and scale plans.** (`operationId: getCallSummary_v1`)

| name | in | type | required | notes |
|---|---|---|---|---|
| `callId` | path | string (`^AC(.*)$`) | **yes** | The call associated with the summary. E.g. `ACsampleActivity02`. |

Request body: _none (GET)._

Response (`200`) — `data` is a single object:

```json
{
  "data": {
    "callId": "ACea724hac8c30465bcbcff0b76e4c1c7b",
    "nextSteps": ["Bring an umbrella."],
    "status": "completed",
    "summary": ["You talked about the weather."],
    "jobs": [
      {
        "icon": "string",
        "name": "string",
        "result": {
          "data": [
            { "name": "string", "value": "string" }
          ]
        }
      }
    ]
  }
}
```

Summary object fields:

| field | type | required | nullable | notes |
|---|---|---|---|---|
| `callId` | string | yes | no | The call this summary belongs to. |
| `nextSteps` | array of string | yes | yes | Suggested follow-up actions, e.g. `"Bring an umbrella."`. Null if none/unavailable. |
| `status` | enum string | yes | no | One of: `absent`, `in-progress`, `completed`, `failed`. |
| `summary` | array of string | yes | yes | Summary bullet lines, e.g. `"You talked about the weather."`. Null if unavailable. |
| `jobs` | array of object | no | yes | Optional structured "jobs" (Sona/AI-extracted fields). Each job: `icon` (string), `name` (string), `result.data[]` where each item is `{ name: string, value: string\|number\|boolean\|null }`. |

**Gotchas — Summary**
- **Plan-gated: business and scale plans only.** Lower plans will not have summaries (expect `403 Forbidden` / `code: "0500403"` or `status: "absent"`).
- AI processing is asynchronous: `status` may be `in-progress` or `absent` and `summary`/`nextSteps` may be `null` right after a call. Poll until `status: "completed"`.
- `summary` and `nextSteps` are **arrays of strings**, not single strings — render each element as a line/bullet.
- `jobs` is optional and may be absent entirely; `jobs[].result.data[].value` can be string, number, boolean, or null — type-check before use.
- Error codes: `400` (`0500400`), `401` (`0500401`), `403` (`0500403`), `404` (`0500404`), `500` (`0501500`).

Example:

```bash
curl --request GET \
  --url 'https://api.quo.com/v1/call-summaries/ACsampleActivity02' \
  --header 'Authorization: YOUR_RAW_API_KEY'
```

---

### Get a transcription for a call

```
GET https://api.quo.com/v1/call-transcripts/{id}
```

Retrieve a detailed transcript of a specific call. Supports transcripts for both regular calls and calls handled by Sona. **Call transcripts are only available on business and scale plans.** (`operationId: getCallTranscript_v1`)

| name | in | type | required | notes |
|---|---|---|---|---|
| `id` | path | string (`^AC(.*)$`) | **yes** | Unique identifier of the call associated with this transcript. Note: the path param is named `id` (not `callId`). E.g. `ACsampleActivity01`. |

Request body: _none (GET)._

Response (`200`) — `data` is a single object:

```json
{
  "data": {
    "callId": "ACea724hac8c30465bcbcff0b76e4c1c7b",
    "createdAt": "2022-01-01T00:00:00Z",
    "dialogue": [
      {
        "content": "Hello, world!",
        "start": 5.123456,
        "end": 10.123456,
        "identifier": "+19876543210",
        "userId": "US123abc"
      }
    ],
    "duration": 100,
    "status": "completed"
  }
}
```

Transcript object fields (all `required`):

| field | type | nullable | notes |
|---|---|---|---|
| `callId` | string | no | The call this transcript belongs to. |
| `createdAt` | string (date-time) | no | When the transcription was created. |
| `dialogue` | array of object | yes | The dialogue segments (see below). The whole array is nullable. |
| `duration` | number | no | Total transcribed call duration in seconds. |
| `status` | enum string | no | One of: `absent`, `in-progress`, `completed`, `failed`. |

`dialogue[]` segment fields (all `required` within a segment):

| field | type | nullable | notes |
|---|---|---|---|
| `content` | string | no | Transcribed text of the segment, e.g. `"Hello, world!"`. |
| `start` | number | no | Segment start time in seconds, relative to call start (e.g. `5.123456`). |
| `end` | number | no | Segment end time in seconds, relative to call start (e.g. `10.123456`). |
| `identifier` | string | yes | Phone number of the participant who spoke (E.164). Null if not available. |
| `userId` | string (`US…`) | yes | Quo user who spoke. **Null for external participants** or if user identification is unavailable. |

**Gotchas — Transcription**
- **Path param is named `id`, not `callId`** — different from the recordings/summary/voicemail endpoints (which use `callId`). The value is still the `AC…` call ID.
- **Plan-gated: business and scale plans only.** Otherwise expect `403 Forbidden` (`code: "0600403"`) or `status: "absent"`.
- Asynchronous: `dialogue` may be `null` and `status` may be `in-progress`/`absent` until processing finishes. Poll until `status: "completed"`.
- `start`/`end`/`duration` are floating-point seconds (`number`, not integer). `identifier` and `userId` per-segment are nullable; expect nulls for the external caller's segments where the user isn't a Quo user.
- Error codes: `400` (`0600400`), `401` (`0600401`), `403` (`0600403`), `404` (`0600404`), `500` (`0601500`).

Example:

```bash
curl --request GET \
  --url 'https://api.quo.com/v1/call-transcripts/ACsampleActivity01' \
  --header 'Authorization: YOUR_RAW_API_KEY'
```

---

### Get a voicemail for a call

```
GET https://api.quo.com/v1/call-voicemails/{callId}
```

Retrieve a voicemail associated with a specific call. Returns **null data fields while the voicemail is processing**; returns completed data fields once finished processing. (`operationId: getCallVoicemails_v1`)

| name | in | type | required | notes |
|---|---|---|---|---|
| `callId` | path | string (`^AC(.*)$`) | **yes** | The call for which a voicemail is retrieved. E.g. `ACsampleActivity02`. |

Request body: _none (GET)._

Response (`200`) — `data` is a single object:

```json
{
  "data": {
    "duration": 60,
    "id": "VMsampleVoicemail01",
    "transcript": "Hello, this is a voicemail from John Doe.",
    "recordingUrl": "https://examplestorage.com/a643d4d3e1484fcc8b721627284eda5e.mp3",
    "status": "completed"
  }
}
```

Voicemail object fields (all `required`):

| field | type | nullable | notes |
|---|---|---|---|
| `duration` | integer | yes | Voicemail length in seconds. Null if not completed or unknown. |
| `id` | string (`^VM(.*)$`) | no | Unique voicemail ID, e.g. `VMsampleVoicemail01`. |
| `transcript` | string | yes | Voicemail transcript text. **Null if not completed or transcript unavailable.** |
| `recordingUrl` | string (uri) | yes | Download/access URL for the voicemail audio. **Null if not completed or URL unavailable.** |
| `status` | enum string | no | One of: `completed`, `in-progress`. |

**Gotchas — Voicemail**
- While processing (`status: "in-progress"`), `duration`, `transcript`, and `recordingUrl` are all **null**. Re-fetch until `status: "completed"`.
- Voicemail `status` enum is only `completed` / `in-progress` (no `failed`/`absent`), unlike recordings/summary/transcription.
- `recordingUrl` points at external storage and is likely a time-limited signed URL — download promptly.
- Voicemail transcript availability is not explicitly plan-gated in the docs (unlike summary/transcript, which require business/scale), but the AI-generated transcript field can still be null.
- Error codes: `400` (`1200400`), `401` (`1200401`), `403` (`1200403`), `404` (`1200404`), `500` (`1201500`).

Example:

```bash
curl --request GET \
  --url 'https://api.quo.com/v1/call-voicemails/ACsampleActivity02' \
  --header 'Authorization: YOUR_RAW_API_KEY'
```

---

### Cross-endpoint summary

| Endpoint | Method | Path | `data` shape | Plan-gated |
|---|---|---|---|---|
| List calls | GET | `/v1/calls` | array of call | no |
| Get a call by ID | GET | `/v1/calls/{callId}` | single call | no |
| Get recordings | GET | `/v1/call-recordings/{callId}` | array of recording | no |
| Get summary | GET | `/v1/call-summaries/{callId}` | single summary | **business + scale only** |
| Get transcription | GET | `/v1/call-transcripts/{id}` | single transcript | **business + scale only** |
| Get voicemail | GET | `/v1/call-voicemails/{callId}` | single voicemail | no (transcript field still nullable) |

Note the inconsistent path-param name: transcription uses `{id}`; all others use `{callId}`. The resource path segments also differ from the entity ID prefixes (e.g. recordings live under `/call-recordings/` keyed by the `AC…` call ID, and return their own `CR…`-style recording IDs).
