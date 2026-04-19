import { http, HttpResponse, type HttpHandler } from 'msw'

// /v1/health bootstrap handler lives here (per Plan 04-04 deviation #3).
// Plan 04-06's proposed empty-stub would break useHealth tests and the
// Topbar health dot in dev, so the handler is kept here.
export const healthHandlers: HttpHandler[] = [
  http.get('/v1/health', () =>
    HttpResponse.json({
      status: 'ok',
      version: '0.1.0',
      uptime_seconds: 3600,
    }),
  ),
]
