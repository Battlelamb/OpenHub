import { http, HttpResponse, type HttpHandler } from 'msw'

export const workflowsHandlers: HttpHandler[] = [
  http.get('/v1/workflows', () =>
    HttpResponse.json([
      {
        id: 'wf-1',
        name: 'Code Review Pipeline',
        status: 'running',
        steps: [
          { id: 'step-1', name: 'Lint', status: 'completed', started_at: new Date().toISOString(), completed_at: new Date().toISOString() },
          { id: 'step-2', name: 'Test', status: 'running', started_at: new Date().toISOString() },
          { id: 'step-3', name: 'Deploy', status: 'pending' },
        ],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]),
  ),
  http.get('/v1/workflows/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      name: 'Code Review Pipeline',
      status: 'running',
      steps: [
        { id: 'step-1', name: 'Lint', status: 'completed', started_at: new Date().toISOString(), completed_at: new Date().toISOString() },
        { id: 'step-2', name: 'Test', status: 'running', started_at: new Date().toISOString() },
        { id: 'step-3', name: 'Deploy', status: 'pending' },
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
]
