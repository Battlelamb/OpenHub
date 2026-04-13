import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useTasks, useCancelTask } from '@/hooks/queries/useTasks'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { TaskCreateForm } from '@/components/forms/TaskCreateForm'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Link } from '@tanstack/react-router'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/tasks',
  component: TasksPage,
})

function TasksPage() {
  const { t } = useTranslation('tasks')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [cancelTaskId, setCancelTaskId] = useState<string | null>(null)
  
  const { data: tasks, isLoading } = useTasks(statusFilter !== 'all' ? { status: statusFilter } : {})
  const cancelTask = useCancelTask()

  const handleCancel = async () => {
    if (cancelTaskId) {
      await cancelTask.mutateAsync(cancelTaskId)
      setCancelTaskId(null)
    }
  }

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-zinc-50">{t('title')}</h1>
        <div className="flex items-center gap-4">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filterAll')}</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="claimed">Claimed</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          <TaskCreateForm />
        </div>
      </div>
      {tasks && tasks.length > 0 ? (
        <ResponsiveList>
          <ResponsiveList.Header>
            <tr>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.title')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.status')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.agent')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.priority')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.updated')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">Actions</th>
            </tr>
          </ResponsiveList.Header>
          {tasks.map((task) => (
            <ResponsiveList.Row key={task.id}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <Link to="/tasks/$taskId" params={{ taskId: task.id }} className="text-emerald-400 hover:text-emerald-300">
                  {task.title}
                </Link>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <TaskStatusBadge status={task.status} />
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-400">{task.agent_id || '-'}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-400">{task.priority}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-400">{new Date(task.updated_at).toLocaleString()}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                {task.status === 'running' && (
                  <Button variant="destructive" size="sm" onClick={() => setCancelTaskId(task.id)}>
                    {t('cancelCta')}
                  </Button>
                )}
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
      <AlertDialog open={!!cancelTaskId} onOpenChange={() => setCancelTaskId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('cancelCta')}</AlertDialogTitle>
            <AlertDialogDescription>{t('cancelConfirmBody')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancelConfirmBack')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleCancel}>Continue</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
