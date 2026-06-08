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
})
