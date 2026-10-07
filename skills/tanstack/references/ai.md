# TanStack AI

> Verified 2026-10-07 against `@tanstack/ai@0.65.1` / `@tanstack/ai-react@0.30.0` / `@tanstack/ai-client@0.38.0` docs (TanStack CLI 0.71.1). Pre-1.0: minors break. Re-check with `tanstack doc ai <path>` when the installed version differs.

## Contents
When to use · Packages · Mental model · Core API · Patterns · Traps · Migration notes · Go deeper

## When to use / when not to
- Use for: streaming chat with a server-held provider key, isomorphic tools (one definition, `.server()` or `.client()` implementation), human approval of tool calls, typed structured output, agent loops, resumable streams, sandboxed coding agents.
- Skip for: one-off server-side completion where the raw provider SDK is enough; pure UI work. For production chat-workspace UX (threads, composer, attachments, message rendering), prefer a dedicated `tanstack-ai-chat` skill if one is installed. This file covers the core integration.

## Packages
| Package | Role |
|---|---|
| `@tanstack/ai` | Server core: `chat`, `toolDefinition`, `toServerSentEventsResponse`, `chatParamsFromRequest`, strategies, middleware, `embed`, `summarize`, `decide`. Peer: `@opentelemetry/api` |
| `@tanstack/ai-client` | Headless `ChatClient`, connection adapters, `createChatClientOptions`, `InferChatMessages` |
| `@tanstack/ai-react` / `-vue` / `-solid` / `-preact` | `useChat` (re-exports connection adapters). Peer: `react >=18`, `@tanstack/ai ^0.65` |
| `@tanstack/ai-svelte` | `createChat` (getters, not stores) |
| `@tanstack/ai-angular` | `injectChat` (field initializer or constructor only) |
| Providers | `@tanstack/ai-openai`, `-anthropic`, `-gemini`, `-ollama`, `-openrouter` (recommended for one key, 300+ models), `-groq`, `-grok`, `-bedrock`, `-vertex`, `-cloudflare`, ... |
| Durability | `memoryStream` (in `@tanstack/ai`), `@tanstack/ai-durable-stream` (`durableStream`) |
| Sandboxes | `@tanstack/ai-sandbox` + provider pkg such as `@tanstack/ai-sandbox-docker` |
| Devtools | `@tanstack/react-ai-devtools` + `@tanstack/react-devtools` |

```bash
npm i @tanstack/ai @tanstack/ai-react @tanstack/ai-openai zod
npm i -D @tanstack/react-ai-devtools @tanstack/react-devtools
```

## Mental model
- The **server** owns the provider key and calls `chat()`. `chat()` returns an async iterable of AG-UI `StreamChunk`s. You wrap it in a `Response` (`toServerSentEventsResponse` / `toHttpResponse`).
- The **adapter** is activity-specific and carries the model: `openaiText('gpt-5.5')`, `anthropicText(...)`, `geminiText(...)`, `ollamaText(...)`. No `model:` option on `chat()`.
- The **client** (`useChat`) sends an AG-UI `RunAgentInput` body. Parse it on the server with `chatParamsFromRequest(request)`, not `request.json()`.
- A **thread** is the conversation (`threadId`). A **run** is one `RUN_STARTED` → `RUN_FINISHED` execution (`runId`). An interrupt ends a run, and the continuation is a new run with `parentRunId`.
- **Tools** are declared once with `toolDefinition()`. Pass `.server(fn)` to `chat()` for server execution. Pass the bare definition to `chat()` plus `.client(fn)` to `useChat({ tools })` for browser execution.
- The **agent loop** keeps going while the model returns tool calls and the `agentLoopStrategy` allows it. Default: `maxIterations(5)` model turns.
- **Interrupts** (approvals, client-tool execution, generic pauses) surface as `interrupts` on `useChat`. You resolve them per item.
- **Durability** (resumable streams) replays a live run after a reload. **Persistence** (saving the conversation) is a separate layer.

