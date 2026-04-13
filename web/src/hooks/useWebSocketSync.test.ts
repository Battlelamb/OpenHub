import { describe, it, expect } from 'vitest'
import { buildWsUrl } from './useWebSocketSync'

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
})
