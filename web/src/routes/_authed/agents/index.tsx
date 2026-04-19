import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useAgents } from '@/hooks/queries/useAgents'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import { AgentStatusBadge } from '@/components/common/StatusBadge'
import { Link } from '@tanstack/react-router'
import type { Agent } from '@/types/entities'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/agents',
  component: AgentsPage,
})

function AgentsPage() {
  const { t } = useTranslation('agents')
  const { data: agents, isLoading } = useAgents()

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-zinc-50 mb-6">{t('title')}</h1>
      {agents && agents.length > 0 ? (
        <ResponsiveList>
          <ResponsiveList.Header>
            <tr>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.name')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.status')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.capabilities')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.lastSeen')}</th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">{t('columns.currentTask')}</th>
            </tr>
          </ResponsiveList.Header>
          {agents.map((agent: Agent) => (
            <ResponsiveList.Row key={agent.id}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <Link to="/agents/$agentId" params={{ agentId: agent.id }} className="text-emerald-400 hover:text-emerald-300">
                  {agent.name}
                </Link>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <AgentStatusBadge status={agent.status} />
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-300">{agent.capabilities.join(', ')}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-400">{agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleString() : 'Never'}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="text-sm text-zinc-400">{agent.current_task_id || '-'}</span>
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
