import { createServerFileRoute } from '@tanstack/react-start/server'
import { chat, chatParamsFromRequest, toServerSentEventsResponse } from '@tanstack/ai'
import { anthropicText } from '@tanstack/ai-anthropic'
import { jobTools } from '../../server/job-tools'

export const ServerRoute = createServerFileRoute('/api/assistant').methods({
  POST: async ({ request }) => {
    const params = await chatParamsFromRequest(request)
    const stream = chat({
      adapter: anthropicText('claude-sonnet-5-5'),
      messages: params.messages,
      tools: jobTools,
    })
    return toServerSentEventsResponse(stream)
  },
})
