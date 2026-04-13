import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useAgent } from '@/hooks/queries/useAgents'
import { AgentStatusBadge } from '@/components/common/StatusBadge'
import { Link } from '@tanstack/react-router'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/agents/$agentId',
  component: AgentDetailPage,
})

function AgentDetailPage() {
  const { t } = useTranslation('agents')
  const { agentId } = Route.useParams()
  const { data: agent, isLoading } = useAgent(agentId)

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  if (!agent) {
    return <div className="p-8 text-zinc-400">Agent not found</div>
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <Link to="/agents" className="text-sm text-zinc-400 hover:text-zinc-300">&larr; Back to Agents</Link>
      </div>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex items-center gap-4 mb-6">
          <h1 className="text-2xl font-semibold text-zinc-50">{agent.name}</h1>
          <AgentStatusBadge status={agent.status} />
        </div>
        <dl className="grid gap-4 md:grid-cols-2">
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.status')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{agent.status}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.capabilities')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{agent.capabilities.join(', ')}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.lastSeen')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">{agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleString() : 'Never'}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{t('columns.currentTask')}</dt>
            <dd className="text-sm text-zinc-300 mt-1">
              {agent.current_task_id || '-'}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
