import { fetchServerSentEvents, useChat } from '@tanstack/ai-react'

export function AssistantPanel() {
  const chat = useChat({ connection: fetchServerSentEvents('/api/assistant') })
  return <aside aria-label="Assistant">{chat.messages.length} messages</aside>
}
