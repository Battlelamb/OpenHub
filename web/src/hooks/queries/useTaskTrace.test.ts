import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useTaskTrace } from './useTaskTrace'
import type { TraceSpan } from '@/types/entities'

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
}

describe('useTaskTrace', () => {
  it('fetches spans for a given task id', async () => {
    const { result } = renderHook(() => useTaskTrace('task-1'), { wrapper: wrap() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    const spans = result.current.data as TraceSpan[]
    expect(Array.isArray(spans)).toBe(true)
    expect(spans.length).toBeGreaterThan(0)
    // msw mock seeds a 'tool' category span first
    expect(spans[0].category).toBe('tool')
    // Shape assertion (compile-time via cast above, runtime on required keys)
    for (const key of ['id', 'name', 'category', 'duration_ms', 'level', 'started_at']) {
      expect(spans[0]).toHaveProperty(key)
    }
  })

  it('is disabled when taskId is undefined', () => {
    const { result } = renderHook(() => useTaskTrace(undefined), { wrapper: wrap() })
    expect(result.current.fetchStatus).toBe('idle')
    expect(result.current.data).toBeUndefined()
  })
})
