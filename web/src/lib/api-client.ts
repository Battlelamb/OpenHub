import { useAuthStore } from '@/stores/auth-store'
import { getRouter } from './router-ref'

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail?: string
  instance?: string
  errors?: Array<{ field: string; message: string }>
  trace_id?: string
}

export class ApiError extends Error {
  constructor(public problem: ProblemDetail) {
    super(problem.title)
    this.name = 'ApiError'
  }
}

export interface ApiOptions extends RequestInit {
  skipAuth?: boolean
}

export async function api<T = unknown>(path: string, init: ApiOptions = {}): Promise<T> {
  const { skipAuth, ...rest } = init
  const token = useAuthStore.getState().token
  const headers = new Headers(rest.headers)
  if (token && !skipAuth) headers.set('Authorization', `Bearer ${token}`)
  if (rest.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(path, { ...rest, headers })

  if (res.status === 401 && !skipAuth) {
    const router = getRouter()
    const onLogin = router?.state.location.pathname === '/login'
    if (!onLogin) {
      useAuthStore.getState().clear()
      router?.navigate({ to: '/login' as any, search: { redirect: router.state.location.href } as any })
    }
  }

  if (!res.ok) {
    const problem: ProblemDetail = await res.json().catch(() => ({
      type: 'about:blank',
      title: res.statusText || 'Request failed',
      status: res.status,
    }))
    throw new ApiError(problem)
  }

  if (res.status === 204) return undefined as T
  const text = await res.text()
  return (text ? JSON.parse(text) : undefined) as T
}
