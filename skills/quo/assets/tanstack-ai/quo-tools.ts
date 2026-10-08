/**
 * quo-tools.ts: a TanStack AI (`@tanstack/ai` >= 0.66) tool catalog for Quo
 * (formerly OpenPhone). It is server-only because the tools close over the Quo
 * API key through `QuoClient`.
 *
 *   import { chat, maxIterations } from '@tanstack/ai'
 *   import { createQuoClient } from './quo-client'
 *   import { createQuoTools } from './quo-tools'
 *
 *   const quo = createQuoClient()                       // reads QUO_API_KEY
 *   const tools = createQuoTools(quo, { allowedInboxIds: ['PNabc123'] })
 *   chat({ adapter, messages, tools, toolExecution: 'sequential', agentLoopStrategy: maxIterations(8) })
 *
 * Design rules baked in (see references/agent-tools-tanstack.md):
 *   - One verb per tool, flat Zod inputs with described fields and strict id/E.164 patterns,
 *     so the model fills them correctly the first time.
 *   - Compact outputs: projections, not raw API payloads. Fewer tokens, less leaked data.
 *   - Anything that reaches a customer (send, schedule) is `needsApproval: true`.
 *     Approval is a UI gate, not authorization: `policy` is re-checked inside execute.
 *   - Errors come back as data (`{ ok: false, issues, hint }`), so the model can repair
 *     a bad call instead of the run crashing. Sends are never auto-retried.
 *   - Customer-authored text (messages, transcripts, notes) is marked untrusted.
 */
import { QuoApiError, type QuoClient } from './quo-client'
import { estimateSegments, quoToolDefs, UNTRUSTED } from './quo-tool-defs'

export { estimateSegments, quoToolDefs } from './quo-tool-defs'

// ---------------------------------------------------------------------------
// Policy
// ---------------------------------------------------------------------------

export interface ScheduledMessage {
  from: string
  to: string[]
  content: string
  sendAt: string
}

export interface QuoToolPolicy {
  /** PN ids the agent may read from and send from. Omit to allow every workspace number. */
  allowedInboxIds?: string[]
  /** Hard cap on recipients per send. Default 1. Quo allows up to 10, which creates ONE shared group thread. */
  maxRecipientsPerSend?: number
  /** Drop every write tool (send, schedule, contacts, tasks, notes, conversation state). */
  readOnly?: boolean
  /** Truncate transcript text returned to the model. Default 12 000 chars. */
  maxTranscriptChars?: number
  /**
   * Quo has no scheduled-send endpoint. Provide a durable job queue (BullMQ, Inngest,
   * Cloudflare Queues, pg-boss, ...) whose worker calls POST /v1/messages at `sendAt`.
   * When omitted, quo_schedule_message is not registered.
   */
  scheduler?: {
    schedule(job: ScheduledMessage): Promise<{ jobId: string }>
  }
  /**
   * Send ledger: guards against executing one approved send twice (a replayed
   * approval, a duplicated continuation request, two server instances). Keyed by
   * the tool call id. Default: in-memory, which protects one process only; back it
   * with a unique-key table in production (INSERT ... ON CONFLICT DO NOTHING).
   */
  sendLedger?: {
    /** Return true if this key was not seen before and is now claimed. */
    claim(key: string): Promise<boolean>
  }
  /** Audit hook for every executed write. Called after the Quo call returns. */
  onWrite?: (event: { tool: string; input: unknown; result: unknown }) => void | Promise<void>
}

class PolicyError extends Error {}

function assertInbox(policy: QuoToolPolicy, phoneNumberId: string | undefined) {
  if (!phoneNumberId || !policy.allowedInboxIds?.length) return
  if (!policy.allowedInboxIds.includes(phoneNumberId)) {
    throw new PolicyError(`Inbox ${phoneNumberId} is not allowed for this assistant. Use quo_list_inboxes.`)
  }
}

/** Run a Quo call and convert failures into data the model can act on. */
async function guard<T>(fn: () => Promise<T>, onUnknown?: string): Promise<T | Record<string, unknown>> {
  try {
    return await fn()
  } catch (err) {
    if (err instanceof PolicyError) return { ok: false, error: 'policy', message: err.message }
    if (err instanceof QuoApiError) {
      const e = err.toToolError()
      return err.status >= 500 && onUnknown ? { ...e, hint: onUnknown } : e
    }
    if (err instanceof Error && err.name === 'AbortError') throw err
    return {
      ok: false,
      error: 'network',
      message: err instanceof Error ? err.message : String(err),
      hint: onUnknown ?? 'Request did not complete. Reads may be retried.',
    }
  }
}

