import { expect, test } from './helpers'

test.describe('System Status', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="nav-status"]')
    await expect(page.locator('[data-testid="page-status"]')).toBeVisible()
  })

  test('displays healthz card', async ({ page }) => {
    await expect(page.locator('[data-testid="healthz-card"]')).toBeVisible()
  })

  test('displays readyz card', async ({ page }) => {
    await expect(page.locator('[data-testid="readyz-card"]')).toBeVisible()
  })

  test('displays legacy health card', async ({ page }) => {
    await expect(page.locator('[data-testid="legacy-health-card"]')).toBeVisible()
  })

  test('page does not crash even if readyz is degraded', async ({ page }) => {
    await expect(page.locator('[data-testid="page-status"]')).toBeVisible()
  })

  test('system details show release metadata or an explicit error state', async ({ page }) => {
    await expect(page.locator('[data-testid="system-status-panel"]')).toBeVisible()

    await expect
      .poll(
        async () => {
          const loaded = await page.locator('[data-testid="system-status-loaded"]').isVisible().catch(() => false)
          const error = await page.locator('[data-testid="system-status-error"]').isVisible().catch(() => false)
          if (loaded) return 'loaded'
          if (error) return 'error'
          return 'pending'
        },
        { timeout: 10_000 },
      )
      .not.toBe('pending')

    const loaded = await page.locator('[data-testid="system-status-loaded"]').isVisible().catch(() => false)
    if (loaded) {
      const panel = page.locator('[data-testid="system-status-panel"]')
      await expect(panel.locator('[data-testid="system-status-version"]').first()).toBeVisible()
      await expect(panel.locator('[data-testid="system-release-link"]').first()).toHaveAttribute(
        'href',
        'https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.4',
      )
    } else {
      await expect(page.locator('[data-testid="system-status-error"]')).toBeVisible()
    }
  })
})
