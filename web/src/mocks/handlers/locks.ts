import { http, HttpResponse } from 'msw'

export const locksHandlers = [
  http.get('/v1/locks', () =>
    HttpResponse.json([
      {
        resource_id: 'resource-1',
        agent_id: 'agent-1',
        acquired_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      },
    ]),
  ),
]
