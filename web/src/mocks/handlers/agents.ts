import { http, HttpResponse } from 'msw'

export const agentsHandlers = [
  http.get('/v1/agents', () =>
    HttpResponse.json([
      {
        id: 'agent-1',
        name: 'claude-code',
        status: 'online',
        capabilities: ['code', 'test', 'debug'],
        last_heartbeat: new Date().toISOString(),
        current_task_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]),
  ),
  http.get('/v1/agents/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      name: 'claude-code',
      status: 'online',
      capabilities: ['code', 'test', 'debug'],
      last_heartbeat: new Date().toISOString(),
      current_task_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
]
