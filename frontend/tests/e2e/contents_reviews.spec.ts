import { test, expect } from '@playwright/test';
import { loginAsManager, loginAsMarketer } from './helpers';

test.describe('Phân hệ Quản lý Nội dung & Duyệt bài (Contents & Review Workflow)', () => {
  test('Tạo nội dung bản nháp và gửi duyệt có cảnh báo từ cấm (Banned Keywords)', async ({ page }) => {
    // 1. Marketer đăng nhập tạo bài viết
    await loginAsMarketer(page);
    await page.goto('/contents');
    await expect(page.locator('h1')).toContainText('Quản lý nội dung');

    // Mở modal tạo nội dung
    await page.getByRole('button', { name: 'Soạn nội dung mới' }).click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Điền form
    await modal.getByLabel(/Chiến dịch/i).selectOption({ index: 1 });
    await modal.getByLabel(/Kênh triển khai/i).selectOption({ index: 1 });
    await modal.getByLabel(/Tiêu đề/i).fill('Bài viết ra mắt có từ cấm');
    await modal.getByLabel(/Nội dung chính/i).fill(
      'Sản phẩm cà phê rang xay nguyên chất cam kết 100% không hoá chất, như thần dược mang lại năng lượng tức thì.'
    );
    await modal.getByLabel(/Lời kêu gọi hành động/i).fill('Mua ngay');

    // Lưu bản nháp -> tự động chuyển hướng sang /contents/:id
    await modal.getByRole('button', { name: 'Lưu bản nháp' }).click();
    await expect(page).toHaveURL(/\/contents\/\d+/, { timeout: 10000 });

    // 2. Bấm Gửi duyệt
    const submitBtn = page.getByRole('button', { name: 'Gửi duyệt' });
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // 3. Hệ thống cảnh báo từ cấm (CONTRACT §4, §10: vẫn cho gửi nhưng cảnh báo và đính kèm banned_matches)
    const alertCallout = page.getByText(/từ cấm/i).first();
    await expect(alertCallout).toBeVisible({ timeout: 6000 });
  });

  test('Quản lý phê duyệt nội dung của nhân viên trong hàng đợi duyệt', async ({ page }) => {
    await loginAsManager(page);
    await page.goto('/reviews');
    await expect(page.locator('h1')).toContainText('Hàng đợi duyệt nội dung');

    // Tìm bài viết đang chờ duyệt do Marketer tạo
    const approveBtn = page.getByRole('button', { name: 'Duyệt' }).first();
    if (await approveBtn.isVisible()) {
      await approveBtn.click();

      // Hộp thoại xác nhận duyệt
      const approveModal = page.locator('[role="dialog"]');
      await expect(approveModal).toBeVisible();

      await approveModal.getByRole('button', { name: 'Xác nhận duyệt' }).click();
      await expect(approveModal).not.toBeVisible({ timeout: 6000 });
    }
  });

  test('Quản lý KHÔNG được tự duyệt nội dung do chính mình tạo (CANNOT_REVIEW_OWN)', async ({ page }) => {
    await loginAsManager(page);
    await page.goto('/contents');

    // Quản lý tự tạo một bài viết mới
    await page.getByRole('button', { name: 'Soạn nội dung mới' }).click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    await modal.getByLabel(/Chiến dịch/i).selectOption({ index: 1 });
    await modal.getByLabel(/Kênh triển khai/i).selectOption({ index: 1 });
    await modal.getByLabel(/Tiêu đề/i).fill('Bài viết do Quản lý tự soạn');
    await modal.getByLabel(/Nội dung chính/i).fill('Thông báo đặc biệt về workshop rang cà phê cuối tuần.');

    // Lưu bản nháp -> tự động chuyển hướng sang /contents/:id
    await modal.getByRole('button', { name: 'Lưu bản nháp' }).click();
    await expect(page).toHaveURL(/\/contents\/\d+/, { timeout: 10000 });

    // Gửi duyệt từ trang chi tiết
    await page.getByRole('button', { name: 'Gửi duyệt' }).click();
    await page.waitForTimeout(1000);

    // Vào trang /reviews: Quản lý thấy nhãn chặn tự duyệt, không thể bấm duyệt
    await page.goto('/reviews');
    const blockReasonText = page.locator('text=Bạn không thể tự duyệt nội dung do chính mình tạo').first();
    await expect(blockReasonText).toBeVisible({ timeout: 6000 });
  });

  test('Đánh dấu bài viết đã xuất bản (Mark Published)', async ({ page }) => {
    await loginAsManager(page);
    // Tìm bài viết ở trạng thái APPROVED
    await page.goto('/contents?status=APPROVED');

    const firstApprovedLink = page.locator('tbody tr td a').first();
    if (await firstApprovedLink.isVisible()) {
      await firstApprovedLink.click();

      // Bấm nút Đánh dấu đã đăng
      const publishBtn = page.getByRole('button', { name: 'Đánh dấu đã đăng' });
      await expect(publishBtn).toBeVisible({ timeout: 6000 });
      await publishBtn.click();

      const modal = page.locator('[role="dialog"]');
      await expect(modal).toBeVisible();

      await modal.getByLabel(/Đường dẫn liên kết/i).fill('https://facebook.com/annamcoffee/posts/demo-123');
      await modal.getByRole('button', { name: 'Xác nhận đã đăng' }).click();

      await expect(modal).not.toBeVisible({ timeout: 6000 });
      // Trạng thái chuyển sang Đã đăng
      await expect(page.locator('text=Đã đăng').first()).toBeVisible({ timeout: 6000 });
    }
  });
});
