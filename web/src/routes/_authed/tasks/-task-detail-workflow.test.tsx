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
          task_type: 'feature',
          priority: 2,
          assigned_agent_id: 'brunhilde',
          requested_capabilities: ['typescript'],
          created_at: '2026-05-21T10:00:00Z',
          updated_at: '2026-05-21T10:05:00Z',
          created_by: 'system-seed',
          completed_at: null,
          retry_count: 1,
          max_retries: 3,
          last_error: null,
        })
      )
    )

    renderWithQuery(<TaskWorkflowDetail taskId="task-workflow" />)

    expect(await screen.findByRole('heading', { name: 'Workflow-ready task' })).toBeInTheDocument()
    expect(screen.getByTestId('workflow-canvas')).toHaveAttribute('data-mode', 'embedded')
    expect(screen.getByTestId('workflow-canvas')).toHaveTextContent('Workflow canvas for Workflow-ready task')
    expect(screen.getByRole('heading', { name: 'Task Details' })).toBeInTheDocument()
    expect(screen.getByText('Type')).toBeInTheDocument()
    expect(screen.getByText('feature')).toBeInTheDocument()
    expect(screen.getByText('Priority')).toBeInTheDocument()
    expect(screen.getByText('P2')).toBeInTheDocument()
    expect(screen.getByText('Requested capabilities')).toBeInTheDocument()
    expect(screen.getByText('typescript')).toBeInTheDocument()
    expect(screen.getByText('Retry budget')).toBeInTheDocument()
    expect(screen.getByText('1 / 3')).toBeInTheDocument()
    expect(screen.getByText('System info')).toBeInTheDocument()
    expect(screen.getByText('system-seed')).toBeInTheDocument()
    expect(screen.getByText('2026-05-21 10:00 UTC')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Trace' })).not.toBeInTheDocument()
  })
})