// ---------------------------------------------------------------------------
// Server implementations
// ---------------------------------------------------------------------------

type Any = any

export function memorySendLedger(ttlMs = 24 * 60 * 60 * 1000): NonNullable<QuoToolPolicy['sendLedger']> {
  const seen = new Map<string, number>()
  return {
    async claim(key) {
      const now = Date.now()
      for (const [k, t] of seen) if (now - t > ttlMs) seen.delete(k)
      if (seen.has(key)) return false
      seen.set(key, now)
      return true
    },
  }
}

export function createQuoTools(quo: QuoClient, policy: QuoToolPolicy = {}) {
  const maxRecipients = Math.min(policy.maxRecipientsPerSend ?? 1, 10)
  const ledger = policy.sendLedger ?? memorySendLedger()
  /** Claim a send once per tool call; falls back to the argument fingerprint when no id is given. */
  const claimSend = (tool: string, toolCallId: string | undefined, args: unknown) =>
    ledger.claim(`${tool}:${toolCallId ?? JSON.stringify(args)}`)
  // Conversation ids this tool set has returned from an allowed inbox. Quo has no
  // GET /conversations/{id}, so a scoped assistant may only change conversations it has seen.
  const seenConversations = new Set<string>()
  const remember = <T extends { conversationId?: string | null }>(rows: T[]) => {
    for (const r of rows) if (r.conversationId) seenConversations.add(r.conversationId)
    return rows
  }
  const audit = async (tool: string, input: unknown, result: unknown) => {
    await policy.onWrite?.({ tool, input, result })
    return result
  }

  const reads = [
    quoToolDefs.listInboxes.server(() =>
      guard(async () => {
        const numbers = await quo.listAll<Any>('/phone-numbers', {}, { max: 200 })
        const allowed = policy.allowedInboxIds
        return {
          ok: true,
          inboxes: numbers
            .filter((n) => !allowed?.length || allowed.includes(n.id))
            .map((n) => ({ phoneNumberId: n.id, name: n.name, phoneNumber: n.phoneNumber })),
        }
      }),
    ),

    quoToolDefs.listUsers.server(({ limit, after }) =>
      guard(async () => {
        const page = await quo.v2<Any>('GET', '/users', { query: { limit, after } })
        return {
          ok: true,
          users: page.data.map((u: Any) => ({ userId: u.id, name: [u.firstName, u.lastName].filter(Boolean).join(' '), email: u.email, role: u.role })),
          nextCursor: page.nextCursor,
        }
      }),
    ),

    quoToolDefs.findMessages.server((i) =>
      guard(async () => {
        assertInbox(policy, i.phoneNumberId)
        if (!i.phoneNumberId && policy.allowedInboxIds?.length === 1) i.phoneNumberId = policy.allowedInboxIds[0]
        const page = await quo.v2<Any>('GET', '/messages', {
          query: {
            phoneNumberId: i.phoneNumberId,
            from: i.from,
            to: i.to,
            direction: i.direction,
            status: i.status,
            createdAt: { gt: i.createdAfter, lt: i.createdBefore },
            limit: i.limit,
            after: i.after,
          },
        })
        const rows = page.data.filter((m: Any) => !policy.allowedInboxIds?.length || policy.allowedInboxIds.includes(m.phoneNumberId))
        return { ok: true, note: UNTRUSTED, messages: remember(rows.map(projectMessage)), nextCursor: page.nextCursor }
      }),
    ),

    quoToolDefs.getThread.server((i) =>
      guard(async () => {
        assertInbox(policy, i.phoneNumberId)
        const page = await quo.v1<Any>('GET', '/v1/messages', {
          query: {
            phoneNumberId: i.phoneNumberId,
            participants: i.participants,
            createdAfter: i.createdAfter,
            maxResults: i.maxResults,
            pageToken: i.pageToken,
          },
        })
        return { ok: true, note: UNTRUSTED, messages: remember(page.data.map(projectMessage)), nextPageToken: page.nextPageToken ?? null }
      }),
    ),

    quoToolDefs.listConversations.server((i) =>
      guard(async () => {
        const ids = i.phoneNumberIds?.length ? i.phoneNumberIds : policy.allowedInboxIds
        ids?.forEach((id) => assertInbox(policy, id))
        const page = await quo.v2<Any>('GET', '/conversations', {
          query: {
            phoneNumberId: ids?.length ? { in: ids } : undefined,
            updatedAt: { gte: i.updatedAfter, lte: i.updatedBefore },
            sort: i.sort,
            limit: i.limit,
            after: i.after,
          },
        })
        return {
          ok: true,
          conversations: remember(page.data.map((c: Any) => ({
            conversationId: c.id,
            phoneNumberId: c.phoneNumberId,
            name: c.name,
            participants: c.participants,
            lastActivityId: c.lastActivityId,
            lastActivityAt: c.lastActivityAt,
            snoozedUntil: c.snoozedUntil,
          }))),
          nextCursor: page.nextCursor,
        }
      }),
    ),

    quoToolDefs.listCalls.server((i) =>
      guard(async () => {
        assertInbox(policy, i.phoneNumberId)
        if (!i.phoneNumberId && policy.allowedInboxIds?.length === 1) i.phoneNumberId = policy.allowedInboxIds[0]
        const include = [i.includeSummary && 'summary', i.includeVoicemail && 'voicemail'].filter(Boolean) as string[]
        const page = await quo.v2<Any>('GET', '/calls', {
          query: {
            phoneNumberId: i.phoneNumberId,
            participant: i.participant,
            direction: i.direction,
            status: i.statuses?.length === 1 ? i.statuses[0] : i.statuses?.length ? { in: i.statuses } : undefined,
            createdAt: { gte: i.createdAfter, lte: i.createdBefore },
            include: include.length ? include : undefined,
            limit: i.limit,
            after: i.after,
          },
        })
        const rows = page.data.filter((c: Any) => !policy.allowedInboxIds?.length || policy.allowedInboxIds.includes(c.phoneNumberId))
        return { ok: true, note: UNTRUSTED, calls: rows.map(projectCall), nextCursor: page.nextCursor }
      }),
    ),

    quoToolDefs.getCallTranscript.server(({ callId }) =>
      guard(async () => {
        const segments = await quo.listAll<Any>(`/calls/${encodeURIComponent(callId)}/transcripts`, {}, { max: 20 })
        const pending = segments.find((s) => s.status === 'in-progress')
        const lines = segments
          .filter((s) => s.status === 'completed')
          .flatMap((s) => s.dialogue.map((d: Any) => `${d.identifier ?? d.actorId ?? 'unknown'}: ${d.content}`))
        const text = lines.join('\n')
        const max = policy.maxTranscriptChars ?? 12_000
        return {
          ok: true,
          note: UNTRUSTED,
          status: pending ? 'in-progress' : lines.length ? 'completed' : (segments[0]?.status ?? 'absent'),
          untrustedTranscript: text.slice(0, max),
          truncated: text.length > max,
        }
      }),
    ),

    quoToolDefs.findContacts.server((i) =>
      guard(async () => {
        const page = await quo.v2<Any>('GET', '/contacts', {
          query: {
            externalId: i.externalIds?.length ? { in: i.externalIds } : undefined,
            source: i.sources?.length ? { in: i.sources } : undefined,
            limit: i.limit,
            after: i.after,
          },
        })
        return {
          ok: true,
          contacts: page.data.map((c: Any) => ({
            contactId: c.id,
            name: [c.firstName, c.lastName].filter(Boolean).join(' '),
            company: c.company,
            role: c.role,
            externalId: c.externalId,
            source: c.source,
          })),
          nextCursor: page.nextCursor,
        }
      }),
    ),

    quoToolDefs.getContact.server(({ contactId }) =>
      guard(async () => {
        const { data: c } = await quo.v1<Any>('GET', `/v1/contacts/${encodeURIComponent(contactId)}`)
        return {
          ok: true,
          note: UNTRUSTED,
          contact: {
            contactId: c.id,
            firstName: c.defaultFields.firstName,
            lastName: c.defaultFields.lastName,
            company: c.defaultFields.company,
            role: c.defaultFields.role,
            phoneNumbers: c.defaultFields.phoneNumbers.map((p: Any) => ({ label: p.name, value: p.value })),
            emails: c.defaultFields.emails.map((e: Any) => ({ label: e.name, value: e.value })),
            customFields: c.customFields.map((f: Any) => ({ name: f.name, key: f.key, value: f.value })),
            externalId: c.externalId,
            source: c.source, // integration-synced contacts (e.g. a CRM source) cannot be edited in Quo
          },
        }
      }),
    ),

    quoToolDefs.listTasks.server(({ limit, after }) =>
      guard(async () => {
        const page = await quo.v2<Any>('GET', '/tasks', { query: { limit, after } })
        return {
          ok: true,
          tasks: page.data.map((t: Any) => ({
            taskId: t.taskId,
            title: t.title,
            status: t.status,
            dueDate: t.dueDate,
            assignedTo: t.assignedTo,
            conversationId: t.conversationId,
            activityId: t.activityId,
            phoneNumberId: t.phoneNumberId,
          })),
          nextCursor: page.nextCursor,
        }
      }),
    ),
  ]

  if (policy.readOnly) return reads

  const writes = [
    quoToolDefs.sendMessage.server((i, ctx) =>
      guard(
        async () => {
          // Re-check policy here: an approval click is not authorization.
          assertInbox(policy, i.fromPhoneNumberId)
          if (i.to.length > maxRecipients) {
            throw new PolicyError(`At most ${maxRecipients} recipient(s) per send. Send private messages one call per person.`)
          }
          if (!(await claimSend('quo_send_message', ctx?.toolCallId, i))) {
            throw new PolicyError('This approved send already ran. Do not send it again; check quo_find_messages for its status.')
          }
          const body = {
            from: i.fromPhoneNumberId,
            to: i.to,
            content: i.content,
            userId: i.userId,
            setInboxStatus: i.markDone ? ('done' as const) : undefined,
          }
          const { data } = await quo.v1<Any>('POST', '/v1/messages', { body, retry: false })
          return audit('quo_send_message', i, {
            ok: true,
            messageId: data.id,
            conversationId: data.conversationId,
            status: data.status, // "queued" (202): delivery is reported later by message.delivered / message.failed webhooks
            ...estimateSegments(i.content),
          })
        },
        'Outcome unknown: the message may have been sent. Do NOT resend. Check with quo_find_messages (to + createdAfter) first.',
      ),
    ),

    quoToolDefs.setConversationState.server(({ conversationId, state }) =>
      guard(async () => {
        const path = `/conversations/${encodeURIComponent(conversationId)}/mark-as-${state}`
        if (policy.allowedInboxIds?.length && !seenConversations.has(conversationId)) {
          throw new PolicyError('Unknown conversation for this assistant. Find it first with quo_list_conversations or quo_find_messages.')
        }
        await quo.v2<Any>('POST', path, { retry: true })
        return audit('quo_set_conversation_state', { conversationId, state }, { ok: true, conversationId, state })
      }),
    ),

    quoToolDefs.createContact.server((i) =>
      guard(async () => {
        const body = {
          defaultFields: {
            firstName: i.firstName,
            lastName: i.lastName,
            company: i.company,
            role: i.role,
            // Zod defaults apply at runtime, but execute args are typed from the schema input.
            phoneNumbers: (i.phoneNumbers ?? []).map((p) => ({ name: p.label ?? 'mobile', value: p.value })),
            emails: (i.emails ?? []).map((e) => ({ name: e.label ?? 'work', value: e.value })),
          },
          externalId: i.externalId,
          source: i.source,
        }
        const { data } = await quo.v1<Any>('POST', '/v1/contacts', { body, retry: false })
        return audit('quo_create_contact', i, { ok: true, contactId: data.id })
      }),
    ),

    quoToolDefs.updateContact.server(({ contactId, ...fields }) =>
      guard(async () => {
        const body = Object.fromEntries(Object.entries(fields).filter(([, v]) => v !== undefined))
        if (!Object.keys(body).length) return { ok: false, error: 'validation', message: 'Nothing to change.' }
        await quo.v2<Any>('PATCH', `/contacts/${encodeURIComponent(contactId)}`, { body })
        return audit('quo_update_contact', { contactId, ...body }, { ok: true, contactId, changed: Object.keys(body) })
      }),
    ),

    quoToolDefs.addContactNote.server(({ contactId, text }) =>
      guard(async () => {
        const { data } = await quo.v2<Any>('POST', `/contacts/${encodeURIComponent(contactId)}/notes`, { body: { text } })
        return audit('quo_add_contact_note', { contactId }, { ok: true, noteId: data.id })
      }),
    ),

    quoToolDefs.createTask.server((i) =>
      guard(async () => {
        if (i.link.type === 'inbox') assertInbox(policy, i.link.phoneNumberId)
        const { type: _type, ...link } = i.link
        const body = { title: i.title, description: i.description, dueDate: i.dueDate, assignedTo: i.assignedTo, ...link }
        // v1 accepts phoneNumberId | conversationId | activityId; 2026-03-30 POST /tasks requires conversationId.
        const { data } = await quo.v1<Any>('POST', '/v1/tasks', { body, retry: false })
        return audit('quo_create_task', i, { ok: true, taskId: data.taskId ?? data.id })
      }),
    ),

    quoToolDefs.updateTask.server(({ taskId, action }) =>
      guard(async () => {
        const base = `/tasks/${encodeURIComponent(taskId)}`
        switch (action.type) {
          case 'complete':
          case 'reopen':
            await quo.v2('PATCH', `${base}/status`, { body: { status: action.type === 'complete' ? 'completed' : 'open' }, retry: true })
            break
          case 'setDueDate':
            await quo.v2('PATCH', `${base}/due-date`, { body: { dueDate: action.dueDate }, retry: true })
            break
          case 'clearDueDate':
            await quo.v2('DELETE', `${base}/due-date`, { retry: true })
            break
          case 'assign':
            await quo.v2('POST', `${base}/users`, { body: { userId: action.userId } })
            break
          case 'unassign':
            await quo.v2('DELETE', `${base}/users`, { body: { userId: action.userId } })
            break
        }
        return audit('quo_update_task', { taskId, action }, { ok: true, taskId, applied: action.type })
      }),
    ),
  ]

  const scheduler = policy.scheduler
  const scheduling = scheduler
    ? [
        quoToolDefs.scheduleMessage.server((i, ctx) =>
          guard(async () => {
            assertInbox(policy, i.fromPhoneNumberId)
            if (i.to.length > maxRecipients) throw new PolicyError(`At most ${maxRecipients} recipient(s) per message.`)
            if (Date.parse(i.sendAt) <= Date.now() + 30_000) throw new PolicyError('sendAt must be in the future; use quo_send_message to send now.')
            if (!(await claimSend('quo_schedule_message', ctx?.toolCallId, i))) {
              throw new PolicyError('This approved schedule request already ran. Do not schedule it again.')
            }
            const { jobId } = await scheduler.schedule({ from: i.fromPhoneNumberId, to: i.to, content: i.content, sendAt: i.sendAt })
            return audit('quo_schedule_message', i, { ok: true, jobId, sendAt: i.sendAt, ...estimateSegments(i.content) })
          }),
        ),
      ]
    : []

  return [...reads, ...writes, ...scheduling]
}

