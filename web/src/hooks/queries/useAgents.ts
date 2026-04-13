import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { Agent } from '@/types/entities'

export function useAgents() {
  return useQuery({
    queryKey: qk.agents.all,
    queryFn: () => api<Agent[]>('/v1/agents'),
  })
}

export function useAgent(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.agents.detail(id) : (['agents', 'none'] as const),
    queryFn: () => api<Agent>(`/v1/agents/${id}`),
    enabled: !!id,
  })
}
