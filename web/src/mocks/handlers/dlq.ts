import { http, HttpResponse, type HttpHandler } from 'msw'

export const dlqHandlers: HttpHandler[] = [
  // Real backend: GET /v1/dlq/ returns {dead_letters:[...], total}.
  http.get('/v1/dlq/', () =>
    HttpResponse.json({
      dead_letters: [
        {
          task_id: 'failed-task-1',
          title: 'Compile broken module',
          task_type: 'feature',
          priority: 3,
          retry_count: 3,
          max_retries: 3,
          last_error: 'TypeError: foo is not callable',
          assigned_to: 'agent-1',
          created_at: new Date(Date.now() - 60_000).toISOString(),
        },
      ],
      total: 1,
    }),
  ),
  http.post('/v1/dlq/:id/retry', () =>
    HttpResponse.json({ status: 'requeued', task_id: 'failed-task-1' }),
  ),
]
