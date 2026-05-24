import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useAcnStatus, useHealth, type AcnStatusResponse } from '@/hooks/queries/useHealth'
import { useTaskSummary } from '@/hooks/queries/useTasks'
import type { TaskStatus } from '@/types/entities'
import type { ReactNode } from 'react'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/health',
  component: HealthPage,
})

function HealthPage() {
  const { t } = useTranslation('health')
  const { data: health, isLoading: healthLoading, isError: healthError } = useHealth()
  const { data: acn, isLoading: acnLoading, isError: acnError } = useAcnStatus()
  const { data: tasks, isLoading: tasksLoading, isError: tasksError } = useTaskSummary()

  const nodeCount = getNodeCount(acn)
  const agents = acn?.agents ?? []
  const onlineAgents = agents.filter((agent) => (agent.agent_status ?? agent.status) === 'online').length
  const agentNames = agents.map((agent) => agent.name).filter(Boolean)

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-50">{t('title')}</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-400">{t('subtitle')}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <TruthCard title={t('service.title')}>
          <Metric
            label={t('service.status')}
            value={healthLoading ? t('states.loading') : healthError ? t('states.unavailable') : (health?.status ?? t('states.unknown'))}
          />
          <Metric
            label={t('service.database')}
            value={health?.database?.status ? t('service.databaseValue', { status: health.database.status }) : t('states.unknown')}
          />
          {health?.version ? <Metric label={t('service.version')} value={health.version} /> : null}
        </TruthCard>

        <TruthCard title={t('acn.title')}>
          <Metric
            label={t('acn.agents')}
            value={acnLoading ? t('states.loading') : acnError ? t('states.unavailable') : formatCount(onlineAgents, t('acn.onlineAgent'), t('acn.onlineAgents'))}
          />
          <Metric label={t('acn.nodes')} value={formatCount(nodeCount, t('acn.node'), t('acn.nodesPlural'))} />
          <Metric label={t('acn.registry')} value={agentNames.length ? agentNames.join(', ') : t('states.none')} />
        </TruthCard>

        <TruthCard title={t('tasks.title')}>
          <Metric
            label={t('tasks.total')}
            value={tasksLoading ? t('states.loading') : tasksError ? t('states.unavailable') : formatCount(tasks?.total ?? 0, t('tasks.totalTask'), t('tasks.totalTasks'))}
          />
          <StatusCounts counts={tasks?.statusCounts ?? {}} />
        </TruthCard>
      </div>

      <section className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
        <h2 className="text-sm font-medium text-zinc-100">{t('note.title')}</h2>
        <p className="mt-2 text-sm text-zinc-400">{t('note.body')}</p>
      </section>
    </div>
  )
}

function TruthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="rounded-lg border border-zinc-800 bg-zinc-900/80 p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-300">{title}</h2>
      <dl className="mt-4 space-y-3">{children}</dl>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-zinc-50">{value}</dd>
    </div>
  )
}

function StatusCounts({ counts }: { counts: Partial<Record<TaskStatus, number>> }) {
  const statuses: TaskStatus[] = ['running', 'queued', 'claimed', 'completed', 'failed', 'cancelled']
  const visible = statuses.filter((status) => counts[status])

  if (!visible.length) return <Metric label="Statuses" value="None" />

  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-zinc-500">Statuses</dt>
      <dd className="mt-2 flex flex-wrap gap-2">
        {visible.map((status) => (
          <span key={status} className="rounded-full border border-zinc-700 bg-zinc-950 px-2.5 py-1 text-xs font-medium text-zinc-200">
            {counts[status]} {status}
          </span>
        ))}
      </dd>
    </div>
  )
}

function getNodeCount(acn: AcnStatusResponse | undefined) {
  if (!acn) return 0
  if (Array.isArray(acn.nodes)) return acn.nodes.length
  if (typeof acn.nodes === 'number') return acn.nodes
  return 0
}

function formatCount(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`
}
