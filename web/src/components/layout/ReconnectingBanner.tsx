import { useTranslation } from 'react-i18next'
import { useUIStore } from '@/stores/ui-store'
import { Loader2 } from 'lucide-react'

export function ReconnectingBanner() {
  const { t } = useTranslation('common')
  const wsStatus = useUIStore((s) => s.wsStatus)
  if (wsStatus !== 'reconnecting') return null
  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400"
    >
      <Loader2 className="size-3 animate-spin" />
      <span>{t('reconnecting')}</span>
    </div>
  )
}
