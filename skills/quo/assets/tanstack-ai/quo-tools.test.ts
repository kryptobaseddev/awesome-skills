/**
 * quo-tools.test.ts: offline contract test for quo-client.ts + quo-tools.ts.
 * Mocks fetch (no API key, no network) and checks the behaviour the tools
 * promise: headers per surface, filter serialization, policy gates, no retry
 * on sends, 429 backoff, the 10 req/s limiter, schema rejection, approval flags.
 *
 *   npx tsx quo-tools.test.ts      # exits 1 on any FAIL
 */
import { createQuoClient } from './quo-client'
import { createQuoTools, estimateSegments } from './quo-tools'

// Parse like TanStack AI does before execute: Standard Schema validate (applies Zod defaults).
function parseWithStandardSchema(schema: any, value: unknown) {
  const r = schema['~standard'].validate(value)
  if (r instanceof Promise) throw new Error('async schema')
  if (r.issues) throw new Error(JSON.stringify(r.issues))
  return r.value
}

type Call = { method: string; url: URL; headers: Record<string, string>; body?: any; t: number }
const calls: Call[] = []
let script: Array<(c: Call) => Response | undefined> = []
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
const fakeFetch = (async (input: any, init: any) => {
  const c: Call = { method: init.method, url: new URL(String(input)), headers: init.headers, body: init.body ? JSON.parse(init.body) : undefined, t: Date.now() }
  calls.push(c)
  for (const h of script) { const r = h(c); if (r) return r }
  return json(200, { data: [], nextCursor: null })
}) as typeof fetch
let fails = 0
const check = (name: string, cond: boolean, extra?: unknown) => { console.log(`${cond ? 'PASS' : 'FAIL'} ${name}`, cond ? '' : JSON.stringify(extra)); if (!cond) fails++ }

const quo = createQuoClient({ apiKey: 'k_test', fetch: fakeFetch, maxRps: 10, maxRetries: 2 })
const tools = createQuoTools(quo, { allowedInboxIds: ['PNallowed'], scheduler: { schedule: async () => ({ jobId: 'job1' }) } })
const byName = Object.fromEntries(tools.map((t: any) => [t.name, t]))
const run = async (name: string, raw: any) => { const t = byName[name]; const args = parseWithStandardSchema(t.inputSchema, raw); return t.execute(args, { emitCustomEvent() {} }) }

// 1 v2 read: header, raw key, bracket filters
calls.length = 0
await run('quo_list_calls', { statuses: ['missed', 'no-answer'], createdAfter: '2026-10-01T00:00:00Z' })
let c = calls[0]!
check('v2 path has no /v1', c.url.pathname === '/calls')
check('v2 sends Quo-Api-Version', c.headers['Quo-Api-Version'] === '2026-03-30')
check('raw key, no Bearer', c.headers['Authorization'] === 'k_test')
check('status[in] comma list', c.url.searchParams.get('status[in]') === 'missed,no-answer', c.url.search)
check('createdAt[gte]', c.url.searchParams.get('createdAt[gte]') === '2026-10-01T00:00:00Z')
check('include=summary,voicemail', c.url.searchParams.get('include') === 'summary,voicemail', c.url.search)
check('single allowed inbox auto-scoped', c.url.searchParams.get('phoneNumberId') === 'PNallowed')

// 2 v1 thread: repeated participants, no version header
calls.length = 0
await run('quo_get_thread', { phoneNumberId: 'PNallowed', participants: ['+14155550100', '+14155550101'] })
c = calls[0]!
check('v1 path', c.url.pathname === '/v1/messages')
check('v1 no version header', !('Quo-Api-Version' in c.headers))
check('v1 repeated participants', c.url.searchParams.getAll('participants').length === 2, c.url.search)
check('v1 maxResults default applied', c.url.searchParams.get('maxResults') === '30')

// 3 policy: disallowed inbox -> tool error, no HTTP call
calls.length = 0
let r: any = await run('quo_send_message', { fromPhoneNumberId: 'PNother', to: ['+14155550100'], content: 'hi' })
check('disallowed inbox blocked', r.ok === false && r.error === 'policy' && calls.length === 0, r)
r = await run('quo_send_message', { fromPhoneNumberId: 'PNallowed', to: ['+14155550100', '+14155550101'], content: 'hi' })
check('recipient cap blocks group send', r.ok === false && calls.length === 0, r)