## Core API
Server route (any host that returns a Web `Response`):
```ts
import { chat, chatParamsFromRequest, toServerSentEventsResponse } from '@tanstack/ai'
import { openaiText } from '@tanstack/ai-openai'

export async function POST(request: Request) {
  const { messages, threadId, runId } = await chatParamsFromRequest(request) // throws 400 Response on bad body
  const abortController = new AbortController()
  const stream = chat({
    adapter: openaiText('gpt-5.5'),       // model lives on the adapter
    messages,
    threadId,
    runId,
    systemPrompts: ['You are a helpful assistant'],
    modelOptions: { temperature: 0.3, max_output_tokens: 1000 }, // provider-native keys
    abortController,
  })
  return toServerSentEventsResponse(stream, { abortController }) // same controller -> stop() halts the model
}
```
Client:
```tsx
import { useState } from 'react'
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'

export function Chat() {
  const [input, setInput] = useState('')
  const { messages, sendMessage, isLoading, stop, error } = useChat({
    connection: fetchServerSentEvents('/api/chat'),
  })
  return (
    <>
      {messages.map((m) => (
        <div key={m.id}>
          {m.parts.map((p, i) => (p.type === 'text' ? <p key={i}>{p.content}</p> : null))}
        </div>
      ))}
      <form onSubmit={(e) => { e.preventDefault(); if (!input.trim()) return; sendMessage(input); setInput('') }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} />
        {isLoading ? <button type="button" onClick={stop}>Stop</button> : <button type="submit">Send</button>}
      </form>
    </>
  )
}
```
`useChat` options (verified): `connection` | `fetcher` (exactly one), `tools`, `initialMessages`, `threadId`, `forwardedProps`, `body` (deprecated), `context`, `outputSchema`, `onResponse`, `onChunk`, `onFinish`, `onError`, `onInterruptStateChange`. Return values include `messages`, `sendMessage(content, { body })`, `append`, `addToolResult`, `reload`, `stop`, `isLoading`, `error`, `setMessages`, `clear`, `interrupts`, `resuming`, and with `outputSchema` also `partial` and `final`.

Other adapters: Vue `useChat` returns refs (`.value` in script). Solid returns accessors (`messages()`). Svelte `createChat` returns getters (`chat.messages`). Call `chat.stop()` in `onDestroy`. Angular `injectChat` returns Signals.

Connection adapters (all from `@tanstack/ai-react` or `@tanstack/ai-client`): `fetchServerSentEvents` (default), `fetchHttpStream` (NDJSON, when SSE is blocked; server side `toHttpResponse`), `xhrHttpStream` / `xhrServerSentEvents` (React Native/Expo), `stream(factory)` (sync async-iterable), `rpcStream`, `webSocket` (server `toWebSocketResponse`). URL, `headers` and `body` can be functions for per-request values.

## Patterns
**1. TanStack Start server route** (`src/routes/api.chat.ts` maps to `/api/chat`):
```ts
import { createFileRoute } from '@tanstack/react-router'
import { chat, chatParamsFromRequest, toServerSentEventsResponse } from '@tanstack/ai'
import { openaiText } from '@tanstack/ai-openai'

export const Route = createFileRoute('/api/chat')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const p = await chatParamsFromRequest(request)
        return toServerSentEventsResponse(
          chat({ adapter: openaiText('gpt-5.5'), messages: p.messages, threadId: p.threadId, runId: p.runId }),
        )
      },
    },
  },
})
```
To call a Start **server function** instead of HTTP, use `fetcher` (async), not `stream()` (sync only):
```ts
useChat({ fetcher: ({ messages }, { signal }) => chatFn({ data: { messages }, signal }) })
```

