import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useHealth } from '@/hooks/queries/useHealth'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/health',
  component: HealthPage,
})

function HealthPage() {
  const { t } = useTranslation('health')
  const { data } = useHealth()
  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold text-zinc-50">{t('title')}</h1>
      <pre className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4 font-mono text-xs text-zinc-50">
        {JSON.stringify(data ?? { status: 'unknown' }, null, 2)}
      </pre>
    </div>
  )
}
