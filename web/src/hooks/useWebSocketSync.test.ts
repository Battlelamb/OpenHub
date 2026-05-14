import { describe, it, expect, vi } from 'vitest'
import { buildWsUrl, handleEvent } from './useWebSocketSync'
import { qk } from '@/lib/query-keys'

describe('useWebSocketSync', () => {
  describe('buildWsUrl', () => {
    it('does NOT include ?token= in the URL (first-frame auth per D-03)', () => {
      const url = buildWsUrl()
      expect(url).not.toContain('?token=')
      expect(url).toMatch(/^ws[s]?:\/\/.+/)
      expect(url).toContain('/v1/ws/ui')
    })

    it('uses wss:// when window.location.protocol is https:', () => {
      const originalProtocol = window.location.protocol
      Object.defineProperty(window, 'location', {
        value: { protocol: 'https:', host: 'example.com' },
        writable: true,
      })
      const url = buildWsUrl()
      expect(url).toBe('wss://example.com/v1/ws/ui')
      Object.defineProperty(window, 'location', {
        value: { protocol: originalProtocol, host: 'localhost:5173' },
        writable: true,
      })
    })

    it('uses ws:// when window.location.protocol is http:', () => {
      const originalProtocol = window.location.protocol
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:5173' },
        writable: true,
      })
      const url = buildWsUrl()
      expect(url).toBe('ws://localhost:5173/v1/ws/ui')
      Object.defineProperty(window, 'location', {
        value: { protocol: originalProtocol, host: 'localhost:5173' },
        writable: true,
      })
    })
  })

  describe('handleEvent', () => {
    it('invalidates agent cache for ACN node and agent events', () => {
      const qc = {
        setQueryData: vi.fn(),
        invalidateQueries: vi.fn(),
      }

      handleEvent(qc as any, {
        event: 'acn_agent_registered',
        timestamp: '2026-05-14T00:00:00Z',
        data: { agent_id: 'agent-1', agent_name: 'Brunhilde', node_name: 'node-1' },
      })
      handleEvent(qc as any, {
        event: 'acn_node_heartbeat',
        timestamp: '2026-05-14T00:00:01Z',
        data: { node_id: 'node-1', agent_id: 'agent-1' },
      })

      expect(qc.invalidateQueries).toHaveBeenCalledTimes(2)
      expect(qc.invalidateQueries).toHaveBeenCalledWith({ queryKey: qk.agents.all })
    })

    it('patches task status and invalidates task lists for live task events', () => {
      const qc = {
        setQueryData: vi.fn(),
        invalidateQueries: vi.fn(),
      }

      handleEvent(qc as any, {
        event: 'task_status_changed',
        timestamp: '2026-05-14T00:00:00Z',
        data: { task_id: 'task-1', status: 'running' },
      })

      expect(qc.setQueryData).toHaveBeenCalledWith(qk.tasks.all, expect.any(Function))
      expect(qc.setQueryData).toHaveBeenCalledWith(qk.tasks.detail('task-1'), expect.any(Function))
      expect(qc.invalidateQueries).toHaveBeenCalledWith({ queryKey: qk.tasks.all })
    })
  })
})
