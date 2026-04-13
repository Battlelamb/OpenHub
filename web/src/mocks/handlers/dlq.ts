import { http, HttpResponse } from 'msw'

export const dlqHandlers = [
  http.get('/v1/dlq', () => HttpResponse.json([])),
  http.post('/v1/dlq/:id/retry', ({ params }) =>
    HttpResponse.json({
      task_id: params.id,
      title: 'Retried Task',
      failed_at: new Date().toISOString(),
      error: 'Previous error',
      retries: 1,
    }),
  ),
]
