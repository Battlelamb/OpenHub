import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { Task, TaskStatus, TaskPriority } from '@/types/entities'

interface TaskFilters {
  status?: string
}

interface BackendTaskResponse {
  id: string
  title: string
  description?: string
  status: string
  priority: number
  assigned_agent_id?: string | null
  requested_capabilities?: string[]
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  last_error?: string
  created_at: string
  updated_at: string
}

interface BackendTaskSearchResponse {
  tasks: BackendTaskResponse[]
  total: number
  page: number
  limit: number
}

function adaptTask(b: BackendTaskResponse): Task {
  return {
    id: b.id,
    title: b.title,
    description: b.description,
    status: (b.status as TaskStatus) ?? 'queued',
    priority: (b.priority as TaskPriority) ?? 3,
    agent_id: b.assigned_agent_id ?? null,
    required_capabilities: b.requested_capabilities ?? [],
    result: b.output_data,
    error: b.last_error,
    created_at: b.created_at,
    updated_at: b.updated_at,
  }
}

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({
    queryKey: qk.tasks.list(filters),
    queryFn: async (): Promise<Task[]> => {
      const qs = new URLSearchParams()
      // TODO(04-11): real pagination UI. For now, hardcode page 1 limit 100.
      qs.set('page', '1')
      qs.set('limit', '100')
      if (filters.status) qs.set('status', filters.status)
      const res = await api<BackendTaskSearchResponse>(`/v1/tasks/search?${qs.toString()}`)
      return (res.tasks ?? []).map(adaptTask)
    },
  })
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.tasks.detail(id) : (['tasks', 'none'] as const),
    queryFn: async (): Promise<Task> => {
      const b = await api<BackendTaskResponse>(`/v1/tasks/${id}`)
      return adaptTask(b)
    },
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
    mutationFn: async (payload: CreateTaskPayload): Promise<Task> => {
      // Trailing slash to avoid FastAPI 307 redirect
      const b = await api<BackendTaskResponse>('/v1/tasks/', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      return adaptTask(b)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.tasks.all }),
  })
}

export function useCancelTask() {
  const qc = useQueryClient()
  return useMutation({
    // /v1/tasks/{id}/cancel returns {status, message}, not the full task. We invalidate to refetch.
    mutationFn: (taskId: string) => api(`/v1/tasks/${taskId}/cancel`, { method: 'POST' }),
    onSuccess: (_, taskId) => {
      qc.invalidateQueries({ queryKey: qk.tasks.all })
      qc.invalidateQueries({ queryKey: qk.tasks.detail(taskId) })
    },
  })
}

export function useTransitionTaskStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ taskId, status }: { taskId: string; status: TaskStatus }): Promise<Task> => {
      const b = await api<BackendTaskResponse>(`/v1/tasks/${taskId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      return adaptTask(b)
    },
    onSuccess: (task) => {
      qc.invalidateQueries({ queryKey: qk.tasks.all })
      qc.invalidateQueries({ queryKey: qk.tasks.detail(task.id) })
    },
  })
}
