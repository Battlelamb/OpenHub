import { http, HttpResponse } from 'msw'

export const settingsHandlers = [
  http.get('/v1/settings', () =>
    HttpResponse.json({
      theme: 'dark',
      language: 'en',
    }),
  ),
]
