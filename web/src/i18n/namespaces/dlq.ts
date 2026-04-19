export const en = {
  title: 'Dead Letter Queue',
  columns: {
    title: 'Task',
    error: 'Error',
    retries: 'Retries',
    failedAt: 'Failed at',
    actions: '',
  },
  retryCta: 'Retry',
  retryConfirmBody:
    'Retry task: This re-queues the task with a fresh lease. Continue?',
  emptyHeading: 'DLQ is empty',
  emptyBody: 'No failed tasks. Failed tasks land here for manual retry.',
} as const

export const tr = {
  title: 'Dead Letter Queue',
  columns: {
    title: 'Gorev',
    error: 'Hata',
    retries: 'Deneme',
    failedAt: 'Basarisiz oldu',
    actions: '',
  },
  retryCta: 'Tekrar dene',
  retryConfirmBody:
    'Gorevi tekrar dene: Bu, gorevi yeni bir kira ile kuyruga alir. Devam?',
  emptyHeading: 'DLQ bos',
  emptyBody:
    'Basarisiz gorev yok. Basarisiz gorevler manuel tekrar deneme icin buraya gelir.',
} as const
