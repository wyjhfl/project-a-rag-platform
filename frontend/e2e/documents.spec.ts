import { expect, test } from './helpers'

test.describe('Documents Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="nav-documents"]')
    await expect(page.locator('[data-testid="page-documents"]')).toBeVisible()
  })

  test('displays ingest section', async ({ page }) => {
    await expect(page.locator('[data-testid="page-documents"]')).toBeVisible()
  })

  test('clicking async ingest shows confirm dialog and can cancel', async ({ page }) => {
    await page.click('[data-testid="ingest-async-button"]')

    const confirmDialog = page.locator('.el-message-box')
    await expect(confirmDialog).toBeVisible({ timeout: 5_000 })

    await confirmDialog.locator('button:has-text("取消")').click()
    await expect(confirmDialog).not.toBeVisible()

    await expect(page.locator('[data-testid="page-documents"]')).toBeVisible()
  })
})
