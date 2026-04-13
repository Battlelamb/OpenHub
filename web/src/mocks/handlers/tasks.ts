import { http, HttpResponse, type HttpHandler } from 'msw'

export const tasksHandlers: HttpHandler[] = [
  http.get('/v1/tasks', () =>
    HttpResponse.json([
      {
        id: 'task-1',
        title: 'Code review for PR #123',
        description: 'Review the changes in the authentication module',
        status: 'running',
        priority: 3,
        agent_id: 'agent-1',
        required_capabilities: ['code', 'review'],
        progress: 45,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 'task-2',
        title: 'Write unit tests',
        description: 'Add tests for the new API endpoints',
        status: 'queued',
        priority: 2,
        agent_id: null,
        required_capabilities: ['test'],
        progress: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]),
  ),
  http.get('/v1/tasks/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      title: 'Code review for PR #123',
      description: 'Review the changes in the authentication module',
      status: 'running',
      priority: 3,
      agent_id: 'agent-1',
      required_capabilities: ['code', 'review'],
      progress: 45,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
  http.post('/v1/tasks', async ({ request }) => {
    const body = await request.json() as { title: string; description?: string; priority?: number }
    return HttpResponse.json({
      ...body,
      id: 'task-new',
      status: 'queued',
      agent_id: null,
      progress: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }),
  http.post('/v1/tasks/:id/cancel', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      title: 'Cancelled task',
      description: 'This task was cancelled',
      status: 'cancelled',
      priority: 3,
      agent_id: 'agent-1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
]
