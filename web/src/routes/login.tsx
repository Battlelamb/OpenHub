import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoginForm } from '@/components/forms/LoginForm'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

function LoginPage() {
  const { t } = useTranslation('common')
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 pt-16">
      <Card className="w-full max-w-sm border-zinc-800 bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-2xl font-semibold text-zinc-50">{t('signInTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  )
}
