import { http, HttpResponse, type HttpHandler } from 'msw'

export const costsHandlers: HttpHandler[] = [
  // Real backend path with the {per_agent: [...]} envelope.
  http.get('/v1/costs/summary', () =>
    HttpResponse.json({
      period_days: 7,
      total_cost_usd: 12.345,
      total_input_tokens: 100_000,
      total_output_tokens: 30_000,
      per_agent: [
        {
          agent_name: 'claude-code',
          total_cost_usd: 8.91,
          input_tokens: 70_000,
          output_tokens: 20_000,
          api_calls: 42,
        },
        {
          agent_name: 'cursor',
          total_cost_usd: 3.435,
          input_tokens: 30_000,
          output_tokens: 10_000,
          api_calls: 18,
        },
      ],
    }),
  ),
]
