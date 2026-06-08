import { expect, test } from './helpers'

test.describe('Acceptance Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('default page is acceptance center', async ({ page }) => {
    await expect(page.locator('[data-testid="page-acceptance"]')).toBeVisible()
  })

  test('page shows content or loading state, not blank', async ({ page }) => {
    const pageEl = page.locator('[data-testid="page-acceptance"]')
    await expect(pageEl).toBeVisible()
    const hasContent = await pageEl.innerText()
    expect(hasContent.length).toBeGreaterThan(0)
  })

  test('shows production release entrypoint', async ({ page }) => {
    const releaseBadge = page.locator('[data-testid="release-badge"]')
    await expect(releaseBadge).toBeVisible()
    await expect(releaseBadge).toContainText('v1.0.5')

    const releaseLink = page.locator('[data-testid="release-link"]')
    await expect(releaseLink).toHaveAttribute(
      'href',
      'https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.5',
    )
  })

  test('shows interview showcase summary and demo route', async ({ page }) => {
    await expect(page.locator('[data-testid="interview-showcase-card"]')).toBeVisible()
    await expect(page.locator('[data-testid="interview-pitch"]')).toContainText('企业设备售后诊断 RAG 平台')
    await expect(page.locator('[data-testid="showcase-proof-grid"]')).toContainText('生产门禁')
    await expect(page.locator('[data-testid="showcase-architecture-pillars"]')).toContainText('OpenAPI')
    await expect(page.locator('[data-testid="showcase-demo-route"]')).toContainText('System Status')
  })

  test('shows RAG quality, bad case, and tradeoff evidence', async ({ page }) => {
    await expect(page.locator('[data-testid="rag-quality-card"]')).toBeVisible()
    await expect(page.locator('[data-testid="rag-quality-card"]')).toContainText('RAG 质量证据')
    await expect(page.locator('[data-testid="rag-quality-metric-context-precision"]')).toBeVisible()
    await expect(page.locator('[data-testid="rag-quality-metric-faithfulness"]')).toBeVisible()
    await expect(page.locator('[data-testid="rag-quality-metric-context-recall"]')).toBeVisible()
    await expect(page.locator('[data-testid="bad-case-boundary-card"]')).toContainText('资料不足时拒答')
    await expect(page.locator('[data-testid="risk-tradeoff-card"]')).toContainText('外部队列')
  })
})
