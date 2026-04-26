import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { MemoryItem } from '@/types/entities'

interface BackendMemoryKey {
  key: string
  value_type?: string
  tags?: string[]
  created_by?: string
  updated_at?: string
}

interface BackendMemoryKeysResponse {
  keys: BackendMemoryKey[]
  total: number
}

function adaptMemory(b: BackendMemoryKey): MemoryItem {
  let age_seconds = 0
  if (b.updated_at) {
    try {
      const updatedMs = new Date(b.updated_at).getTime()
      const nowMs = Date.now()
      age_seconds = Math.max(0, Math.floor((nowMs - updatedMs) / 1000))
    } catch {
      age_seconds = 0
    }
  }
  return {
    key: b.key,
    size_bytes: 0,                  // backend /keys does not include size; future TODO to add SUM(LENGTH(value)) per key
    age_seconds,
    value_preview: undefined,
    value_type: b.value_type,
    tags: b.tags,
    updated_at: b.updated_at,
  }
}

export function useMemoryEntries() {
  return useQuery({
    queryKey: qk.memory,
    queryFn: async (): Promise<MemoryItem[]> => {
      const res = await api<BackendMemoryKeysResponse>('/v1/memory/keys?limit=200')
      return (res.keys ?? []).map(adaptMemory)
    },
  })
}
