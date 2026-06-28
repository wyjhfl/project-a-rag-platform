import { expect, test } from './helpers'

test.describe('Console hash routing', () => {
  test('opens jobs page directly from hash URL', async ({ page }) => {
    await page.goto('/#/jobs')

    await expect(page.locator('[data-testid="page-jobs"]')).toBeVisible()
    await expect(page.locator('[data-testid="nav-jobs"]')).toHaveAttribute('aria-current', 'page')
  })

  test('opens agentic rag page directly from hash URL', async ({ page }) => {
    await page.goto('/#/agentic')

    await expect(page.locator('[data-testid="page-agentic"]')).toBeVisible()
    await expect(page.locator('[data-testid="nav-agentic"]')).toHaveAttribute('aria-current', 'page')
  })

  test('updates URL hash when navigating between console pages', async ({ page }) => {
    await page.goto('/')

    await page.click('[data-testid="nav-status"]')
    await expect(page).toHaveURL(/#\/status$/)
    await expect(page.locator('[data-testid="nav-status"]')).toHaveAttribute('aria-current', 'page')

    await page.click('[data-testid="nav-audit"]')
    await expect(page).toHaveURL(/#\/audit$/)
    await expect(page.locator('[data-testid="page-audit"]')).toBeVisible()
  })

  test('invalid hash falls back to a valid console page', async ({ page }) => {
    await page.goto('/#/not-a-real-tab')

    await expect(page.locator('[data-testid="page-acceptance"]')).toBeVisible()
    await expect(page).toHaveURL(/#\/acceptance$/)
  })
})
