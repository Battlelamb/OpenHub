import { http, HttpResponse } from 'msw'

export const costsHandlers = [
  http.get('/v1/costs', () =>
    HttpResponse.json([
      {
        agent_id: 'agent-1',
        agent_name: 'claude-code',
        total_tokens: 10000,
        total_cost_usd: 0.50,
        task_count: 5,
      },
    ]),
  ),
]