function projectMessage(m: Any) {
  return {
    messageId: m.id,
    conversationId: m.conversationId,
    direction: m.direction,
    from: m.from,
    to: m.to,
    status: m.status,
    createdAt: m.createdAt,
    untrustedText: m.text ?? m.content ?? null,
    media: (m.media ?? []).map((x: Any) => ({ url: x.url, type: x.type })),
  }
}

function projectCall(c: Any) {
  const external = (c.participants ?? []).filter((p: Any) => !p.actorId).map((p: Any) => p.phoneNumber)
  return {
    callId: c.id,
    phoneNumberId: c.phoneNumberId,
    direction: c.direction,
    status: c.status,
    externalParticipants: external,
    // Incoming, never answered by a person, not handled by the AI agent and not forwarded,
    // whatever the status string says (missed, no-answer, abandoned, busy, canceled, or
    // completed with no answer). Forwarded and AI-handled calls are reported separately.
    missed:
      c.direction === 'incoming' &&
      !c.answeredAt &&
      !c.aiHandled &&
      c.status !== 'forwarded' &&
      !c.forwardedTo &&
      !['queued', 'initiated', 'ringing', 'in-progress'].includes(c.status),
    answeredBy: c.answeredBy,
    aiHandled: c.aiHandled,
    durationSec: c.duration,
    createdAt: c.createdAt,
    summary:
      c.summary?.status === 'completed'
        ? { title: c.summary.title, untrustedSummary: c.summary.summary, untrustedNextSteps: c.summary.nextSteps }
        : c.summary
          ? { status: c.summary.status }
          : undefined,
    voicemail:
      c.voicemail == null
        ? undefined
        : c.voicemail.status === 'completed'
          ? { durationSec: c.voicemail.duration, untrustedTranscript: c.voicemail.transcript, recordingUrl: c.voicemail.recordingUrl }
          : { status: c.voicemail.status },
  }
}

export type QuoTools = ReturnType<typeof createQuoTools>
