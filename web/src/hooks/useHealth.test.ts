import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import React from 'react'
import { server } from '@/mocks/server'
import { useHealth } from './queries/useHealth'

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
}

describe('useHealth', () => {
  it('fetches /v1/health and returns status', async () => {
    server.use(http.get('/v1/health', () => HttpResponse.json({ status: 'ok', version: 'test' })))
    const { result } = renderHook(() => useHealth(), { wrapper: wrap() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('ok')
  })
})
