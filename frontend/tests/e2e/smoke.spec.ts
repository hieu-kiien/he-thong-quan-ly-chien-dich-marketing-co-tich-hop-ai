import { test, expect } from '@playwright/test';

test('App loads successfully and shows brand title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Chiến dịch Marketing|AIA331/);
  const brand = page.locator('text=MarketFlow AI').first();
  await expect(brand).toBeVisible();
});
