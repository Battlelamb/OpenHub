import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { TraceSpan } from '@/types/entities'

/**
 * UI-12: fetch the distributed trace for a task as an array of TraceSpan objects.
 * Backend endpoint: GET /v1/tasks/{task_id}/trace (see app/api/routes_tasks.py).
 * Returns [] when the task has no spans yet; TraceTimeline renders its own empty state.
 *
 * No WebSocket merge is currently wired for trace spans - useQuery's staleTime / refetch
 * on remount is sufficient for v1. Spans are additive and rarely mutated after write.
 */
export function useTaskTrace(taskId: string | undefined) {
  return useQuery({
    queryKey: taskId ? qk.tasks.trace(taskId) : (['tasks', 'none', 'trace'] as const),
    queryFn: () => api<TraceSpan[]>(`/v1/tasks/${taskId}/trace`),
    enabled: !!taskId,
  })
}
