import { test, expect } from '@playwright/test';

test('App loads successfully and shows brand title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Chiến dịch Marketing|AIA331/);
  // Trang đăng nhập Halloween: form "Đăng nhập" + scene "Không gian của bạn".
  // "MarketFlow AI" chỉ render trong Sidebar sau khi đăng nhập.
  await expect(page.locator('#login-title')).toHaveText('Đăng nhập');
  await expect(page.locator('#email')).toBeVisible();
});
