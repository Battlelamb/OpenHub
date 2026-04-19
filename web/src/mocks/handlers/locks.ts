import { http, HttpResponse, type HttpHandler } from 'msw'

export const locksHandlers: HttpHandler[] = [
  http.get('/v1/locks', () => HttpResponse.json([])),
]
