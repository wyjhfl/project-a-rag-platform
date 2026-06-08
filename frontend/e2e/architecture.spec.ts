import { expect, navigateTo, test } from './helpers'

test.describe('Architecture Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await navigateTo(page, 'architecture')
  })

  test('shows system layers, flows, and production gate evidence', async ({ page }) => {
    await expect(page.locator('[data-testid="page-architecture"]')).toBeVisible()
    await expect(page.locator('[data-testid="architecture-overview-card"]')).toContainText('架构总览')
    await expect(page.locator('[data-testid="architecture-layer-map"]')).toContainText('FastAPI')
    await expect(page.locator('[data-testid="architecture-rag-flow"]')).toContainText('grounded')
    await expect(page.locator('[data-testid="architecture-job-flow"]')).toContainText('Worker')
    await expect(page.locator('[data-testid="architecture-observability-flow"]')).toContainText('Prometheus')
    await expect(page.locator('[data-testid="architecture-acceptance-gate"]')).toContainText('final_production_acceptance.ps1')
  })
})
