import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import React from 'react'
import { server } from '@/mocks/server'
import { Toaster } from '@/components/ui/sonner'
import { KanbanBoard } from './KanbanBoard'

const dndState = vi.hoisted(() => ({
  dropResult: {
    draggableId: 'task-queued',
    source: { droppableId: 'queued', index: 0 },
    destination: { droppableId: 'cancelled', index: 0 },
  },
}))

const routerState = vi.hoisted(() => ({
  navigate: vi.fn(),
}))

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    useNavigate: () => routerState.navigate,
  }
})

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children, onDragEnd }: { children: React.ReactNode; onDragEnd: (result: unknown) => void }) => (
    <div>
      <button type="button" onClick={() => onDragEnd(dndState.dropResult)}>
        simulate drop
      </button>
      {children}
    </div>
  ),
  Droppable: ({
    children,
    droppableId,
  }: {
    children: (provided: unknown, snapshot: unknown) => React.ReactNode
    droppableId: string
  }) => (
    <section data-testid={`column-${droppableId}`}>
      {children(
        { innerRef: vi.fn(), droppableProps: {} },
        { isDraggingOver: false }
      )}
    </section>
  ),
  Draggable: ({
    children,
    draggableId,
  }: {
    children: (provided: unknown, snapshot: unknown) => React.ReactNode
    draggableId: string
  }) => (
    <article data-testid={`card-${draggableId}`}>
      {children(
        { innerRef: vi.fn(), draggableProps: {}, dragHandleProps: {} },
        { isDragging: false }
      )}
    </article>
  ),
}))

vi.mock('@/components/forms/TaskCreateForm', () => ({
  TaskCreateForm: () => <button type="button">Create task</button>,
}))

vi.mock('@/components/canvas/WorkflowCanvas', () => ({
  WorkflowCanvas: ({ task, open }: { task: { title: string }; open: boolean }) =>
    open ? <div role="dialog">Workflow canvas for {task.title}</div> : null,
}))

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
      <Toaster />
    </QueryClientProvider>
  )
}

function mockTasks() {
  server.use(
    http.get('/v1/tasks/search', () =>
      HttpResponse.json({
        tasks: [
          {
            id: 'task-queued',
            title: 'Queued task',
            description: 'Waiting for work',
            status: 'queued',
            priority: 1,
            assigned_agent_id: null,
            requested_capabilities: ['python'],
            created_at: '2026-05-21T10:00:00Z',
            updated_at: '2026-05-21T10:00:00Z',
          },
          {
            id: 'task-waiting-approval',
            title: 'Waiting approval task',
            description: 'Agent claim needs verification',
            status: 'waiting_approval',
            priority: 2,
            assigned_agent_id: null,
            requested_capabilities: ['review'],
            created_at: '2026-05-21T10:00:00Z',
            updated_at: '2026-05-21T10:06:00Z',
          },
          {
            id: 'task-cancelled',
            title: 'Cancelled task',
            description: 'Stopped by admin',
            status: 'cancelled',
            priority: 3,
            assigned_agent_id: null,
            requested_capabilities: [],
            created_at: '2026-05-21T10:00:00Z',
            updated_at: '2026-05-21T10:05:00Z',
          },
        ],
        total: 3,
        page: 1,
        limit: 100,
      })
    )
  )
}

describe('KanbanBoard', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    dndState.dropResult = {
      draggableId: 'task-queued',
      source: { droppableId: 'queued', index: 0 },
      destination: { droppableId: 'cancelled', index: 0 },
    }
    routerState.navigate.mockClear()
  })

  it('renders all lifecycle columns including cancelled and groups task cards by status', async () => {
    mockTasks()

    renderWithQuery(<KanbanBoard />)

    expect(await screen.findByRole('heading', { name: 'Tasks' })).toBeInTheDocument()
    for (const column of ['Queued', 'Claimed', 'Running', 'Waiting approval', 'Completed', 'Failed', 'Cancelled']) {
      expect(screen.getByText(column)).toBeInTheDocument()
    }
    expect(screen.getByText('Queued task')).toBeInTheDocument()
    expect(screen.getByText('Waiting approval task')).toBeInTheDocument()
    expect(screen.getByText('Cancelled task')).toBeInTheDocument()
    expect(screen.getByTestId('column-waiting_approval')).toContainElement(screen.getByText('Waiting approval task'))
    expect(screen.getByTestId('column-cancelled')).toContainElement(screen.getByText('Cancelled task'))
  })

  it('navigates to the task detail route when a task card is clicked', async () => {
    mockTasks()

    renderWithQuery(<KanbanBoard />)

    await userEvent.click(await screen.findByText('Queued task'))

    expect(routerState.navigate).toHaveBeenCalledWith({
      to: '/tasks/$taskId',
      params: { taskId: 'task-queued' },
    })
  })

  it('calls the status transition API and shows an updating state while a drag-drop mutation is pending', async () => {
    mockTasks()
    let patchCalled = false
    server.use(
      http.patch('/v1/tasks/task-queued/status', async ({ request }) => {
        patchCalled = true
        const body = (await request.json()) as { status: string }
        expect(body.status).toBe('cancelled')
        await new Promise((resolve) => setTimeout(resolve, 50))
        return HttpResponse.json({
          id: 'task-queued',
          title: 'Queued task',
          description: 'Waiting for work',
          status: 'cancelled',
          priority: 1,
          assigned_agent_id: null,
          requested_capabilities: ['python'],
          created_at: '2026-05-21T10:00:00Z',
          updated_at: '2026-05-21T10:10:00Z',
        })
      })
    )

    renderWithQuery(<KanbanBoard />)

    await screen.findByText('Queued task')
    await userEvent.click(screen.getByRole('button', { name: 'simulate drop' }))

    expect(await screen.findByText('Updating status')).toBeInTheDocument()
    await waitFor(() => expect(patchCalled).toBe(true))
  })

  it('shows backend transition errors as toast text', async () => {
    mockTasks()
    dndState.dropResult = {
      draggableId: 'task-queued',
      source: { droppableId: 'queued', index: 0 },
      destination: { droppableId: 'completed', index: 0 },
    }
    server.use(
      http.patch('/v1/tasks/task-queued/status', () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Conflict',
            status: 409,
            detail: "Transition 'queued' → 'completed' is not allowed.",
          },
          { status: 409 }
        )
      )
    )

    renderWithQuery(<KanbanBoard />)

    await screen.findByText('Queued task')
    await userEvent.click(screen.getByRole('button', { name: 'simulate drop' }))

    expect(await screen.findByText('Conflict')).toBeInTheDocument()
    expect(screen.getByText("Transition 'queued' → 'completed' is not allowed.")).toBeInTheDocument()
  })
})
