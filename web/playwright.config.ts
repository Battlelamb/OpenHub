import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E config for OpenHub dashboard.
 *
 * Tests run against the live dev server at localhost:7788.
 * The API must be running before executing E2E tests.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  timeout: 30_000,

  use: {
    baseURL: 'http://localhost:7788',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
