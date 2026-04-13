import { http, HttpResponse } from 'msw'

export const memoryHandlers = [
  http.get('/v1/memory', () =>
    HttpResponse.json([
      {
        key: 'test-key',
        size_bytes: 1024,
        age_seconds: 3600,
        value_preview: { data: 'test' },
      },
    ]),
  ),
]
