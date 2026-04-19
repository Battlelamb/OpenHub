import { useState } from 'react'
import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useMemoryEntries } from '@/hooks/queries/useMemory'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { JsonViewer } from '@/components/common/JsonViewer'
import { Eye } from 'lucide-react'
import type { MemoryItem } from '@/types/entities'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/memory',
  component: MemoryPage,
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatAge(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

function MemoryPage() {
  const { t } = useTranslation(['memory', 'common'])
  const { data: items = [], isLoading } = useMemoryEntries()
  const [inspecting, setInspecting] = useState<MemoryItem | null>(null)

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
                {t('columns.key')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.size')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t('columns.age')}
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-400">
                {' '}
              </th>
            </tr>
          </ResponsiveList.Header>
          {items.map((m) => (
            <ResponsiveList.Row key={m.key}>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono text-xs text-zinc-50">{m.key}</span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono tabular-nums text-xs text-zinc-400">
                  {formatSize(m.size_bytes)}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <span className="font-mono tabular-nums text-xs text-zinc-400">
                  {formatAge(m.age_seconds)}
                </span>
              </ResponsiveList.Cell>
              <ResponsiveList.Cell header className="py-3 px-4">
                <Button
                  size="icon"
                  variant="ghost"
                  aria-label={t('inspectLabel')}
                  onClick={() => setInspecting(m)}
                >
                  <Eye className="size-4" />
                </Button>
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
      <Sheet
        open={!!inspecting}
        onOpenChange={(open) => !open && setInspecting(null)}
      >
        <SheetContent side="right" className="w-[420px] sm:max-w-[560px]">
          <SheetHeader>
            <SheetTitle className="font-mono text-sm">
              {inspecting?.key}
            </SheetTitle>
          </SheetHeader>
          <div className="mt-4 max-h-[80vh] overflow-auto">
            <JsonViewer value={inspecting?.value_preview ?? null} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
