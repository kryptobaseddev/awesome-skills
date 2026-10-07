// src/router.tsx (current file in the project)
import { createRouter } from '@tanstack/react-router'
import { QueryClient } from '@tanstack/react-query'
import { setupRouterSsrQueryIntegration } from '@tanstack/react-router-ssr-query'
import { routeTree } from './routeTree.gen'

export function getRouter() {
  const queryClient = new QueryClient()
  const router = createRouter({ routeTree, context: { queryClient }, defaultPreload: 'intent', defaultPreloadStaleTime: 0, scrollRestoration: true })
  setupRouterSsrQueryIntegration({ router, queryClient })
  return router
}
