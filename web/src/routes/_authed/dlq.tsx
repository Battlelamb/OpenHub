import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useDlq, useRetryDlq } from '@/hooks/queries/useDlq'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/dlq',
  component: DlqPage,
})

function DlqPage() {
  const { t } = useTranslation(['dlq', 'common'])
  const { data: items = [], isLoading } = useDlq()
  const retry = useRetryDlq()

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold text-zinc-50">{t('title')}</h1>
      {items.length > 0 ? (
        <ResponsiveList>
          <ResponsiveList.Header>
            <tr>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.title')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.error')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.retries')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.failedAt')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {' '}
              </th>
            </tr>
          </ResponsiveList.Header>
          {items.map((i) => (
            <ResponsiveList.Row key={i.task_id}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-50">{i.title}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-xs text-red-400">{i.error}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="tabular-nums text-sm text-zinc-400">
                  {i.retries}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-xs text-zinc-400">
                  {i.failed_at}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button size="sm">{t('retryCta')}</Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{t('retryCta')}</AlertDialogTitle>
                      <AlertDialogDescription>
                        {t('retryConfirmBody')}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => retry.mutate(i.task_id)}
                      >
                        {t('retryCta')}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </ResponsiveList.Cell>
            </ResponsiveList.Row>
          ))}
        </ResponsiveList>
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8 text-center">
          <div className="text-lg font-semibold text-zinc-50">
            {t('emptyHeading')}
          </div>
          <div className="mt-2 text-sm text-zinc-400">{t('emptyBody')}</div>
        </div>
      )}
    </div>
  )
}
