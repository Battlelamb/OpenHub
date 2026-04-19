import { http, HttpResponse, type HttpHandler } from 'msw'

export const costsHandlers: HttpHandler[] = [
  http.get('/v1/costs', () => HttpResponse.json([])),
]
