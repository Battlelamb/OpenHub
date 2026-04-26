import { http, HttpResponse, type HttpHandler } from 'msw'

export const locksHandlers: HttpHandler[] = [
  // Real backend: GET /v1/locks/ returns ResourceLock[] (added in Plan 04-10).
  http.get('/v1/locks/', () =>
    HttpResponse.json([
      {
        resource_id: 'repo/main',
        agent_id: 'agent-1',
        acquired_at: new Date(Date.now() - 30_000).toISOString(),
        expires_at: new Date(Date.now() + 270_000).toISOString(),
        conflict: false,
      },
    ]),
  ),
]
