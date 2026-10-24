import { test, expect } from '@playwright/test';
import { loginAsManager } from './helpers';

test.describe('Phân hệ Lập lịch Đăng bài (Calendar & Scheduling)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsManager(page);
    await page.goto('/calendar');
    await expect(page.locator('h1')).toContainText('Lịch đăng bài');
  });

  test('Chuyển đổi chế độ xem Tháng / Tuần và điều hướng thời gian', async ({ page }) => {
    // Chuyển sang xem theo Tuần
    const weekBtn = page.getByRole('button', { name: 'Tuần', exact: true });
    await weekBtn.click();
    await page.waitForTimeout(300);

    // Chuyển lại sang xem theo Tháng
    const monthBtn = page.getByRole('button', { name: 'Tháng', exact: true });
    await monthBtn.click();
    await page.waitForTimeout(300);

    // Nút Hôm nay
    await page.getByRole('button', { name: 'Hôm nay' }).click();
  });

  test('Lập lịch đăng mới cho bài viết đã duyệt', async ({ page }) => {
    await page.getByRole('button', { name: 'Lập lịch mới' }).click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Chọn bài viết đã duyệt thuộc chiến dịch đang chạy (Content 2)
    const contentSelect = modal.getByLabel(/Bài viết cần lên lịch/i);
    await contentSelect.selectOption('2');

    // Điền thời gian đăng bài (3 ngày tới lúc 10:00, nằm trong thời gian chiến dịch)
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 3);
    const dateStr = futureDate.toISOString().slice(0, 10);
    await modal.getByLabel(/Thời điểm đăng bài/i).fill(`${dateStr}T10:00`);

    await modal.getByLabel(/Ghi chú thêm/i).fill('Đăng kèm hashtag thương hiệu #AnNamCoffee.');
    await modal.getByRole('button', { name: 'Xác nhận lên lịch' }).click();

    // Modal đóng lại
    await expect(modal).not.toBeVisible({ timeout: 6000 });
  });

  test('Xem chi tiết lịch đăng và thao tác Huỷ lịch đăng bài', async ({ page }) => {
    // Tìm một thẻ lịch đăng bất kỳ trong bảng lịch
    const scheduleCard = page.locator('button.w-full.text-left, [role="button"]:has-text("PLANNED"), [role="button"]:has-text("Dự kiến")').first();
    if (await scheduleCard.isVisible()) {
      await scheduleCard.click();

      const detailModal = page.locator('[role="dialog"]');
      await expect(detailModal).toBeVisible();

      // Nút huỷ lịch
      const cancelBtn = detailModal.getByRole('button', { name: 'Huỷ lịch' });
      if (await cancelBtn.isVisible()) {
        await cancelBtn.click();
        await expect(detailModal).not.toBeVisible({ timeout: 6000 });
      }
    }
  });
});
