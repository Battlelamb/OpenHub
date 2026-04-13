import { http, HttpResponse } from 'msw'

export const tasksHandlers = [
  http.get('/v1/tasks', () => HttpResponse.json([])),
  http.get('/v1/tasks/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      title: 'Test Task',
      description: 'A test task',
      status: 'queued',
      priority: 3,
      agent_id: null,
      required_capabilities: ['code'],
      progress: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
  http.post('/v1/tasks', async ({ request }) => {
    const body = await request.json() as { title: string; description?: string; priority?: number }
    return HttpResponse.json({
      id: 'task-new',
      title: body.title,
      description: body.description,
      status: 'queued',
      priority: body.priority || 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }),
  http.post('/v1/tasks/:id/cancel', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      title: 'Cancelled Task',
      status: 'cancelled',
      priority: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
]
