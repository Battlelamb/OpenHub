import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { api } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'

const schema = z.object({
  username: z.string().min(1, 'Username required'),
  password: z.string().min(1, 'Password required'),
})

type LoginValues = z.infer<typeof schema>

interface LoginResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  agent_id: string | null
  role: 'admin' | 'agent' | 'viewer'
  permissions: string[]
}

export function LoginForm() {
  const { t } = useTranslation('common')
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  
  // Get redirect from search params, default to /agents
  const getRedirect = () => {
    try {
      const search = useSearch({ strict: false }) as { redirect?: string }
      return search.redirect || '/agents'
    } catch {
      return '/agents'
    }
  }

  const form = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: '', password: '' },
  })

  const onSubmit = async (values: LoginValues) => {
    try {
      const formBody = new URLSearchParams({ username: values.username, password: values.password }).toString()
      const res = await api<LoginResponse>('/v1/auth/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formBody,
        skipAuth: true,
      })
      setSession(res.access_token, res.refresh_token, res.expires_in, {
        id: res.agent_id ?? values.username,
        name: values.username,
        role: res.role,
      })
      const target = getRedirect()
      navigate({ to: target as any })
    } catch (err: any) {
      if (err && typeof err === 'object' && 'problem' in err) {
        toast.error(err.problem.title || t('requestFailed'), { description: err.problem.detail })
      } else {
        toast.error(t('requestFailed'), { description: t('networkError') })
      }
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input autoComplete="username" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {t('signIn')}
        </Button>
      </form>
    </Form>
  )
}
