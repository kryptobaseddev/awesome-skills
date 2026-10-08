/**
 * send-approval.example.tsx: approval UI for quo_send_message / quo_schedule_message
 * with @tanstack/ai-react (>= 0.30). It shows what the person is actually approving:
 * sender, every recipient, the final text, segment count, and whether the
 * recipients share a group thread. It also lets them edit the text before
 * approving. Style it with your design system; the structure is what matters.
 *
 * The server re-checks policy inside execute, so this card is a consent gate,
 * not the authorization boundary.
 */
import { useState } from 'react'
import { fetchServerSentEvents, useChat } from '@tanstack/ai-react'
import { estimateSegments, quoToolDefs } from './quo-tool-defs'

// Definitions only (no execute): they type the approval interrupts. The client
// never runs them, and the server route ignores client-declared tools.
const approvalTools = [quoToolDefs.sendMessage, quoToolDefs.scheduleMessage] as const

export function useQuoAssistant() {
  return useChat({ connection: fetchServerSentEvents('/api/quo-assistant'), tools: approvalTools })
}

type Chat = ReturnType<typeof useQuoAssistant>
type Interrupt = Chat['interrupts'][number]
type SendInterrupt = Extract<Interrupt, { kind: 'tool-approval' }>

export function PendingSends({ chat }: { chat: Chat }) {
  const pending = chat.interrupts.filter(
    (i): i is SendInterrupt => i.kind === 'tool-approval',
  )
  if (!pending.length) return null
  return (
    <section aria-label="Messages waiting for your approval">
      {pending.map((i) => (
        <SendCard key={i.id} interrupt={i} disabled={chat.resuming || !i.canResolve} />
      ))}
    </section>
  )
}

/** Approve, optionally with edited text. Narrowing by toolName keeps editedArgs typed per tool. */
function approve(i: SendInterrupt, content?: string) {
  if (i.toolName === 'quo_send_message') {
    return i.resolveInterrupt(true, content === undefined ? undefined : { editedArgs: { ...i.originalArgs, content } })
  }
  return i.resolveInterrupt(true, content === undefined ? undefined : { editedArgs: { ...i.originalArgs, content } })
}

function SendCard({
  interrupt,
  disabled,
}: {
  interrupt: SendInterrupt
  disabled: boolean
}) {
  const args: typeof interrupt.originalArgs & { sendAt?: string } = interrupt.originalArgs
  const [text, setText] = useState(args.content)
  const { segments, encoding } = estimateSegments(text)
  const group = args.to.length > 1

  return (
    <article>
      <h3>{args.sendAt ? `Schedule for ${new Date(args.sendAt).toLocaleString()}` : 'Send now'}</h3>
      <dl>
        <dt>From inbox</dt>
        <dd>{args.fromPhoneNumberId}</dd>
        <dt>To</dt>
        <dd>{args.to.join(', ')}</dd>
      </dl>
      {group && (
        <p role="alert">
          This creates one group thread: all {args.to.length} recipients see each other's numbers and replies.
        </p>
      )}
      <label>
        Message
        <textarea value={text} maxLength={1600} onChange={(e) => setText(e.target.value)} rows={4} />
      </label>
      <p>
        {text.length}/1600 characters · {segments} segment{segments === 1 ? '' : 's'} ({encoding}) · cannot be unsent
      </p>
      <button
        type="button"
        disabled={disabled || !text.trim()}
        onClick={() =>
          approve(interrupt, text === args.content ? undefined : text)
        }
      >
        {args.sendAt ? 'Schedule' : 'Send'}
      </button>
      <button type="button" disabled={disabled} onClick={() => interrupt.resolveInterrupt(false)}>
        Don't send
      </button>
    </article>
  )
}
