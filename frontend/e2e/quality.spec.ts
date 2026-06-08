import { expect, navigateTo, test } from './helpers'

test.describe('Quality Insights Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await navigateTo(page, 'quality')
  })

  test('shows RAG quality metrics and tradeoff lane', async ({ page }) => {
    await expect(page.locator('[data-testid="page-quality"]')).toBeVisible()
    await expect(page.locator('[data-testid="quality-overview-card"]')).toContainText('RAG 质量洞察')
    await expect(page.locator('[data-testid="quality-regression-pass-rate"]')).toBeVisible()
    await expect(page.locator('[data-testid="quality-context-precision"]')).toBeVisible()
    await expect(page.locator('[data-testid="quality-faithfulness"]')).toBeVisible()
    await expect(page.locator('[data-testid="quality-context-recall"]')).toBeVisible()
    await expect(page.locator('[data-testid="quality-badcase-count"]')).toBeVisible()
    await expect(page.locator('[data-testid="quality-tradeoff-lane"]')).toContainText('外部队列')
  })
})