**2. Server tool + agent loop control**
```ts
import { chat, toolDefinition, maxIterations, combineStrategies, type AgentLoopState } from '@tanstack/ai'
import { z } from 'zod'

const getWeatherDef = toolDefinition({
  name: 'get_weather',
  description: 'Get current weather for a city',
  inputSchema: z.object({ city: z.string() }),
  outputSchema: z.object({ temp: z.number(), conditions: z.string() }),
})
const getWeather = getWeatherDef.server(async ({ city }, { context, emitCustomEvent }) => {
  emitCustomEvent('progress', { step: 1 })
  return { temp: 62, conditions: 'cloudy' }
})

chat({
  adapter: openaiText('gpt-5.5'),
  messages,
  tools: [getWeather],
  toolExecution: 'sequential', // default runs one turn's server tools concurrently
  agentLoopStrategy: combineStrategies([maxIterations(10), ({ messages }: AgentLoopState) => messages.length < 100]),
})
```
Other strategy: `untilFinishReason(['stop', 'length'])`. There is no built-in tool-call cap. Use middleware (`onBeforeToolCall` returning `{ type: 'skip', result }`, plus `onShouldContinue`). See `chat/agentic-cycle`.

**3. Client tool (runs in the browser).** On the server, pass the **definition**. On the client, register the `.client()` implementation:
```ts
// server: chat({ ..., tools: [updateUIDef] })
// client:
import { createChatClientOptions, type InferChatMessages } from '@tanstack/ai-client'
const updateUI = updateUIDef.client((input) => { toast(input.message); return { success: true } })
const opts = createChatClientOptions({ connection: fetchServerSentEvents('/api/chat'), tools: [updateUI] })
type Msgs = InferChatMessages<typeof opts>
const { messages } = useChat(opts) // part.type === 'tool-call' && part.name === 'update_ui' narrows input/output
```

**4. Approval (interrupt).** Add `needsApproval: true` to the definition. Forward the resume fields on the server:
```ts
const p = await chatParamsFromRequest(request)
chat({
  adapter: openaiText('gpt-5.5'),
  messages: p.messages, threadId: p.threadId, runId: p.runId, parentRunId: p.parentRunId,
  ...(p.resume ? { resume: p.resume } : {}),
  tools: [transfer], // transferTool.server(...)
})
```
```tsx
const { interrupts, resuming } = useChat({ connection, threadId: 'acct-42', tools: [transferTool] as const })
interrupts.map((it) =>
  it.kind === 'tool-approval' && it.toolName === 'transfer' ? (
    <div key={it.id}>
      Send {it.originalArgs.amount}?
      <button disabled={!it.canResolve || resuming} onClick={() => it.resolveInterrupt(true)}>Approve</button>
      <button disabled={!it.canResolve || resuming} onClick={() => it.resolveInterrupt(false)}>Reject</button>
    </div>
  ) : null,
)
```
`resolveInterrupt(true, { editedArgs, payload })` replaces the args (full replacement, validated against `inputSchema`). `resolveInterrupt(false, { payload })` is a rejection that the model sees. `it.cancel()` abandons the pause without choosing a branch. The server is stateless: it rebuilds the batch from the submitted history.

**5. Structured output**
```ts
const person = await chat({ adapter: openaiText('gpt-5.5'), messages, outputSchema: z.object({ name: z.string(), age: z.number() }) })
// streaming: chat({ ..., outputSchema, stream: true }) -> useChat({ outputSchema }) gives `partial` (DeepPartial) and `final` (T | null)
```
Accepts Standard JSON Schema (Zod 4.2+, ArkType, Valibot via converter). Anthropic rejects schemas it judges "too complex" (400). Remove optional, union and default fields to fix it.

**6. Resumable stream (durability)**
```ts
import { memoryStream, resumeServerSentEventsResponse } from '@tanstack/ai'
// POST: return toServerSentEventsResponse(stream, { durability: { adapter: memoryStream(request) } })
export async function GET(request: Request) {
  return resumeServerSentEventsResponse({ adapter: memoryStream(request) }) // replay only, no model call
}
```
In production, swap in `durableStream(request, options)` from `@tanstack/ai-durable-stream`. `memoryStream` works in a single process only.

