export const qk = {
  agents: {
    all: ['agents'] as const,
    detail: (id: string) => ['agents', id] as const,
  },
  tasks: {
    all: ['tasks'] as const,
    list: (filters: { status?: string } = {}) => ['tasks', 'list', filters] as const,
    detail: (id: string) => ['tasks', id] as const,
    trace: (id: string) => ['tasks', id, 'trace'] as const,
  },
  workflows: {
    all: ['workflows'] as const,
    detail: (id: string) => ['workflows', id] as const,
  },
  health: ['health'] as const,
  dlq: ['dlq'] as const,
  costs: ['costs'] as const,
  memory: ['memory'] as const,
  locks: ['locks'] as const,
  search: {
    semantic: (query: string) => ['search', 'semantic', query] as const,
  },
} as const
