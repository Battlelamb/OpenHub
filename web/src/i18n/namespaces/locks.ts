export const en = {
  title: 'Resource locks',
  columns: {
    resource: 'Resource',
    agent: 'Agent',
    acquired: 'Acquired',
    expires: 'Expires',
    conflict: 'Conflict',
  },
  emptyHeading: 'No active locks',
  emptyBody:
    'Resource locks appear here when agents claim shared resources.',
} as const

export const tr = {
  title: 'Kaynak kilitleri',
  columns: {
    resource: 'Kaynak',
    agent: 'Ajan',
    acquired: 'Alindi',
    expires: 'Suresi dolar',
    conflict: 'Cakisma',
  },
  emptyHeading: 'Aktif kilit yok',
  emptyBody:
    'Ajanlar paylasilan kaynaklari talep ettiginde kaynak kilitleri burada gorunur.',
} as const