// 4 send 500 -> NOT retried, outcome-unknown hint
script = [(c) => (c.method === 'POST' && c.url.pathname === '/v1/messages' ? json(500, { title: 'Internal Server Error', message: 'boom', trace: 't1' }) : undefined)]
calls.length = 0
r = await run('quo_send_message', { fromPhoneNumberId: 'PNallowed', to: ['+14155550100'], content: 'Your appointment is tomorrow at 3pm' })
check('send not retried on 500', calls.length === 1, calls.length)
check('send 500 says do not resend', r.ok === false && /Do NOT resend/.test(r.hint) && r.trace === 't1', r)

// 5 send success
script = [(c) => (c.method === 'POST' ? json(202, { data: { id: 'ACm1', conversationId: 'CN1', status: 'queued' } }) : undefined)]
r = await run('quo_send_message', { fromPhoneNumberId: 'PNallowed', to: ['+14155550100'], content: 'ok' })
check('send success projection', r.ok && r.messageId === 'ACm1' && r.segments === 1, r)
check('send body uses from/to/content', JSON.stringify(calls.at(-1)!.body) === JSON.stringify({ from: 'PNallowed', to: ['+14155550100'], content: 'ok' }), calls.at(-1)!.body)

// 6 GET 429 retried then success; 400 surfaces issues
let n = 0
script = [(c) => (c.url.pathname === '/users' && n++ < 1 ? new Response('{"title":"Too Many Requests","message":"slow"}', { status: 429, headers: { 'retry-after': '1' } }) : undefined)]
calls.length = 0
r = await run('quo_list_users', {})
check('GET retried after 429', calls.length === 2 && r.ok === true, { len: calls.length, r })
script = [() => json(400, { title: 'Bad Request', message: 'Validation failed for 1 field.', errors: [{ path: '/query/limit', message: 'must be <= 50', value: 200 }] })]
r = await run('quo_find_contacts', { externalIds: ['crm-1'] })
check('400 -> issues for model', r.ok === false && r.issues[0].path === '/query/limit' && /Fix the fields/.test(r.hint), r)
check('externalId[in]', calls.at(-1)!.url.searchParams.get('externalId[in]') === 'crm-1')

// 7 rate limiter: 25 parallel GETs never exceed 10 within any 1s window
script = []; calls.length = 0
await Promise.all(Array.from({ length: 25 }, () => quo.v2('GET', '/users')))
const ts = calls.map((c) => c.t).sort((a, b) => a - b)
let maxWin = 0
for (let i = 0; i < ts.length; i++) { let j = i; while (j < ts.length && ts[j]! - ts[i]! < 1000) j++; maxWin = Math.max(maxWin, j - i) }
check('limiter <=10 per second', maxWin <= 10, maxWin)

// 8 schema rejects bad ids / non-E.164 before any call
let threw = false
try { parseWithStandardSchema(byName['quo_send_message'].inputSchema, { fromPhoneNumberId: 'abc', to: ['4155550100'], content: 'x' }) } catch { threw = true }
check('schema rejects bad PN id and non-E.164', threw)

// 9 schedule: past time rejected
r = await run('quo_schedule_message', { fromPhoneNumberId: 'PNallowed', to: ['+14155550100'], content: 'x', sendAt: '2020-01-01T00:00:00Z' })
check('schedule rejects past sendAt', r.ok === false && r.error === 'policy', r)

// 10 approval flags
check('send needsApproval', byName['quo_send_message'].needsApproval === true)
check('schedule needsApproval', byName['quo_schedule_message'].needsApproval === true)
check('reads have no approval', !byName['quo_list_calls'].needsApproval)
check('readOnly drops writes', createQuoTools(quo, { readOnly: true }).every((t: any) => !/send|create|update|add|set|schedule/.test(t.name)))

