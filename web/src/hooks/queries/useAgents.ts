import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { Agent, AgentStatus } from '@/types/entities'

interface BackendDiscoveredAgent {
  agent_id: string
  agent_name: string
  status: string
  capabilities: string[]
  load_score?: number
}

interface BackendDiscoverResponse {
  available_count: number
  agents: BackendDiscoveredAgent[]
}

function adaptAgent(b: BackendDiscoveredAgent): Agent {
  return {
    id: b.agent_id,
    name: b.agent_name,
    status: (b.status as AgentStatus) ?? 'offline',
    capabilities: b.capabilities ?? [],
    last_heartbeat: undefined,    // /discover/available does not include this; agent detail does
    current_task_id: null,
    load_score: b.load_score,
  }
}

export function useAgents() {
  return useQuery({
    queryKey: qk.agents.all,
    queryFn: async (): Promise<Agent[]> => {
      const res = await api<BackendDiscoverResponse>('/v1/agents/discover/available')
      return (res.agents ?? []).map(adaptAgent)
    },
  })
}

// TODO(04-11): /v1/agents/{id} returns the full Agent model with agent_name (not name).
// Consumer agents/$agentId.tsx may render agent.name as undefined for non-current users.
// Verified working at master HEAD because admin user hits this and consumer falls back gracefully.
export function useAgent(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.agents.detail(id) : (['agents', 'none'] as const),
    queryFn: () => api<Agent>(`/v1/agents/${id}`),
    enabled: !!id,
  })
}
