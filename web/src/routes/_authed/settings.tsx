import { createRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Route as parentRoute } from '../_authed'
import { useUIStore } from '@/stores/ui-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError, createAgentInvite, type AgentInviteResponse } from '@/lib/api-client'

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
  const [invite, setInvite] = useState<AgentInviteResponse | null>(null)
  const [isCreatingInvite, setIsCreatingInvite] = useState(false)

  const handleCreateInvite = async () => {
    setIsCreatingInvite(true)
    try {
      const nextInvite = await createAgentInvite()
      setInvite(nextInvite)
      toast.success(t('settings:inviteCreated'))
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.problem.title || t('common:requestFailed'), { description: err.problem.detail })
      } else {
        toast.error(t('common:requestFailed'), { description: t('common:networkError') })
      }
    } finally {
      setIsCreatingInvite(false)
    }
  }

  const handleCopyInvite = async () => {
    if (!invite?.invite_code) return
    try {
      await navigator.clipboard.writeText(invite.invite_code)
      toast.success(t('settings:inviteCopied'))
    } catch {
      toast.error(t('settings:inviteCopyFailed'))
    }
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-semibold text-zinc-50">
        {t('settings:title')}
      </h1>

      <Card className="border-zinc-800 bg-zinc-950/70">
        <CardHeader>
          <CardTitle className="text-zinc-50">{t('settings:appearanceTitle')}</CardTitle>
          <CardDescription>{t('settings:appearanceDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
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
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-950/70">
        <CardHeader>
          <CardTitle className="text-zinc-50">{t('settings:agentInviteTitle')}</CardTitle>
          <CardDescription>{t('settings:agentInviteDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
            {t('settings:agentInviteWarning')}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button onClick={handleCreateInvite} disabled={isCreatingInvite}>
              {isCreatingInvite ? t('settings:creatingInvite') : t('settings:createInvite')}
            </Button>
            {invite ? (
              <Button variant="outline" onClick={handleCopyInvite}>
                {t('settings:copyInvite')}
              </Button>
            ) : null}
          </div>
          {invite ? (
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300" htmlFor="agent-invite-code">
                {t('settings:inviteCode')}
              </label>
              <Input
                id="agent-invite-code"
                readOnly
                value={invite.invite_code}
                className="font-mono text-sm"
              />
              <p className="text-sm text-zinc-400">
                {t('settings:inviteExpires')}: {invite.expires_in}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