// 11 transcript flatten
script = [(c) => (c.url.pathname.endsWith('/transcripts') ? json(200, { data: [{ recordingId: 'CR1', status: 'completed', startTime: 'x', createdAt: 'x', duration: 3, dialogue: [{ content: 'Hello', start: 0, end: 1, identifier: '+14155550100', actorId: null }] }], nextCursor: null }) : undefined)]
r = await run('quo_get_call_transcript', { callId: 'ACcall1' })
check('transcript lines', r.untrustedTranscript === '+14155550100: Hello' && r.status === 'completed', r)

// 12 send ledger: a replayed approval (same toolCallId) executes once
script = [(c) => (c.method === 'POST' ? json(202, { data: { id: 'ACm2', conversationId: 'CN1', status: 'queued' } }) : undefined)]
calls.length = 0
const sendTool = byName['quo_send_message']
const sendArgs = parseWithStandardSchema(sendTool.inputSchema, { fromPhoneNumberId: 'PNallowed', to: ['+14155550100'], content: 'replay me' })
const first: any = await sendTool.execute(sendArgs, { toolCallId: 'tc-1', emitCustomEvent() {} })
const second: any = await sendTool.execute(sendArgs, { toolCallId: 'tc-1', emitCustomEvent() {} })
check('ledger: first send ok', first.ok === true)
check('ledger: replayed approval blocked, one POST', second.ok === false && calls.filter((c) => c.method === 'POST').length === 1, { second, n: calls.length })

// 13 missed flag: incoming completed-but-unanswered counts as missed
script = [(c) => (c.url.pathname === '/calls' ? json(200, { data: [
  { id: 'AC1', direction: 'incoming', status: 'completed', answeredAt: null, phoneNumberId: 'PNallowed', participants: [] },
  { id: 'AC2', direction: 'incoming', status: 'completed', answeredAt: '2026-10-07T10:00:00Z', phoneNumberId: 'PNallowed', participants: [] },
  { id: 'AC3', direction: 'incoming', status: 'busy', answeredAt: null, phoneNumberId: 'PNallowed', participants: [] },
  { id: 'AC4', direction: 'outgoing', status: 'no-answer', answeredAt: null, phoneNumberId: 'PNallowed', participants: [] },
  { id: 'AC5', direction: 'incoming', status: 'completed', answeredAt: null, aiHandled: true, phoneNumberId: 'PNallowed', participants: [] },
  { id: 'AC6', direction: 'incoming', status: 'forwarded', answeredAt: null, forwardedTo: '+14155550199', phoneNumberId: 'PNallowed', participants: [] },
], nextCursor: null }) : undefined)]
r = await run('quo_list_calls', {})
check('missed flag (AI-handled and forwarded excluded)', JSON.stringify(r.calls.map((c: any) => c.missed)) === '[true,false,true,false,false,false]', r.calls.map((c: any) => c.missed))

// 15 scoped assistant may only change conversations it has seen
script = []
r = await run('quo_set_conversation_state', { conversationId: 'CNunseen', state: 'done' })
check('unseen conversation blocked when scoped', r.ok === false && r.error === 'policy', r)
script = [(c) => (c.url.pathname === '/conversations' && c.method === 'GET' ? json(200, { data: [{ id: 'CNseen', phoneNumberId: 'PNallowed', participants: [] }], nextCursor: null }) : undefined)]
await run('quo_list_conversations', {})
script = [(c) => (c.method === 'POST' ? json(200, { data: { id: 'CNseen' } }) : undefined)]
r = await run('quo_set_conversation_state', { conversationId: 'CNseen', state: 'done' })
check('seen conversation allowed', r.ok === true, r)

// 14 injected cross-process limiter is used instead of the local one
let acquired = 0
const q2 = createQuoClient({ apiKey: 'k', fetch: fakeFetch, limiter: async () => { acquired++ } })
await q2.v2('GET', '/users')
check('custom limiter used', acquired === 1)

check('segments GSM', estimateSegments('a'.repeat(161)).segments === 2)
check('segments UCS-2', estimateSegments('héllo 😀').encoding === 'UCS-2')
console.log(fails ? `${fails} FAILED` : 'ALL PASS'); process.exit(fails ? 1 : 0)
