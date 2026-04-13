import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { Workflow } from '@/types/entities'

export function useWorkflows() {
  return useQuery({
    queryKey: qk.workflows.all,
    queryFn: () => api<Workflow[]>('/v1/workflows'),
  })
}

export function useWorkflow(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.workflows.detail(id) : (['workflows', 'none'] as const),
    queryFn: () => api<Workflow>(`/v1/workflows/${id}`),
    enabled: !!id,
  })
}
