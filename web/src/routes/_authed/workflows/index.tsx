import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useWorkflows } from '@/hooks/queries/useWorkflows'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import { Link } from '@tanstack/react-router'
import type { Workflow } from '@/types/entities'

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    queued: 'text-zinc-400',
    running: 'text-sky-400',
    completed: 'text-emerald-500',
    failed: 'text-red-500',
    cancelled: 'text-zinc-500',
  }
  return colors[status] || 'text-zinc-400'
}

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/workflows',
  component: WorkflowsPage,
})

function WorkflowsPage() {
  const { t } = useTranslation('workflows')
  const { data: workflows, isLoading } = useWorkflows()

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-zinc-50 mb-6">{t('title')}</h1>
      {workflows && workflows.length > 0 ? (
        <ResponsiveList>
          <ResponsiveList.Header>
            <tr>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.name')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.status')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.steps')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.updated')}</th>
            </tr>
          </ResponsiveList.Header>
          {workflows.map((workflow: Workflow) => (
            <ResponsiveList.Row key={workflow.id}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <Link to="/workflows/$workflowId" params={{ workflowId: workflow.id }} className="text-emerald-400 hover:text-emerald-300">
                  {workflow.name}
                </Link>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className={`text-sm font-medium ${getStatusColor(workflow.status)}`}>{workflow.status}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-300">{workflow.steps.length} steps</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-400">{new Date(workflow.updated_at).toLocaleString()}</span>
              </ResponsiveList.Cell>
            </ResponsiveList.Row>
          ))}
        </ResponsiveList>
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8">
          <h2 className="text-lg font-medium text-zinc-50">{t('emptyHeading')}</h2>
          <p className="text-sm text-zinc-400 mt-2">{t('emptyBody')}</p>
        </div>
      )}
    </div>
  )
}
