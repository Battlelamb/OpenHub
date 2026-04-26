import { http, HttpResponse, type HttpHandler } from 'msw'

export const memoryHandlers: HttpHandler[] = [
  // Real backend path with the {keys: [...], total} envelope.
  http.get('/v1/memory/keys', () =>
    HttpResponse.json({
      keys: [
        {
          key: 'shared/onboarding-notes',
          value_type: 'text',
          tags: ['team', 'onboarding'],
          created_by: 'agent-1',
          updated_at: new Date(Date.now() - 5 * 60_000).toISOString(),
        },
        {
          key: 'cache/last-pr-summary',
          value_type: 'json',
          tags: ['cache'],
          created_by: 'agent-2',
          updated_at: new Date(Date.now() - 90 * 60_000).toISOString(),
        },
      ],
      total: 2,
    }),
  ),
]
