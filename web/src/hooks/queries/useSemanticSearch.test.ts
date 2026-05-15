import { describe, expect, it } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import React from 'react'
import { server } from '@/mocks/server'
import { useSemanticSearch } from './useSemanticSearch'

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
}

describe('useSemanticSearch', () => {
  it('posts a trimmed semantic query for agent and task hits', async () => {
    let captured: unknown = null
    server.use(
      http.post('/v1/search', async ({ request }) => {
        captured = await request.json()
        return HttpResponse.json({
          query: 'vector routing',
          total: 2,
          hits: [
            { entity_type: 'agent', id: 'agent-1', content: 'Agent: Router', distance: 0.12 },
            { entity_type: 'task', id: 'task-1', content: 'Route vector work', distance: 0.2 },
          ],
        })
      }),
    )

    const { result } = renderHook(() => useSemanticSearch('  vector routing  '), { wrapper: wrap() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(captured).toEqual({ query: 'vector routing', types: ['agent', 'task'], top_k: 8 })
    expect(result.current.data?.hits[0]).toMatchObject({ entity_type: 'agent', id: 'agent-1' })
  })

  it('stays idle for short queries', () => {
    const { result } = renderHook(() => useSemanticSearch('x'), { wrapper: wrap() })

    expect(result.current.fetchStatus).toBe('idle')
    expect(result.current.data).toBeUndefined()
  })
})
