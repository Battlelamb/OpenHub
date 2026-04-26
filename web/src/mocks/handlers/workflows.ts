import { http, HttpResponse, type HttpHandler } from 'msw'

export const workflowsHandlers: HttpHandler[] = [
  // Real backend: GET /v1/workflows/ returns List[WorkflowResponse] (added in Plan 04-10).
  http.get('/v1/workflows/', () =>
    HttpResponse.json([
      {
        run_id: 'wf-1',
        name: 'Code Review Pipeline',
        status: 'running',
        created_at: new Date().toISOString(),
        created_by: 'agent-1',
        progress: {
          steps: [
            { id: 'step-1', name: 'Lint', status: 'completed', started_at: new Date().toISOString(), completed_at: new Date().toISOString() },
            { id: 'step-2', name: 'Test', status: 'running', started_at: new Date().toISOString() },
            { id: 'step-3', name: 'Deploy', status: 'pending' },
          ],
        },
        input_data: {},
      },
    ]),
  ),
  // Detail by run_id - same shape as the list element.
  http.get('/v1/workflows/:id', ({ params }) =>
    HttpResponse.json({
      run_id: params.id,
      name: 'Code Review Pipeline',
      status: 'running',
      created_at: new Date().toISOString(),
      created_by: 'agent-1',
      progress: {
        steps: [
          { id: 'step-1', name: 'Lint', status: 'completed', started_at: new Date().toISOString(), completed_at: new Date().toISOString() },
          { id: 'step-2', name: 'Test', status: 'running', started_at: new Date().toISOString() },
          { id: 'step-3', name: 'Deploy', status: 'pending' },
        ],
      },
      input_data: {},
    }),
  ),
]
