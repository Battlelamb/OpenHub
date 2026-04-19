import { http, HttpResponse, type HttpHandler } from 'msw'

export const dlqHandlers: HttpHandler[] = [
  http.get('/v1/dlq', () => HttpResponse.json([])),
  http.post('/v1/dlq/:id/retry', () => HttpResponse.json({ ok: true })),
]
