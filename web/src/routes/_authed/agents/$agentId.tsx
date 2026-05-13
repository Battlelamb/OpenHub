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
            <dd className="text-sm text-zinc-300 mt-1">
              <div className="flex flex-wrap gap-2">
                {agent.capabilities.map(cap => (
                  <span key={cap} className="px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
                    {cap}
                  </span>
                ))}
              </div>
            </dd>
          </div>
          {agent.mcp_profiles && agent.mcp_profiles.length > 0 && (
            <div className="md:col-span-2">
              <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">MCP Tools</dt>
              <dd className="text-sm text-zinc-300 mt-1 flex flex-wrap gap-2">
                {agent.mcp_profiles.map(mcp => (
                  <span key={mcp} className="px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    {mcp}
                  </span>
                ))}
              </dd>
            </div>
          )}
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
          <div className="md:col-span-2">
            <dt className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Connection Info</dt>
            <dd className="text-sm text-zinc-300 mt-1 space-y-1">
              {agent.node_name && (
                <div><span className="text-zinc-500">Node:</span> {agent.node_name}</div>
              )}
              {agent.status === 'offline' && agent.offline_reason && (
                <div className="text-amber-400/90 mt-2 p-3 bg-amber-500/10 rounded-md border border-amber-500/20">
                  <span className="block font-medium mb-1">Offline Reason:</span>
                  {agent.offline_reason === 'stale_agent_heartbeat' 
                    ? `The agent process hasn't sent a heartbeat recently. The underlying node (${agent.node_name || 'unknown'}) might still be running, but this specific agent is unresponsive.`
                    : agent.offline_reason.replaceAll('_', ' ')}
                </div>
              )}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
