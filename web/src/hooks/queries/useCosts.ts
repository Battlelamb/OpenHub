import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { CostItem } from '@/types/entities'

interface BackendCostPerAgent {
  agent_name: string
  total_cost_usd: number
  input_tokens: number
  output_tokens: number
  api_calls: number
}

interface BackendCostSummary {
  period_days: number
  total_cost_usd: number
  total_input_tokens: number
  total_output_tokens: number
  per_agent: BackendCostPerAgent[]
}

function adaptCost(b: BackendCostPerAgent): CostItem {
  return {
    // Backend per_agent does not surface agent_id. agent_name is the join key.
    // Consumer (costs.tsx) uses agent_id only as a React key. Falling back to agent_name
    // is safe because agent_name is unique per agent (Agent.agent_name has unique constraint).
    agent_id: b.agent_name,
    agent_name: b.agent_name,
    total_tokens: (b.input_tokens ?? 0) + (b.output_tokens ?? 0),
    total_cost_usd: b.total_cost_usd ?? 0,
    task_count: b.api_calls ?? 0,
  }
}

export function useCosts() {
  return useQuery({
    queryKey: qk.costs,
    queryFn: async (): Promise<CostItem[]> => {
      const res = await api<BackendCostSummary>('/v1/costs/summary?days=7')
      return (res.per_agent ?? []).map(adaptCost)
    },
  })
}
