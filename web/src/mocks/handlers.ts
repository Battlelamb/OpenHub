import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/v1/health', () =>
    HttpResponse.json({ status: 'ok', version: 'test' }),
  ),
  http.post('/v1/auth/login', async () =>
    HttpResponse.json({
      access_token: 'fake.jwt.token',
      refresh_token: 'fake.refresh.token',
      expires_in: 900,
      user: { id: 'u1', name: 'admin', role: 'admin' },
    }),
  ),
  http.get('/v1/agents', () => HttpResponse.json([])),
  http.get('/v1/tasks', () => HttpResponse.json([])),
  http.get('/v1/workflows', () => HttpResponse.json([])),
]
