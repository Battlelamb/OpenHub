import { http, HttpResponse, type HttpHandler } from 'msw'

export const agentsHandlers: HttpHandler[] = [
  // Real backend path. Returns {available_count, agents:[{agent_id, agent_name, status, capabilities, load_score}]}
  http.get('/v1/agents/discover/available', () =>
    HttpResponse.json({
      available_count: 2,
      agents: [
        {
          agent_id: 'agent-1',
          agent_name: 'claude-code',
          status: 'online',
          capabilities: ['code', 'test', 'debug'],
          load_score: 0.2,
        },
        {
          agent_id: 'agent-2',
          agent_name: 'cursor',
          status: 'idle',
          capabilities: ['edit', 'review'],
          load_score: 0.0,
        },
      ],
    }),
  ),
  // Detail endpoint - keeps the old shape for now (admin access).
  http.get('/v1/agents/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      agent_name: 'claude-code',
      status: 'online',
      capabilities: ['code', 'test', 'debug'],
      last_heartbeat: new Date().toISOString(),
      current_task_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  ),
]
