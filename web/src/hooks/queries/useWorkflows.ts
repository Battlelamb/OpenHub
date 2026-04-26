import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { Workflow, WorkflowStep } from '@/types/entities'

interface BackendWorkflowResponse {
  run_id: string
  name: string
  status: string
  created_at: string
  created_by?: string
  progress: { steps?: WorkflowStep[] } & Record<string, unknown>
  input_data: Record<string, unknown>
}

function adaptWorkflow(b: BackendWorkflowResponse): Workflow {
  return {
    id: b.run_id,
    name: b.name,
    status: (b.status as Workflow['status']) ?? 'queued',
    steps: (b.progress && Array.isArray(b.progress.steps)) ? b.progress.steps : [],
    created_at: b.created_at,
    // Backend WorkflowResponse does not include updated_at; consumer requires a string
    // for `new Date(updated_at).toLocaleString()`. Fall back to created_at to keep the
    // consumer untouched per Plan 04-10 minimal-change rule.
    updated_at: b.created_at,
  }
}

export function useWorkflows() {
  return useQuery({
    queryKey: qk.workflows.all,
    queryFn: async (): Promise<Workflow[]> => {
      const res = await api<BackendWorkflowResponse[]>('/v1/workflows/')
      return (res ?? []).map(adaptWorkflow)
    },
  })
}

export function useWorkflow(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.workflows.detail(id) : (['workflows', 'none'] as const),
    queryFn: async (): Promise<Workflow> => {
      const b = await api<BackendWorkflowResponse>(`/v1/workflows/${id}`)
      return adaptWorkflow(b)
    },
    enabled: !!id,
  })
}
