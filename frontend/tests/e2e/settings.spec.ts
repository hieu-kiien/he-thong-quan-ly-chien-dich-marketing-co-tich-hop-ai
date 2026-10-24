import { test, expect } from '@playwright/test';
import { loginAsManager, loginAsMarketer } from './helpers';

test.describe('Phân hệ Cài đặt Hệ thống & Quản trị (Settings & Admin)', () => {
  test('Quản lý (MANAGER) có thể truy cập đầy đủ 5 tab cài đặt và xem trạng thái AI', async ({ page }) => {
    await loginAsManager(page);
    await page.goto('/settings');
    await expect(page.locator('h1')).toContainText('Cài đặt hệ thống');

    // 1. Kiểm tra đủ 5 tabs
    await expect(page.getByRole('tab', { name: 'Tài khoản cá nhân' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Người dùng' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Kênh tiếp thị' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Hồ sơ thương hiệu' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Trạng thái AI' })).toBeVisible();

    // 2. Chuyển sang tab Trạng thái AI
    await page.getByRole('tab', { name: 'Trạng thái AI' }).click();
    await expect(page.getByText('Trạng thái dịch vụ AI Runner')).toBeVisible();
    // Runner hiển thị sẵn sàng kết nối và model
    await expect(page.locator('text=Sẵn sàng')).toBeVisible({ timeout: 6000 });
    await expect(page.locator('body')).toContainText('fake-qa-runner');

    // 3. Chuyển sang tab Kênh tiếp thị
    await page.getByRole('tab', { name: 'Kênh tiếp thị' }).click();
    await expect(page.getByText('Facebook Fanpage')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'TikTok', exact: true })).toBeVisible();

    // 4. Chuyển sang tab Hồ sơ thương hiệu
    await page.getByRole('tab', { name: 'Hồ sơ thương hiệu' }).click();
    await expect(page.getByText('Từ cấm theo quy định thương hiệu')).toBeVisible();
    await expect(page.locator('body')).toContainText('cam kết 100%');

    // 5. Chuyển sang tab Người dùng
    await page.getByRole('tab', { name: 'Người dùng' }).click();
    await expect(page.getByText('Danh sách người dùng')).toBeVisible();
    await expect(page.locator('body')).toContainText('Nguyễn Văn Quản Lý');
    await expect(page.locator('body')).toContainText('Trần Thị Lan Anh');
  });

  test('Nhân viên (MARKETER) chỉ thấy tab Tài khoản cá nhân, bị ẩn các tab quản trị', async ({ page }) => {
    await loginAsMarketer(page);
    await page.goto('/settings');
    await expect(page.locator('h1')).toContainText('Cài đặt hệ thống');

    // Marketer thấy tab Tài khoản
    await expect(page.getByRole('tab', { name: 'Tài khoản cá nhân' })).toBeVisible();

    // Marketer KHÔNG thấy các tab quản trị
    await expect(page.getByRole('tab', { name: 'Người dùng' })).not.toBeVisible();
    await expect(page.getByRole('tab', { name: 'Kênh tiếp thị' })).not.toBeVisible();
    await expect(page.getByRole('tab', { name: 'Hồ sơ thương hiệu' })).not.toBeVisible();
    await expect(page.getByRole('tab', { name: 'Trạng thái AI' })).not.toBeVisible();
  });
});
