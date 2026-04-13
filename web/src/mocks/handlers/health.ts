import { http, HttpResponse } from 'msw'

export const healthHandlers = [
  http.get('/v1/health', () =>
    HttpResponse.json({
      status: 'ok',
      version: '0.1.0',
      uptime_seconds: 3600,
    }),
  ),
]
