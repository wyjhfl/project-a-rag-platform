import { expect, test } from './helpers'

test.describe('API Key Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('opens API Key config dialog', async ({ page }) => {
    await page.click('[data-testid="api-key-config-button"]')
    const dialog = page.locator('.el-dialog')
    await expect(dialog).toBeVisible()
  })

  test('can input a demo key and select role', async ({ page }) => {
    await page.click('[data-testid="api-key-config-button"]')
    const dialog = page.locator('.el-dialog')
    await expect(dialog).toBeVisible()

    await page.fill('[data-testid="api-key-input"]', 'demo-test-key-123')
    // Click the admin radio button - use text-based selector for Element Plus
    await page.locator('[data-testid="api-key-role-group"]').getByText('admin').click()

    await page.click('[data-testid="api-key-save-button"]')
    await expect(dialog).not.toBeVisible({ timeout: 5000 })

    await expect(page.locator('.key-status')).toBeVisible()
  })

  test('can clear API Key and return to unconfigured state', async ({ page }) => {
    await page.click('[data-testid="api-key-config-button"]')
    const dialog = page.locator('.el-dialog')
    await expect(dialog).toBeVisible()

    await page.fill('[data-testid="api-key-input"]', 'demo-test-key-123')
    await page.click('[data-testid="api-key-save-button"]')
    await expect(dialog).not.toBeVisible({ timeout: 5000 })

    await page.click('[data-testid="api-key-config-button"]')
    await expect(dialog).toBeVisible()

    await page.click('[data-testid="api-key-clear-button"]')
    await expect(dialog).not.toBeVisible({ timeout: 5000 })

    await expect(page.locator('.key-status')).toBeVisible()
  })
})
