import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useTask } from '@/hooks/queries/useTasks'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { TraceTimeline } from '@/components/common/TraceTimeline'
import { Link } from '@tanstack/react-router'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/tasks/$taskId',
  component: TaskDetailPage,
})

function TaskDetailPage() {
  const { t } = useTranslation('tasks')
  const { taskId } = Route.useParams()
  const { data: task, isLoading } = useTask(taskId)

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  if (!task) {
    return <div className="p-8 text-zinc-400">Task not found</div>
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <Link to="/tasks" className="text-sm text-zinc-400 hover:text-zinc-300">&larr; Back to Tasks</Link>
      </div>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 mb-6">
        <div className="flex items-center gap-4 mb-6">
          <h1 className="text-2xl font-semibold text-zinc-50">{task.title}</h1>
          <TaskStatusBadge status={task.status} />
        </div>
        {task.description && (
          <p className="text-sm text-zinc-300 mb-6">{task.description}</p>
        )}
        <dl className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.status')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{task.status}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.priority')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{task.priority}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.agent')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{task.agent_id || 'Unassigned'}</dd>
          </div>
          {task.progress !== undefined && (
            <div>
              <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('progress')}</dt>
              <dd className="text-sm text-zinc-300 mt-1">{task.progress}%</dd>
            </div>
          )}
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Created</dt>
            <dd className="text-sm text-zinc-300 mt-1">{new Date(task.created_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.updated')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{new Date(task.updated_at).toLocaleString()}</dd>
          </div>
        </dl>
      </div>
      <div>
        <h2 className="text-lg font-medium text-zinc-50 mb-4">Trace</h2>
        <TraceTimeline spans={[]} />
      </div>
    </div>
  )
}
