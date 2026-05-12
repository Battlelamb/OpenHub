import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { api, createAgentInvite } from './api-client'
import { useAuthStore } from '@/stores/auth-store'

describe('api-client', () => {
  beforeEach(() => {
    useAuthStore.getState().clear()
  })

  it('returns parsed JSON on 2xx', async () => {
    server.use(http.get('/v1/health', () => HttpResponse.json({ status: 'ok' })))
    const res = await api<{ status: string }>('/v1/health')
    expect(res.status).toBe('ok')
  })

  it('throws ApiError preserving RFC 7807 shape on 4xx', async () => {
    server.use(
      http.get('/v1/tasks/bad', () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Task not found',
            status: 404,
            detail: 'No task with id bad',
          },
          { status: 404 },
        ),
      ),
    )
    await expect(api('/v1/tasks/bad')).rejects.toMatchObject({
      name: 'ApiError',
      problem: { title: 'Task not found', status: 404, detail: 'No task with id bad' },
    })
  })

  it('injects Authorization header when token set', async () => {
    useAuthStore.getState().setSession('jwt-token', 'r', 900, { id: 'u1', name: 'a', role: 'admin' })
    let captured: string | null = null
    server.use(
      http.get('/v1/whoami', ({ request }) => {
        captured = request.headers.get('authorization')
        return HttpResponse.json({})
      }),
    )
    await api('/v1/whoami')
    expect(captured).toBe('Bearer jwt-token')
  })

  it('skipAuth omits Authorization header', async () => {
    useAuthStore.getState().setSession('jwt-token', 'r', 900, { id: 'u1', name: 'a', role: 'admin' })
    let captured: string | null = null
    server.use(
      http.post('/v1/auth/login', ({ request }) => {
        captured = request.headers.get('authorization')
        return HttpResponse.json({})
      }),
    )
    await api('/v1/auth/login', { method: 'POST', body: '{}', skipAuth: true })
    expect(captured).toBeNull()
  })

  it('creates dashboard ACN invites with the current session token', async () => {
    useAuthStore.getState().setSession('jwt-token', 'r', 900, { id: 'u1', name: 'a', role: 'admin' })
    let method: string | null = null
    let captured: string | null = null
    server.use(
      http.post('/v1/acn/dashboard/invite', ({ request }) => {
        method = request.method
        captured = request.headers.get('authorization')
        return HttpResponse.json({ invite_code: 'inv_test', expires_in: '24 hours' })
      }),
    )

    const invite = await createAgentInvite()

    expect(method).toBe('POST')
    expect(captured).toBe('Bearer jwt-token')
    expect(invite.invite_code).toBe('inv_test')
    expect(invite.expires_in).toBe('24 hours')
  })
})
