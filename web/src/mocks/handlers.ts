import { agentsHandlers } from './handlers/agents'
import { tasksHandlers } from './handlers/tasks'
import { workflowsHandlers } from './handlers/workflows'
import { dlqHandlers } from './handlers/dlq'
import { costsHandlers } from './handlers/costs'
import { memoryHandlers } from './handlers/memory'
import { locksHandlers } from './handlers/locks'
import { healthHandlers } from './handlers/health'
import { settingsHandlers } from './handlers/settings'

export const handlers = [
  ...agentsHandlers,
  ...tasksHandlers,
  ...workflowsHandlers,
  ...dlqHandlers,
  ...costsHandlers,
  ...memoryHandlers,
  ...locksHandlers,
  ...healthHandlers,
  ...settingsHandlers,
]
