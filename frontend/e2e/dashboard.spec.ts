import { test, expect } from '@playwright/test'

test.describe('Dashboard Base Verification', () => {
  test('loads the app and shows the empty state correctly', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('heading', { name: /TraceRule/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Upload policy document/i })).toBeVisible()
  })
})
