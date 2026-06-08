import { test as base } from '@playwright/test'

export const test = base.extend({})

export function navigateTo(page: import('@playwright/test').Page, tabKey: string) {
  return page.click(`[data-testid="nav-${tabKey}"]`)
}

export { expect } from '@playwright/test'
