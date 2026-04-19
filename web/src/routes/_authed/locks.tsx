import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useLocks } from '@/hooks/queries/useLocks'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import type { ResourceLock } from '@/types/entities'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/locks',
  component: LocksPage,
})

function LocksPage() {
  const { t } = useTranslation(['locks', 'common'])
  const { data: items = [], isLoading } = useLocks()

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
                {t('columns.resource')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.agent')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.acquired')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.expires')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.conflict')}
              </th>
            </tr>
          </ResponsiveList.Header>
          {items.map((l: ResourceLock) => (
            <ResponsiveList.Row key={l.resource_id}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-sm text-zinc-50">
                  {l.resource_id}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-sm text-zinc-300">
                  {l.agent_id}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-xs text-zinc-400">
                  {l.acquired_at}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-xs text-zinc-400">
                  {l.expires_at}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                {l.conflict ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400">
                    WARN
                  </span>
                ) : (
                  <span className="text-xs text-zinc-500">-</span>
                )}
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
