import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { HealthResponse } from '@/types/entities'

export interface AcnStatusAgent {
  agent_id?: string
  name: string
  status?: string
  agent_status?: string
  node_name?: string
  node_status?: string
  last_agent_heartbeat?: string
}

export interface AcnStatusResponse {
  status?: string
  nodes?: number | unknown[]
  total_agents?: number
  agents?: AcnStatusAgent[]
}

export function useHealth() {
  return useQuery({
    queryKey: qk.health,
    queryFn: () => api<HealthResponse>('/v1/health'),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true,
    retry: false,
  })
}

export function useAcnStatus() {
  return useQuery({
    queryKey: qk.acn.status,
    queryFn: () => api<AcnStatusResponse>('/v1/acn/status'),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    retry: false,
  })
}
