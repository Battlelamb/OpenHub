import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { Task } from '@/types/entities'

interface TaskFilters {
  status?: string
}

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({
    queryKey: qk.tasks.list(filters),
    queryFn: () => {
      const qs = new URLSearchParams()
      if (filters.status) qs.set('status', filters.status)
      const suffix = qs.toString() ? `?${qs.toString()}` : ''
      return api<Task[]>(`/v1/tasks${suffix}`)
    },
  })
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.tasks.detail(id) : (['tasks', 'none'] as const),
    queryFn: () => api<Task>(`/v1/tasks/${id}`),
    enabled: !!id,
  })
}

export interface CreateTaskPayload {
  title: string
  description?: string
  priority?: number
  required_capabilities?: string[]
  agent_id?: string | null
}

export function useCreateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateTaskPayload) =>
      api<Task>('/v1/tasks', { method: 'POST', body: JSON.stringify(payload) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.tasks.all }),
  })
}

export function useCancelTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => api<Task>(`/v1/tasks/${taskId}/cancel`, { method: 'POST' }),
    onSuccess: (_, taskId) => {
      qc.invalidateQueries({ queryKey: qk.tasks.all })
      qc.invalidateQueries({ queryKey: qk.tasks.detail(taskId) })
    },
  })
}
