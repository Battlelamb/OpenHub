import { http, HttpResponse, type HttpHandler } from 'msw'

const sampleTaskResponse = (id: string) => ({
  id,
  title: 'Code review for PR #123',
  description: 'Review the changes in the authentication module',
  status: 'running',
  priority: 3,
  assigned_agent_id: 'agent-1',
  requested_capabilities: ['code', 'review'],
  input_data: {},
  output_data: null,
  last_error: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
})

export const tasksHandlers: HttpHandler[] = [
  // Real backend path: search returns paginated envelope.
  http.get('/v1/tasks/search', ({ request }) => {
    const url = new URL(request.url)
    const limit = Number(url.searchParams.get('limit') ?? 100)
    return HttpResponse.json({
      tasks: [
        sampleTaskResponse('task-1'),
        { ...sampleTaskResponse('task-2'), title: 'Write unit tests', status: 'queued', priority: 2, assigned_agent_id: null },
      ],
      total: 2,
      page: 1,
      limit,
    })
  }),
  // Per-task trace - MUST stay BEFORE the bare :id handler (msw insertion-order match).
  // Preserved from 04-09 (UI-12 distributed trace viewer).
  http.get('/v1/tasks/:id/trace', ({ params }) =>
    HttpResponse.json([
      {
        id: `${params.id}-span-1`,
        name: 'read_file(app/config.py)',
        category: 'tool',
        duration_ms: 12.4,
        level: 0,
        started_at: new Date(Date.now() - 5_000).toISOString(),
      },
      {
        id: `${params.id}-span-2`,
        name: 'claude-3-opus completion',
        category: 'llm',
        duration_ms: 842.1,
        level: 1,
        started_at: new Date(Date.now() - 4_800).toISOString(),
      },
      {
        id: `${params.id}-span-3`,
        name: 'write_file(app/main.py)',
        category: 'tool',
        duration_ms: 5.2,
        level: 1,
        started_at: new Date(Date.now() - 3_900).toISOString(),
      },
    ]),
  ),
  // Detail by id (single TaskResponse envelope - matches real backend).
  http.get('/v1/tasks/:id', ({ params }) =>
    HttpResponse.json(sampleTaskResponse(String(params.id))),
  ),
  // Trailing slash on POST. Real backend declares POST /v1/tasks/ (routes_tasks.py:69).
  http.post('/v1/tasks/', async ({ request }) => {
    const body = await request.json() as { title: string; description?: string; priority?: number }
    return HttpResponse.json({
      ...sampleTaskResponse('task-new'),
      ...body,
      assigned_agent_id: null,
      status: 'queued',
    })
  }),
  http.post('/v1/tasks/:id/cancel', () =>
    HttpResponse.json({ status: 'cancelled', message: 'Task cancelled successfully' }),
  ),
]
