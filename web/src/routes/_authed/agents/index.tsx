import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { useTranslation } from 'react-i18next'
import { useAgents } from '@/hooks/queries/useAgents'
import { AgentStatusBadge } from '@/components/common/StatusBadge'
import { Link } from '@tanstack/react-router'
import type { Agent } from '@/types/entities'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/agents',
  component: AgentsPage,
})

function formatHeartbeat(value?: string): { label: string; tone: string } {
  if (!value) return { label: 'No heartbeat yet', tone: 'text-zinc-500' }

  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return { label: 'Heartbeat unknown', tone: 'text-zinc-500' }

  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000))
  if (seconds < 60) return { label: `${seconds}s ago`, tone: 'text-emerald-400' }

  const minutes = Math.floor(seconds / 60)
  if (minutes < 5) return { label: `${minutes}m ago`, tone: 'text-emerald-400' }
  if (minutes < 30) return { label: `${minutes}m ago`, tone: 'text-amber-400' }

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return { label: `${hours}h ago`, tone: 'text-red-400' }

  const days = Math.floor(hours / 24)
  return { label: `${days}d ago`, tone: 'text-red-400' }
}

function AgentCard({ agent }: { agent: Agent }) {
  const heartbeat = formatHeartbeat(agent.last_agent_heartbeat ?? agent.last_heartbeat)
  const nodeHeartbeat = formatHeartbeat(agent.last_node_heartbeat)
  const capabilityPreview = agent.capabilities.slice(0, 6)
  const extraCapabilities = Math.max(0, agent.capabilities.length - capabilityPreview.length)
  const mcpProfiles = agent.mcp_profiles ?? []
  const presenceNote = agent.offline_reason
    ? agent.offline_reason === 'stale_agent_heartbeat'
      ? `No agent heartbeat within TTL. Node ${agent.node_name ?? 'unknown'} may still be online.`
      : agent.offline_reason.replaceAll('_', ' ')
    : agent.node_status === 'online' && agent.status === 'offline'
      ? `Node ${agent.node_name ?? 'unknown'} is online, but this agent is not connected.`
      : 'Agent heartbeat is current.'

  return (
    <Link
      to="/agents/$agentId"
      params={{ agentId: agent.id }}
      className="group rounded-xl border border-zinc-800 bg-zinc-950/70 p-5 shadow-sm transition hover:border-emerald-500/60 hover:bg-zinc-900/80"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-lg font-semibold text-zinc-50 group-hover:text-emerald-300">{agent.name}</h2>
            <AgentStatusBadge status={agent.status} />
          </div>
          <p className="mt-1 truncate text-xs text-zinc-500">{agent.id}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-xs text-zinc-400">
          {agent.node_name ?? 'unknown node'} · {agent.node_status ?? 'unknown'}
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-zinc-800 bg-black/20 p-3">
          <div className="text-xs uppercase tracking-wide text-zinc-500">Agent heartbeat</div>
          <div className={`mt-1 text-sm font-medium ${heartbeat.tone}`}>{heartbeat.label}</div>
          <div className="mt-1 truncate text-xs text-zinc-600">{agent.last_agent_heartbeat ?? agent.last_heartbeat ?? 'waiting for first signal'}</div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-black/20 p-3">
          <div className="text-xs uppercase tracking-wide text-zinc-500">Node heartbeat</div>
          <div className={`mt-1 text-sm font-medium ${nodeHeartbeat.tone}`}>{nodeHeartbeat.label}</div>
          <div className="mt-1 truncate text-xs text-zinc-600">{agent.last_node_heartbeat ?? 'waiting for node signal'}</div>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-zinc-800 bg-black/20 p-3 text-xs text-zinc-400">
        {presenceNote}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {capabilityPreview.length > 0 ? (
          capabilityPreview.map((capability) => (
            <span key={capability} className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-300">
              {capability}
            </span>
          ))
        ) : (
          <span className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-500">no capabilities reported</span>
        )}
        {extraCapabilities > 0 && (
          <span className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-500">+{extraCapabilities}</span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {mcpProfiles.length > 0 ? (
          mcpProfiles.map((profile) => (
            <span key={profile} className="rounded-full border border-violet-900/60 bg-violet-950/40 px-2 py-1 text-xs text-violet-200">
              MCP: {profile}
            </span>
          ))
        ) : (
          <span className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-500">no MCP profiles reported</span>
        )}
      </div>
    </Link>
  )
}

function AgentsPage() {
  const { t } = useTranslation('agents')
  const { data: agents, isLoading } = useAgents()

  if (isLoading) {
    return <div className="p-8 text-zinc-400">{t('common:loading')}...</div>
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">{t('title')}</h1>
          <p className="mt-1 text-sm text-zinc-500">Live ACN registry snapshot. Cached for 30 seconds; refreshes on focus.</p>
        </div>
        <div className="text-sm text-zinc-400">{agents?.length ?? 0} registered</div>
      </div>

      {agents && agents.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {agents.map((agent: Agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8">
          <h2 className="text-lg font-medium text-zinc-50">{t('emptyHeading')}</h2>
          <p className="mt-2 text-sm text-zinc-400">{t('emptyBody')}</p>
        </div>
      )}
    </div>
  )
}
