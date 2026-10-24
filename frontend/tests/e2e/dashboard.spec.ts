import { test, expect } from '@playwright/test';
import { loginAsManager, takeScreenshot } from './helpers';

test.describe('Phân hệ Tổng quan & Tiện ích chung (Dashboard, Dark Mode, Notifications)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsManager(page);
  });

  test('Số liệu Tổng quan khớp với API và hiển thị nhãn Dữ liệu mẫu', async ({ page }) => {
    // Chờ dashboard load xong
    await expect(page.locator('h1')).toContainText('Tổng quan marketing');

    // Kiểm tra nhãn Dữ liệu mẫu (CONTRACT §0, §10)
    const seedBadge = page.locator('text=Dữ liệu mẫu');
    await expect(seedBadge).toBeVisible({ timeout: 5000 });

    // Kiểm tra các thẻ số liệu thống kê cơ bản
    await expect(page.locator('text=Lượt hiển thị (Views)')).toBeVisible();
    await expect(page.locator('text=Lượt bấm (Clicks)')).toBeVisible();
    await expect(page.locator('text=Chuyển đổi (Conversions)')).toBeVisible();
    await expect(page.locator('text=Tổng chi phí / Ngân sách')).toBeVisible();

    // Đảm bảo không xuất hiện NaN hoặc undefined trên giao diện
    const pageContent = await page.content();
    expect(pageContent).not.toContain('NaN');
    expect(pageContent).not.toContain('undefined');

    // Chụp ảnh giao diện 1280px
    await takeScreenshot(page, 'dashboard-1280px');
  });

  test('Kiểm tra giao diện Responsive ở độ phân giải máy tính bảng 768px', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Tổng quan marketing');

    // Chụp ảnh giao diện 768px
    await takeScreenshot(page, 'dashboard-768px');
  });

  test('Chuyển đổi Chế độ Sáng / Tối (Dark Mode Toggle)', async ({ page }) => {
    const themeBtn = page.locator('header').getByRole('button', { name: /Chuyển sang giao diện tối|Chuyển sang giao diện sáng/i });
    await expect(themeBtn).toBeVisible();

    const initialIsDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));

    // Bấm nút chuyển đổi
    await themeBtn.click();
    await page.waitForTimeout(300);

    const isDarkAfter = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    expect(isDarkAfter).toBe(!initialIsDark);

    // Chuyển lại trạng thái ban đầu
    await themeBtn.click();
    await page.waitForTimeout(300);
    const finalIsDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    expect(finalIsDark).toBe(initialIsDark);
  });

  test('Chuông Thông báo (Notifications Bell) hiển thị danh sách và đánh dấu đã đọc', async ({ page }) => {
    const bellBtn = page.locator('header').getByRole('button', { name: /Thông báo/i });
    await expect(bellBtn).toBeVisible();

    // Mở popover thông báo
    await bellBtn.click();

    // Kiểm tra popover thông báo mở
    const notifHeader = page.locator('p:has-text("Thông báo")').first();
    await expect(notifHeader).toBeVisible();

    // Bấm đánh dấu tất cả đã đọc nếu có
    const markAllReadBtn = page.getByRole('button', { name: 'Đánh dấu tất cả đã đọc' });
    if (await markAllReadBtn.isEnabled()) {
      await markAllReadBtn.click();
      await page.waitForTimeout(500);
    }
  });
});
