import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import '@/i18n'
import { Route } from './health'

const HealthRouteComponent = Route.options.component as React.ComponentType

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('HealthPage truth dashboard', () => {
  it('separates service health from ACN and task truth', async () => {
    server.use(
      http.get('/v1/health', () =>
        HttpResponse.json({
          status: 'healthy',
          version: '0.1.0',
          agents: { connected: 0, max_allowed: 100 },
          tasks: { active: 0, queued: 0, max_concurrent: 50 },
          database: { status: 'ready' },
        }),
      ),
      http.get('/v1/acn/status', () =>
        HttpResponse.json({
          status: 'healthy',
          nodes: 1,
          total_agents: 1,
          agents: [
            {
              agent_id: 'agent-brunhilde',
              name: 'brunhilde',
              status: 'online',
              agent_status: 'online',
              node_name: 'brunhilde-vps',
              node_status: 'online',
              last_agent_heartbeat: '2026-05-24T20:00:00Z',
            },
          ],
        }),
      ),
      http.get('/v1/tasks/search', () =>
        HttpResponse.json({
          total: 3,
          page: 1,
          limit: 100,
          tasks: [
            {
              id: 'task-running',
              title: 'Running task',
              status: 'running',
              priority: 2,
              assigned_agent_id: 'agent-brunhilde',
              requested_capabilities: [],
              created_at: '2026-05-24T20:00:00Z',
              updated_at: '2026-05-24T20:01:00Z',
            },
            {
              id: 'task-queued',
              title: 'Queued task',
              status: 'queued',
              priority: 3,
              assigned_agent_id: null,
              requested_capabilities: [],
              created_at: '2026-05-24T20:02:00Z',
              updated_at: '2026-05-24T20:03:00Z',
            },
            {
              id: 'task-completed',
              title: 'Completed task',
              status: 'completed',
              priority: 4,
              assigned_agent_id: 'agent-brunhilde',
              requested_capabilities: [],
              created_at: '2026-05-24T20:04:00Z',
              updated_at: '2026-05-24T20:05:00Z',
            },
          ],
        }),
      ),
    )

    renderWithQuery(<HealthRouteComponent />)

    expect(await screen.findByRole('heading', { name: 'Health' })).toBeInTheDocument()

    const service = await screen.findByRole('region', { name: /service health/i })
    expect(within(service).getByText('healthy')).toBeInTheDocument()
    expect(within(service).getByText('Database: ready')).toBeInTheDocument()

    const acn = await screen.findByRole('region', { name: /acn registry truth/i })
    expect(within(acn).getByText('1 online agent')).toBeInTheDocument()
    expect(within(acn).getByText('1 node')).toBeInTheDocument()
    expect(within(acn).getByText('brunhilde')).toBeInTheDocument()

    const tasks = await screen.findByRole('region', { name: /task truth/i })
    expect(within(tasks).getByText('3 total tasks')).toBeInTheDocument()
    expect(within(tasks).getByText('1 running')).toBeInTheDocument()
    expect(within(tasks).getByText('1 queued')).toBeInTheDocument()
    expect(within(tasks).getByText('1 completed')).toBeInTheDocument()

    expect(screen.queryByText(/"connected"/)).not.toBeInTheDocument()
    expect(screen.queryByText(/"active"/)).not.toBeInTheDocument()
  })
})
