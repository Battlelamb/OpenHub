import { useTranslation } from 'react-i18next'
import { useUIStore } from '@/stores/ui-store'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ReconnectingBanner } from './ReconnectingBanner'
import { useHealth } from '@/hooks/queries/useHealth'
import { Moon, Sun, Languages, User, LogOut, Heart } from 'lucide-react'

export function Topbar() {
  const { t, i18n } = useTranslation('common')
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)
  const setLanguage = useUIStore((s) => s.setLanguage)
  const { data: health } = useHealth()
  const healthOk = health?.status === 'ok'

  return (
    <header className="flex h-14 items-center gap-4 border-b border-zinc-800 bg-zinc-900 px-4">
      <div className="text-sm font-semibold text-emerald-500">{t('brand')}</div>
      <div className="flex-1">
        <ReconnectingBanner />
      </div>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              aria-label={healthOk ? t('healthOk') : t('healthFail')}
              className={`size-2.5 rounded-full ${healthOk ? 'bg-emerald-500' : 'bg-red-500'}`}
            />
          </TooltipTrigger>
          <TooltipContent>{healthOk ? t('healthOk') : t('healthFail')}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <Button size="icon" variant="ghost" onClick={toggleTheme} aria-label={theme === 'dark' ? t('themeToLight') : t('themeToDark')}>
        {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="icon" variant="ghost" aria-label="User menu">
            <User className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>{t('language')}</DropdownMenuLabel>
          <DropdownMenuItem
            onClick={() => {
              setLanguage('en')
              i18n.changeLanguage('en')
            }}
          >
            <Languages className="mr-2 size-4" /> English
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => {
              setLanguage('tr')
              i18n.changeLanguage('tr')
            }}
          >
            <Languages className="mr-2 size-4" /> Turkce
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <Heart className="mr-2 size-4" /> {t('healthOk')}
          </DropdownMenuItem>
          <DropdownMenuItem>
            <LogOut className="mr-2 size-4" /> {t('signOut')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
