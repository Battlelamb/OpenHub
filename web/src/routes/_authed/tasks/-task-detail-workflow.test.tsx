import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { TaskWorkflowDetail } from './$taskId'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    Link: ({ children }: { children: React.ReactNode }) => <a href="/tasks">{children}</a>,
  }
})

vi.mock('@/components/canvas/WorkflowCanvas', () => ({
  WorkflowCanvas: ({ task, mode }: { task: { title: string }; mode?: string }) => (
    <section data-testid="workflow-canvas" data-mode={mode}>
      Workflow canvas for {task.title}
    </section>
  ),
}))

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('TaskWorkflowDetail', () => {
  it('renders the selected task as an embedded workflow canvas workspace', async () => {
    server.use(
      http.get('/v1/tasks/task-workflow', () =>
        HttpResponse.json({
          id: 'task-workflow',
          title: 'Workflow-ready task',
          description: 'Needs the canvas on the detail route',
          status: 'running',
          priority: 2,
          assigned_agent_id: 'brunhilde',
          requested_capabilities: ['typescript'],
          created_at: '2026-05-21T10:00:00Z',
          updated_at: '2026-05-21T10:05:00Z',
        })
      )
    )

    renderWithQuery(<TaskWorkflowDetail taskId="task-workflow" />)

    expect(await screen.findByRole('heading', { name: 'Workflow-ready task' })).toBeInTheDocument()
    expect(screen.getByTestId('workflow-canvas')).toHaveAttribute('data-mode', 'embedded')
    expect(screen.getByTestId('workflow-canvas')).toHaveTextContent('Workflow canvas for Workflow-ready task')
    expect(screen.queryByText('Task Details')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Trace' })).not.toBeInTheDocument()
  })
})
