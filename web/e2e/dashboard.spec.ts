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

  test('drag-drop updates task status through API and refetches the Kanban board', async ({ page, request }) => {
    const login = await request.post('/v1/auth/admin/login', {
      form: { username: ADMIN_USER, password: ADMIN_PASS },
    })
    expect(login.ok()).toBeTruthy()
    const { access_token: token } = await login.json()
    const title = `E2E Kanban ${Date.now()}`
    const create = await request.post('/v1/tasks/', {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title,
        description: 'Created by Playwright to verify Kanban drag-drop persistence.',
        required_capabilities: [`phase06-e2e-unmatched-${Date.now()}`],
        priority: 50,
      },
    })
    expect(create.ok()).toBeTruthy()
    const created = await create.json()
    const taskId = created.id as string
    expect(created.status).toBe('queued')

    await page.getByRole('link', { name: /tasks/i }).first().click()
    await expect(page).toHaveURL(/\/tasks/)
    await expect(page.getByTestId(`kanban-card-${taskId}`)).toContainText(title, { timeout: 15_000 })
    await expect(page.getByTestId('kanban-column-queued')).toContainText(title)

    const patchResponse = page.waitForResponse(
      (response) =>
        response.url().includes(`/v1/tasks/${taskId}/status`) &&
        response.request().method() === 'PATCH'
    )
    const handle = page.getByTestId(`kanban-drag-handle-${taskId}`)
    const claimedDropzone = page.getByTestId('kanban-dropzone-claimed')
    await handle.scrollIntoViewIfNeeded()

    const handleBox = await handle.boundingBox()
    const dropzoneBox = await claimedDropzone.boundingBox()
    expect(handleBox).not.toBeNull()
    expect(dropzoneBox).not.toBeNull()

    await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + handleBox!.height / 2)
    await page.mouse.down()
    await page.mouse.move(
      dropzoneBox!.x + dropzoneBox!.width / 2,
      dropzoneBox!.y + Math.min(80, dropzoneBox!.height / 2),
      { steps: 30 }
    )
    await page.mouse.up()

    const transition = await patchResponse
    expect(transition.ok()).toBeTruthy()

    await expect(page.locator('[data-sonner-toast]').filter({ hasText: /Task status updated/i })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('kanban-column-claimed')).toContainText(title, { timeout: 15_000 })

    const detail = await request.get(`/v1/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(detail.ok()).toBeTruthy()
    expect((await detail.json()).status).toBe('claimed')
  })

  test('opens a task detail workflow canvas from a Kanban card', async ({ page, request }) => {
    const login = await request.post('/v1/auth/admin/login', {
      form: { username: ADMIN_USER, password: ADMIN_PASS },
    })
    expect(login.ok()).toBeTruthy()
    const { access_token: token } = await login.json()
    const title = `E2E Workflow Canvas ${Date.now()}`
    const create = await request.post('/v1/tasks/', {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title,
        description: 'Created by Playwright to verify Kanban card opens workflow canvas.',
        required_capabilities: [`phase06-workflow-unmatched-${Date.now()}`],
        priority: 40,
      },
    })
    expect(create.ok()).toBeTruthy()
    const taskId = ((await create.json()) as { id: string }).id

    await page.getByRole('link', { name: /tasks/i }).first().click()
    await expect(page.getByTestId(`kanban-card-${taskId}`)).toContainText(title, { timeout: 15_000 })
    await page.getByTestId(`kanban-card-${taskId}`).click()

    await expect(page).toHaveURL(new RegExp(`/dashboard/tasks/${taskId}`), { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: title }).first()).toBeVisible()
    await expect(page.getByTestId('workflow-canvas')).toHaveAttribute('data-mode', 'embedded')
    await expect(page.locator('.react-flow')).toBeVisible()
    await expect(
      page.getByLabel('Task detail information').getByRole('heading', { name: 'Task Details' })
    ).toBeVisible()
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
