import { test, expect } from '@playwright/test'

const BASE = '/dashboard'
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'omer'
const ADMIN_PASS = process.env.E2E_ADMIN_PASSWORD || 'OpenHub2026!'

test.describe('Login flow', () => {
  test('redirects unauthenticated user to login page', async ({ page }) => {
    await page.goto(BASE)
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('shows validation errors on empty submit', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page.getByText(/username required/i)).toBeVisible()
    await expect(page.getByText(/password required/i)).toBeVisible()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await page.getByLabel('Username').fill('wrong-user')
    await page.getByLabel('Password').fill('wrong-pass')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page.locator('[data-sonner-toast]')).toBeVisible({ timeout: 10_000 })
  })

  test('logs in with valid credentials and redirects to agents', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await page.getByLabel('Username').fill(ADMIN_USER)
    await page.getByLabel('Password').fill(ADMIN_PASS)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/agents/, { timeout: 10_000 })
  })
})

test.describe('Dashboard navigation', () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(15_000)
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' })
    await page.getByLabel('Username').fill(ADMIN_USER)
    await page.getByLabel('Password').fill(ADMIN_PASS)
    await page.getByRole('button', { name: /sign in/i }).click()
    await page.waitForURL(/\/agents/, { timeout: 10_000 })
  })

  test('agents page loads with sidebar navigation', async ({ page }) => {
    // Wait for the sidebar to render
    await page.waitForLoadState('domcontentloaded')
    const agentsLink = page.getByRole('link', { name: /agents/i }).first()
    await expect(agentsLink).toBeVisible({ timeout: 10_000 })
    const tasksLink = page.getByRole('link', { name: /tasks/i }).first()
    await expect(tasksLink).toBeVisible()
  })

  test('can navigate to tasks page', async ({ page }) => {
    await page.getByRole('link', { name: /tasks/i }).first().click()
    await expect(page).toHaveURL(/\/tasks/)
  })

  test('can navigate to workflows page', async ({ page }) => {
    await page.getByRole('link', { name: /workflows/i }).first().click()
    await expect(page).toHaveURL(/\/workflows/)
  })

  test('health page loads', async ({ page }) => {
    await page.goto(`${BASE}/health`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).not.toBeEmpty()
  })
})
