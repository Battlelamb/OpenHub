import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { Link } from '@tanstack/react-router'
import { SemanticSearchPanel } from '@/components/common/SemanticSearchPanel'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/',
  component: DashboardPage,
})

function DashboardPage() {
  const { t } = useTranslation(['common', 'nav'])
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-zinc-50 mb-6">{t('common:brand')} Dashboard</h1>
      <SemanticSearchPanel />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Link to="/agents" className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 hover:bg-zinc-800">
          <h2 className="text-lg font-medium text-zinc-50">{t('nav:items.agents')}</h2>
          <p className="text-sm text-zinc-400 mt-1">View and manage connected agents</p>
        </Link>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="text-lg font-medium text-zinc-50">{t('nav:items.tasks')}</h2>
          <p className="text-sm text-zinc-400 mt-1">Coming soon</p>
        </div>
        <Link to="/workflows" className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 hover:bg-zinc-800">
          <h2 className="text-lg font-medium text-zinc-50">{t('nav:items.workflows')}</h2>
          <p className="text-sm text-zinc-400 mt-1">Monitor workflow execution</p>
        </Link>
      </div>
    </div>
  )
}
