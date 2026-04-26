import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { DlqItem } from '@/types/entities'

interface BackendDlqRow {
  task_id: string
  title: string
  task_type?: string
  priority?: number
  retry_count?: number
  max_retries?: number
  last_error?: string
  assigned_to?: string
  created_at?: string
}

interface BackendDlqResponse {
  dead_letters: BackendDlqRow[]
  total: number
}

function adaptDlq(b: BackendDlqRow): DlqItem {
  return {
    task_id: b.task_id,
    title: b.title,
    failed_at: b.created_at ?? '',
    error: b.last_error ?? '',
    retries: b.retry_count ?? 0,
    task_type: b.task_type,
    priority: b.priority,
    max_retries: b.max_retries,
    assigned_to: b.assigned_to,
  }
}

export function useDlq() {
  return useQuery({
    queryKey: qk.dlq,
    queryFn: async (): Promise<DlqItem[]> => {
      // Trailing slash: backend declares the route as @dlq_router.get("/").
      const res = await api<BackendDlqResponse>('/v1/dlq/')
      return (res.dead_letters ?? []).map(adaptDlq)
    },
  })
}

export function useRetryDlq() {
  const qc = useQueryClient()
  return useMutation({
    // Backend route: @dlq_router.post("/{task_id}/retry"). Auth: JWT admin (added in Plan 04-10 Task 1).
    mutationFn: (taskId: string) => api(`/v1/dlq/${taskId}/retry`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dlq }),
  })
}
