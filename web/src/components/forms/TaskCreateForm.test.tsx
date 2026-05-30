import { beforeAll, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import '@/i18n'
import { server } from '@/mocks/server'
import { TaskCreateForm } from './TaskCreateForm'

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={qc}>
      {ui}
    </QueryClientProvider>
  )
}

beforeAll(() => {
  if (!HTMLElement.prototype.hasPointerCapture) {
    HTMLElement.prototype.hasPointerCapture = () => false
  }
  if (!HTMLElement.prototype.setPointerCapture) {
    HTMLElement.prototype.setPointerCapture = () => undefined
  }
  if (!HTMLElement.prototype.releasePointerCapture) {
    HTMLElement.prototype.releasePointerCapture = () => undefined
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => undefined
  }
})

describe('TaskCreateForm', () => {
  it('opens the agent picker without crashing when no agent is selected', async () => {
    server.use(
      http.get('/v1/acn/status', () => HttpResponse.json({ total_agents: 0, agents: [] }))
    )

    renderWithQuery(<TaskCreateForm />)

    await userEvent.click(screen.getByRole('button', { name: 'Create task' }))
    await userEvent.click(screen.getByRole('combobox', { name: 'Agent' }))

    expect(await screen.findByRole('option', { name: 'Any agent' })).toBeInTheDocument()
  })

  it('submits a backend-valid task payload for any-agent tasks', async () => {
    let postedBody: Record<string, unknown> | undefined
    server.use(
      http.get('/v1/acn/status', () => HttpResponse.json({ total_agents: 0, agents: [] })),
      http.post('/v1/tasks/', async ({ request }) => {
        postedBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({
          id: 'task-new',
          title: postedBody.title,
          description: postedBody.description,
          status: 'queued',
          priority: postedBody.priority,
          assigned_agent_id: null,
          requested_capabilities: postedBody.required_capabilities,
          input_data: {},
          output_data: null,
          last_error: null,
          created_at: '2026-05-30T07:00:00Z',
          updated_at: '2026-05-30T07:00:00Z',
        })
      })
    )

    renderWithQuery(<TaskCreateForm />)

    await userEvent.click(screen.getByRole('button', { name: 'Create task' }))
    await userEvent.type(screen.getByLabelText('Title'), 'Fix live create task')
    await userEvent.type(screen.getByLabelText('Description'), 'Regression smoke for task creation')
    await userEvent.click(screen.getByRole('button', { name: 'Dispatch task' }))

    expect(postedBody).toMatchObject({
      title: 'Fix live create task',
      description: 'Regression smoke for task creation',
      priority: 3,
      required_capabilities: ['general'],
    })
    expect(postedBody).not.toHaveProperty('agent_id')
  })
})
