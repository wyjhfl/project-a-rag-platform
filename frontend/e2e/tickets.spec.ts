import { expect, test } from './helpers'

test.describe('Tickets Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="nav-tickets"]')
    await expect(page.locator('[data-testid="page-tickets"]')).toBeVisible()
  })

  test('displays ticket start button', async ({ page }) => {
    await expect(page.locator('[data-testid="ticket-start-button"]')).toBeVisible()
  })

  test('clicking start ticket shows confirm dialog and can cancel', async ({ page }) => {
    await page.click('[data-testid="ticket-start-button"]')

    const confirmDialog = page.locator('.el-message-box')
    await expect(confirmDialog).toBeVisible({ timeout: 5_000 })

    await confirmDialog.locator('button:has-text("取消")').click()
    await expect(confirmDialog).not.toBeVisible()

    await expect(page.locator('[data-testid="page-tickets"]')).toBeVisible()
  })
})
