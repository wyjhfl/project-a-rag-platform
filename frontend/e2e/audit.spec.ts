import { expect, test } from './helpers'

test.describe('Audit Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="nav-audit"]')
    await expect(page.locator('[data-testid="page-audit"]')).toBeVisible()
  })

  test('page does not crash', async ({ page }) => {
    await expect(page.locator('[data-testid="page-audit"]')).toBeVisible()
  })

  test('shows permission error or audit content', async ({ page }) => {
    const hasPermissionError = await page.locator('.el-alert[title*="admin"]').isVisible().catch(() => false)
    const hasTable = await page.locator('.el-table').isVisible().catch(() => false)
    const hasEmpty = await page.locator('.el-empty').isVisible().catch(() => false)
    expect(hasPermissionError || hasTable || hasEmpty).toBeTruthy()
  })

  test('metadata dialog can open if data exists', async ({ page }) => {
    const viewButtons = page.locator('.el-table .el-button:has-text("查看")')
    const count = await viewButtons.count()
    if (count > 0) {
      await viewButtons.first().click()
      await expect(page.locator('.el-dialog:has-text("Metadata")')).toBeVisible()
    }
  })
})
