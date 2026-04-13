import { http, HttpResponse } from 'msw'

export const workflowsHandlers = [
  http.get('/v1/workflows', () => HttpResponse.json([])),
  http.get('/v1/workflows/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      name: 'Test Workflow',
      status: 'running',
      steps: [
        {
          id: 'step-1',
          name: 'Step 1',
          status: 'completed',
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        },
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
]
