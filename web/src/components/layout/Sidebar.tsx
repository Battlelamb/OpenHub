import { Link, useLocation } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { useUIStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'
import {
  Users,
  ListChecks,
  GitBranch,
  AlertCircle,
  DollarSign,
  Activity,
  Database,
  Lock,
  Heart,
  Settings as SettingsIcon,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'

interface NavItem {
  to: string
  key: string
  icon: React.ComponentType<{ className?: string }>
}

interface NavGroup {
  labelKey: string
  items: NavItem[]
}

const groups: NavGroup[] = [
  {
    labelKey: 'nav:groups.operations',
    items: [
      { to: '/agents', key: 'nav:items.agents', icon: Users },
      { to: '/tasks', key: 'nav:items.tasks', icon: ListChecks },
      { to: '/workflows', key: 'nav:items.workflows', icon: GitBranch },
    ],
  },
  {
    labelKey: 'nav:groups.visibility',
    items: [
      { to: '/dlq', key: 'nav:items.dlq', icon: AlertCircle },
      { to: '/costs', key: 'nav:items.costs', icon: DollarSign },
      { to: '/traces', key: 'nav:items.traces', icon: Activity },
      { to: '/memory', key: 'nav:items.memory', icon: Database },
      { to: '/locks', key: 'nav:items.locks', icon: Lock },
    ],
  },
  {
    labelKey: 'nav:groups.admin',
    items: [
      { to: '/health', key: 'nav:items.health', icon: Heart },
      { to: '/settings', key: 'nav:items.settings', icon: SettingsIcon },
    ],
  },
]

export function Sidebar() {
  const { t } = useTranslation(['nav', 'common'])
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const location = useLocation()

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col border-r border-zinc-800 bg-zinc-900 transition-all duration-200',
        collapsed ? 'w-14' : 'w-64',
      )}
      aria-label="Primary navigation"
    >
      <div className="flex h-14 items-center justify-between px-3 border-b border-zinc-800">
        {!collapsed && (
          <span className="text-sm font-semibold text-emerald-500">{t('common:brand')}</span>
        )}
        <button
          type="button"
          onClick={toggleSidebar}
          className="ml-auto rounded p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-50"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {groups.map((group) => (
          <div key={group.labelKey} className="px-2 py-2">
            {!collapsed && (
              <div className="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
                {t(group.labelKey)}
              </div>
            )}
            <ul className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = location.pathname.startsWith(item.to)
                const Icon = item.icon
                return (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className={cn(
                        'flex h-9 items-center gap-2 rounded-md px-2 text-sm transition-colors',
                        active
                          ? 'border-l-2 border-emerald-500 bg-zinc-800 text-zinc-50'
                          : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-50',
                      )}
                    >
                      <Icon className={cn('size-5', active && 'text-emerald-500')} />
                      {!collapsed && <span>{t(item.key)}</span>}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  )
}
