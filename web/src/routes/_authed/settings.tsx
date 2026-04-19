import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'
import { useTranslation } from 'react-i18next'
import { useUIStore } from '@/stores/ui-store'
import { Button } from '@/components/ui/button'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/settings',
  component: SettingsPage,
})

function SettingsPage() {
  const { t, i18n } = useTranslation(['settings', 'common'])
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)
  const setLanguage = useUIStore((s) => s.setLanguage)

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold text-zinc-50">
        {t('settings:title')}
      </h1>
      <div className="flex flex-col gap-3">
        <Button onClick={toggleTheme}>
          {theme === 'dark'
            ? t('common:themeToLight')
            : t('common:themeToDark')}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            const next = i18n.language === 'tr' ? 'en' : 'tr'
            setLanguage(next)
            i18n.changeLanguage(next)
          }}
        >
          {t('common:language')}: {i18n.language.toUpperCase()}
        </Button>
      </div>
    </div>
  )
}
