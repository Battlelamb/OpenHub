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

interface BackendAcnAgent {
  agent_id?: string
  name: string
  status: string
  agent_status?: string
  capabilities?: string[]
  node_id?: string
  node_name?: string
  node_status?: string
  last_heartbeat?: string
  last_agent_heartbeat?: string
  last_node_heartbeat?: string
  offline_reason?: string | null
  mcp_profiles?: string[]
}

interface BackendAcnStatusResponse {
  total_agents: number
  agents: BackendAcnAgent[]
}

function coerceStatus(status: string | undefined): AgentStatus {
  return status === 'online' || status === 'idle' || status === 'error' ? status : 'offline'
}

function adaptDiscoveredAgent(b: BackendDiscoveredAgent): Agent {
  return {
    id: b.agent_id,
    name: b.agent_name,
    status: coerceStatus(b.status),
    capabilities: b.capabilities ?? [],
    last_heartbeat: undefined,    // /discover/available does not include this; agent detail does
    current_task_id: null,
    load_score: b.load_score,
  }
}

function adaptAcnAgent(b: BackendAcnAgent): Agent {
  return {
    id: b.agent_id ?? b.name,
    name: b.name,
    status: coerceStatus(b.agent_status ?? b.status),
    agent_status: coerceStatus(b.agent_status ?? b.status),
    capabilities: b.capabilities ?? [],
    last_heartbeat: b.last_agent_heartbeat ?? b.last_heartbeat,
    last_agent_heartbeat: b.last_agent_heartbeat ?? b.last_heartbeat,
    current_task_id: null,
    node_id: b.node_id,
    node_name: b.node_name,
    node_status: coerceStatus(b.node_status),
    last_node_heartbeat: b.last_node_heartbeat,
    offline_reason: b.offline_reason,
    mcp_profiles: b.mcp_profiles ?? [],
  }
}

export function useAgents() {
  return useQuery({
    queryKey: qk.agents.all,
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    queryFn: async (): Promise<Agent[]> => {
      try {
        const acn = await api<BackendAcnStatusResponse>('/v1/acn/status')
        if (acn.agents?.length) return acn.agents.map(adaptAcnAgent)
      } catch {
        // Fall through to legacy discovery for older/self-hosted deployments.
      }

      // Legacy fallback for older/self-hosted deployments without ACN status.
      const res = await api<BackendDiscoverResponse>('/v1/agents/discover/available')
      return (res.agents ?? []).map(adaptDiscoveredAgent)
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