**Sandboxes** (coding agents that need a shell): `defineSandbox({ provider: dockerSandbox(...), workspace: defineWorkspace({...}) })`, then `chat({ adapter: grokBuildText(...) /* or claudeCodeText, codexText, opencodeText */, middleware: [withSandbox(def)] })`. A harness adapter fails fast if no sandbox middleware is present. See `sandbox/overview`.

**Devtools**
```tsx
<TanStackDevtools plugins={[aiDevtoolsPlugin()]} eventBusConfig={{ connectToServerBus: true }} />
// import { aiDevtoolsPlugin } from '@tanstack/react-ai-devtools'
```

## Traps
1. **Monolithic adapter + `model:` option.** `chat({ adapter: openai(), model: 'gpt-4o' })` no longer exists. Use `chat({ adapter: openaiText('gpt-4o') })`. Embeddings use `openaiEmbedding(model)` with `embed()`, not `openaiEmbed`/`embedding()`. (`migration/migration`)
2. **Root-level `temperature` / `topP` / `maxTokens`.** These were removed. They neither type-check nor take effect. Put them in `modelOptions` under the provider's own key: OpenAI `max_output_tokens`/`top_p`, Anthropic `max_tokens`, Gemini `maxOutputTokens`/`topP`, Ollama nested `options.num_predict`. The codemod is in the doc. (`migration/sampling-options-to-model-options`)
2a. **Per-model option types are narrower than the provider's.** `modelOptions` is typed per model id. In `@tanstack/ai-anthropic` 0.19.5, `claude-sonnet-5-5` accepts `max_tokens` but **not** `temperature`/`top_p`, and `tsc` rejects them; the adapter notes that Sonnet 5 returns a 400 for non-default sampling. When the user asks for a temperature, check the installed adapter's model-options type, tell them if the chosen model cannot take it, and do not cast around it. (Observed in two independent eval runs with `tsc --strict`, 2026-10-07.)
3. **`providerOptions` and `toResponseStream`.** These were renamed to `modelOptions` and `toServerSentEventsStream`. The latter returns a bare `ReadableStream`. Prefer `toServerSentEventsResponse(stream, { abortController })`, which builds the `Response`. (`migration/migration`)
4. **`const { messages } = await request.json()`** still appears in older doc samples. With current `useChat`, the body is AG-UI `RunAgentInput`. Use `chatParamsFromRequest`, which also gives you `threadId`, `runId`, `parentRunId`, `resume` and `forwardedProps`. Next.js, SvelteKit, Hono and raw Node do **not** convert the thrown 400 `Response`. Wrap the call in try/catch there, or use `chatParamsFromRequestBody`. (`api/ai`)
5. **Approval resumes dropped.** If the route never forwards `parentRunId` and `resume` into `chat()`, approvals loop or are lost. (`interrupts/tool-approval`)
6. **Legacy approval API.** `addToolApprovalResponse({ id, approved })`, `pendingInterrupts` and the `approval-requested` / `tool-input-available` custom events are deprecated. Use `interrupts` + `resolveInterrupt`. Denial (`resolveInterrupt(false)`) is not cancellation (`cancel()`). (`interrupts/migration`)
7. **Client tool passed as `.server()` or missing on the client.** For browser execution, the server receives the *definition* and `useChat({ tools })` receives the `.client()` impl. If you pass both a definition and a server impl of the same tool in one `chat()` call, you have mixed up two separate modes. (`tools/tools`)
8. **Stop doesn't stop the model.** `stop()` only aborts the fetch, unless the same `AbortController` goes to both `chat()` and `toServerSentEventsResponse`. (`chat/streaming`)
9. **`maxIterations` caps model turns, not tool calls.** One turn can fan out many parallel tools. Default is 5 turns, which is often too few for agents. (`chat/agentic-cycle`)
10. **Resume re-runs side effects.** On reconnect the client re-POSTs. The model is replayed from the log, but your handler's DB writes run again. Guard them with the adapter's `resumeFrom()` (null on a fresh request). (`resumable-streams/overview`)
11. **Server function via `stream()`.** A Start `createServerFn` returns a Promise, which `stream()` won't accept. Use the `fetcher` option. (`chat/connection-adapters`)
12. **`body` on `useChat`.** It is deprecated and maps to AG-UI `forwardedProps`. Read it server-side as `forwardedProps` from `chatParamsFromRequest`. `reload()` does not replay a per-call `sendMessage` body. (`chat/connection-adapters`)
13. **OpenRouter web search import.** `createWebSearchTool` from the package root was removed. Use `webSearchTool` from `@tanstack/ai-openrouter/tools`. Provider tools live on each adapter's `/tools` subpath. (`migration/migration`)
14. **Keys in the browser.** Adapters read `OPENAI_API_KEY` etc. on the server. For user-supplied keys use BYOK (`useChat({ byok })` + `getByokKey` server-side); never put a provider key in client code. (`advanced/byok`)

