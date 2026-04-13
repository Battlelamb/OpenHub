import { http, HttpResponse, type HttpHandler } from 'msw'

export const agentsHandlers: HttpHandler[] = [
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
      {
        id: 'agent-2',
        name: 'cursor',
        status: 'idle',
        capabilities: ['edit', 'review'],
        last_heartbeat: new Date().toISOString(),
        current_task_id: 'task-1',
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
