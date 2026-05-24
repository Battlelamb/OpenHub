export const en = {
  title: 'Health',
  subtitle: 'Service health, ACN agent registry truth, and task truth are checked from separate sources.',
  states: {
    loading: 'Loading',
    unavailable: 'Unavailable',
    unknown: 'unknown',
    none: 'None',
  },
  service: {
    title: 'Service health',
    status: 'Status',
    database: 'Database',
    databaseValue: 'Database: {{status}}',
    version: 'Version',
  },
  acn: {
    title: 'ACN registry truth',
    agents: 'Agents',
    nodes: 'Nodes',
    registry: 'Registered agents',
    node: 'node',
    nodesPlural: 'nodes',
    onlineAgent: 'online agent',
    onlineAgents: 'online agents',
  },
  tasks: {
    title: 'Task truth',
    total: 'Total',
    totalTask: 'total task',
    totalTasks: 'total tasks',
  },
  note: {
    title: 'Why this page changed',
    body: '/v1/health is process health only. Legacy agent/task counters from that payload are not used as dashboard truth; ACN status and task search are the authoritative dashboard sources.',
  },
} as const

export const tr = {
  title: 'Saglik',
  subtitle: 'Servis sağlığı, ACN agent kayıt gerçeği ve task gerçeği ayrı kaynaklardan kontrol edilir.',
  states: {
    loading: 'Yükleniyor',
    unavailable: 'Ulaşılamıyor',
    unknown: 'bilinmiyor',
    none: 'Yok',
  },
  service: {
    title: 'Servis sağlığı',
    status: 'Durum',
    database: 'Veritabanı',
    databaseValue: 'Veritabanı: {{status}}',
    version: 'Versiyon',
  },
  acn: {
    title: 'ACN kayıt gerçeği',
    agents: 'Agentlar',
    nodes: 'Node’lar',
    registry: 'Kayıtlı agentlar',
    node: 'node',
    nodesPlural: 'node',
    onlineAgent: 'online agent',
    onlineAgents: 'online agent',
  },
  tasks: {
    title: 'Task gerçeği',
    total: 'Toplam',
    totalTask: 'toplam task',
    totalTasks: 'toplam task',
  },
  note: {
    title: 'Bu sayfa neden değişti',
    body: '/v1/health yalnızca process sağlığıdır. Bu payload içindeki legacy agent/task sayaçları dashboard gerçeği olarak kullanılmaz; ACN status ve task search dashboard için yetkili kaynaklardır.',
  },
} as const
