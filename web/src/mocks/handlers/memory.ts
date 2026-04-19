import { http, HttpResponse, type HttpHandler } from 'msw'

export const memoryHandlers: HttpHandler[] = [
  http.get('/v1/memory', () => HttpResponse.json([])),
]
