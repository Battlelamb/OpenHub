import { type HttpHandler } from 'msw'

// Settings page reads from ui-store (client-side only); no network handler
// needed. Keeping the export shape consistent with other feature handlers.
export const settingsHandlers: HttpHandler[] = []
