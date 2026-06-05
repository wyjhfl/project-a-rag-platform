import { expect, test } from './helpers'

test.describe('Evaluations Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="nav-eval"]')
    await expect(page.locator('[data-testid="page-eval"]')).toBeVisible()
  })

  test('displays evaluation section', async ({ page }) => {
    await expect(page.locator('[data-testid="page-eval"]')).toBeVisible()
  })

  test('clicking async eval shows confirm dialog and can cancel', async ({ page }) => {
    await page.click('[data-testid="eval-async-button"]')

    const confirmDialog = page.locator('.el-message-box')
    await expect(confirmDialog).toBeVisible({ timeout: 5_000 })

    await confirmDialog.locator('button:has-text("取消")').click()
    await expect(confirmDialog).not.toBeVisible()

    await expect(page.locator('[data-testid="page-eval"]')).toBeVisible()
  })
})
