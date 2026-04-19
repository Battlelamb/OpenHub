import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useTask } from '@/hooks/queries/useTasks'
import { useTaskTrace } from '@/hooks/queries/useTaskTrace'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { TraceTimeline } from '@/components/common/TraceTimeline'
import { ApiError } from '@/lib/api-client'
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
        <TraceSection taskId={taskId} />
      </div>
    </div>
  )
}

function TraceSection({ taskId }: { taskId: string }) {
  const { t } = useTranslation('tasks')
  const { data, isLoading, error } = useTaskTrace(taskId)

  if (isLoading) {
    return (
      <div aria-label={t('trace.loading')} className="space-y-2">
        <div className="h-6 w-2/3 rounded bg-zinc-800 animate-pulse" />
        <div className="h-6 w-1/2 rounded bg-zinc-800 animate-pulse" />
        <div className="h-6 w-3/4 rounded bg-zinc-800 animate-pulse" />
      </div>
    )
  }

  if (error) {
    const title = error instanceof ApiError ? error.problem.title : t('trace.errorTitle')
    const detail = error instanceof ApiError ? error.problem.detail : String(error)
    return (
      <div role="alert" className="rounded-lg border border-red-500/50 bg-red-500/10 p-4">
        <div className="text-sm font-medium text-red-400">{title}</div>
        {detail ? <div className="text-xs text-red-400/80 mt-1">{detail}</div> : null}
      </div>
    )
  }

  // When data is undefined (disabled or idle) or empty, TraceTimeline renders
  // its own empty state using the same i18n copy keys.
  return <TraceTimeline spans={data ?? []} />
}