## Migration notes
| Old (from memory / early 0.x) | Current |
|---|---|
| `openai()` + `model: '...'` | `openaiText('...')` (also `openaiImage`, `openaiSpeech`, `openaiTranscription`, `openaiSummarize`, `openaiVideo`) |
| `options: { temperature, maxTokens }` then root `temperature` | `modelOptions: { temperature, max_output_tokens }` (provider-native) |
| `providerOptions` | `modelOptions` |
| `toResponseStream(stream, { abortController })` | `toServerSentEventsResponse(stream, { abortController })` or `toServerSentEventsStream(stream, abortController)` |
| `embedding({ adapter: openaiEmbed(), model })` | `embed({ adapter: openaiEmbedding(model), input })` |
| `await request.json()` | `await chatParamsFromRequest(request)` |
| `addToolApprovalResponse({ id, approved })` | `interrupt.resolveInterrupt(approved, { payload?, editedArgs? })` |
| `pendingInterrupts`, `getPendingInterrupts()` | `interrupts`, `getInterrupts()` |
| `onToolCall` callback for client tools | automatic execution of registered `.client()` tools |
| `useChat({ body })` | `useChat({ forwardedProps })` |
| `createWebSearchTool` (openrouter root) | `webSearchTool` from `@tanstack/ai-openrouter/tools` |

## Go deeper
- `tanstack doc ai getting-started/quick-start`: install and first chat, all frameworks
- `tanstack doc ai chat/streaming`: cancel, backpressure, incomplete-stream errors
- `tanstack doc ai chat/connection-adapters`: SSE, NDJSON, RN, fetcher, WebSocket
- `tanstack doc ai chat/agentic-cycle`: loop strategies, tool budgets
- `tanstack doc ai tools/tools`: toolDefinition, hybrid, sequential
- `tanstack doc ai tools/server-tools`: runtime context, progress events
- `tanstack doc ai tools/client-tools`: browser execution, addToolResult
- `tanstack doc ai interrupts/overview`: two-run pause model
- `tanstack doc ai interrupts/tool-approval`: approve, reject, edit args
- `tanstack doc ai interrupts/migration`: legacy approval API mapping
- `tanstack doc ai structured-outputs/overview`: outputSchema, provider limits
- `tanstack doc ai structured-outputs/streaming`: partial/final in useChat
- `tanstack doc ai resumable-streams/overview`: durability adapters, GET replay
- `tanstack doc ai sandbox/overview`: harness agents in sandboxes
- `tanstack doc ai migration/sampling-options-to-model-options`: provider key table, codemod
- `tanstack doc ai migration/migration`: adapter split, renames
- `tanstack doc ai advanced/middleware`: middleware hook reference
- `tanstack doc ai tutorials/basic-chat`: Start app with BYOK
- `tanstack doc ai api/ai`: chat() parameters, helpers
- `tanstack doc ai api/ai-react`: useChat options/returns
- `tanstack doc ai getting-started/devtools`: AI devtools plugin
