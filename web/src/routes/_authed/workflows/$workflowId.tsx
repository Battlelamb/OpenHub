import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useWorkflow } from '@/hooks/queries/useWorkflows'
import { Link } from '@tanstack/react-router'

function getStepStatusColor(status: string) {
  const colors: Record<string, string> = {
    pending: 'text-zinc-400',
    running: 'text-sky-400',
    completed: 'text-emerald-500',
    failed: 'text-red-500',
    skipped: 'text-zinc-500',
  }
  return colors[status] || 'text-zinc-400'
}

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/workflows/$workflowId',
  component: WorkflowDetailPage,
})

function WorkflowDetailPage() {
  const { t } = useTranslation('workflows')
  const { workflowId } = Route.useParams()
  const { data: workflow, isLoading } = useWorkflow(workflowId)

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  if (!workflow) {
    return <div className="p-8 text-zinc-400">Workflow not found</div>
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <Link to="/workflows" className="text-sm text-zinc-400 hover:text-zinc-300">&larr; Back to Workflows</Link>
      </div>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h1 className="text-2xl font-semibold text-zinc-50 mb-4">{workflow.name}</h1>
        <div className="mb-6">
          <span className={`text-sm font-medium ${getStepStatusColor(workflow.status)}`}>Status: {workflow.status}</span>
        </div>
        <h2 className="text-lg font-medium text-zinc-50 mb-4">{t('steps')}</h2>
        <div className="space-y-3">
          {workflow.steps.map((step, index) => (
            <div key={step.id} className="flex items-center gap-4 rounded-md border border-zinc-800 bg-zinc-950 p-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-sm font-medium text-zinc-300">
                {index + 1}
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-zinc-50">{step.name}</h3>
                {step.started_at && (
                  <p className="text-xs text-zinc-400 mt-1">
                    Started: {new Date(step.started_at).toLocaleString()}
                    {step.completed_at && ` • Completed: ${new Date(step.completed_at).toLocaleString()}`}
                  </p>
                )}
              </div>
              <span className={`text-sm font-medium ${getStepStatusColor(step.status)}`}>{step.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
