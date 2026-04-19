import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useCosts } from '@/hooks/queries/useCosts'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import type { CostItem } from '@/types/entities'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/costs',
  component: CostsPage,
})

function CostsPage() {
  const { t } = useTranslation(['costs', 'common'])
  const { data: items = [], isLoading } = useCosts()

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
                {t('columns.agent')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.tokens')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.cost')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.tasks')}
              </th>
            </tr>
          </ResponsiveList.Header>
          {items.map((c: CostItem) => (
            <ResponsiveList.Row key={c.agent_id}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-50">{c.agent_name}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono tabular-nums text-sm text-zinc-300">
                  {c.total_tokens.toLocaleString()}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono tabular-nums text-sm text-zinc-300">
                  ${c.total_cost_usd.toFixed(2)}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="tabular-nums text-sm text-zinc-400">
                  {c.task_count}
                </span>
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
