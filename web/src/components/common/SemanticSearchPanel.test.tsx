import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import React from 'react'
import { server } from '@/mocks/server'
import { SemanticSearchPanel } from './SemanticSearchPanel'

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => <a href={to}>{children}</a>,
}))

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('SemanticSearchPanel', () => {
  it('renders semantic agent and task search results', async () => {
    server.use(
      http.post('/v1/search', () =>
        HttpResponse.json({
          query: 'routing',
          total: 2,
          hits: [
            { entity_type: 'agent', id: 'agent-1', content: 'Agent: Router', distance: 0.1234 },
            { entity_type: 'task', id: 'task-1', content: 'Route vector work', distance: 0.2345 },
          ],
        }),
      ),
    )

    renderWithQuery(<SemanticSearchPanel />)

    await userEvent.type(screen.getByLabelText('Semantic memory query'), 'routing')
    await userEvent.click(screen.getByRole('button', { name: /search memory/i }))

    await waitFor(() => expect(screen.getByText('Agent: Router')).toBeInTheDocument())
    expect(screen.getByText('Route vector work')).toBeInTheDocument()
    expect(screen.getByText('2 results for “routing”')).toBeInTheDocument()
  })
})
