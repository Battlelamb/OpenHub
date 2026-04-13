import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TraceTimeline } from './TraceTimeline'

describe('TraceTimeline', () => {
  it('renders empty state when no spans', () => {
    render(<TraceTimeline spans={[]} />)
    expect(screen.getByText('No trace available')).toBeInTheDocument()
  })

  it('renders spans with correct structure', () => {
    const spans = [
      { id: '1', name: 'LLM call', category: 'llm' as const, duration_ms: 100, level: 0, started_at: new Date().toISOString() },
    ]
    render(<TraceTimeline spans={spans} />)
    expect(screen.getByText('LLM call')).toBeInTheDocument()
    expect(screen.getByText('100ms')).toBeInTheDocument()
  })
})
