import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { DlqItem } from '@/types/entities'

export function useDlq() {
  return useQuery({
    queryKey: qk.dlq,
    queryFn: () => api<DlqItem[]>('/v1/dlq'),
  })
}

export function useRetryDlq() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => api(`/v1/dlq/${taskId}/retry`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dlq }),
  })
}
