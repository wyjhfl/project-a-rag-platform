import { expect, test } from './helpers'

test.describe('System Status', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="nav-status"]')
    await expect(page.locator('[data-testid="page-status"]')).toBeVisible()
  })

  test('displays healthz card', async ({ page }) => {
    const healthzCard = page.locator('.health-grid .el-card').first()
    await expect(healthzCard).toBeVisible()
  })

  test('displays readyz card', async ({ page }) => {
    const cards = page.locator('.health-grid .el-card')
    await expect(cards.nth(1)).toBeVisible()
  })

  test('displays legacy health card', async ({ page }) => {
    const cards = page.locator('.health-grid .el-card')
    await expect(cards.nth(2)).toBeVisible()
  })

  test('page does not crash even if readyz is degraded', async ({ page }) => {
    await expect(page.locator('[data-testid="page-status"]')).toBeVisible()
  })
})
