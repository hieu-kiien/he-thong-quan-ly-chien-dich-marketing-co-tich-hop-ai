import { test, expect } from '@playwright/test';
import * as path from 'path';
import { loginAsManager } from './helpers';

test.describe('Phân hệ Quản lý Số liệu & Nhập CSV (Metrics & CSV Import)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsManager(page);
    await page.goto('/campaigns/1');
    const tabMetrics = page.getByRole('tab', { name: 'Số liệu & Báo cáo' });
    await tabMetrics.click();
    await expect(page.getByText('Lịch sử số liệu thực tế')).toBeVisible();
  });

  test('Kiểm tra quy tắc ràng buộc logic số liệu khi nhập tay (Clicks <= Views, Conversions <= Clicks)', async ({ page }) => {
    // 1. Mở modal nhập số liệu
    await page.getByRole('button', { name: 'Nhập số liệu' }).click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // 2. Chọn kênh và ngày
    await modal.locator('select').selectOption({ index: 1 });
    await modal.locator('input[type="date"]').fill('2026-11-05');

    // 3. Nhập vi phạm Clicks > Views (150 > 100)
    await modal.getByLabel(/Lượt xem/i).fill('100');
    await modal.getByLabel(/Lượt bấm/i).fill('150');
    await modal.getByRole('button', { name: 'Lưu số liệu' }).click();

    // Hệ thống chặn và báo lỗi
    const errorAlert = modal.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Lượt click không thể lớn hơn lượt xem');

    // 4. Nhập vi phạm Conversions > Clicks (80 > 50)
    await modal.getByLabel(/Lượt bấm/i).fill('50');
    await modal.getByLabel(/Chuyển đổi/i).fill('80');
    await modal.getByRole('button', { name: 'Lưu số liệu' }).click();

    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Lượt chuyển đổi không thể lớn hơn lượt click');

    // 5. Nhập số liệu hợp lệ và lưu
    await modal.getByLabel(/Chuyển đổi/i).fill('12');
    await modal.locator('input[inputmode="numeric"]').last().fill('500000');
    await modal.getByRole('button', { name: 'Lưu số liệu' }).click();

    // Modal đóng lại và cập nhật bảng số liệu
    await expect(modal).not.toBeVisible({ timeout: 6000 });
  });

  test('Xem trước (Preview) và Xác nhận lưu (Commit) tệp CSV số liệu', async ({ page }) => {
    // 1. Mở dialog Nhập CSV
    await page.getByRole('button', { name: 'Nhập CSV' }).click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // 2. Tải tệp sample_ads_report.csv
    const csvFilePath = path.resolve('..', 'sample_ads_report.csv');
    const fileInput = modal.locator('input[type="file"]');
    await fileInput.setInputFiles(csvFilePath);

    // 3. Kiểm tra nút Xác nhận nhập xuất hiện với số dòng hợp lệ
    const commitBtn = modal.getByRole('button', { name: /Xác nhận nhập \(\d+ dòng hợp lệ\)/i });
    await expect(commitBtn).toBeVisible({ timeout: 8000 });

    // 4. Bấm Xác nhận nhập
    await commitBtn.click();

    // 5. Thành công: modal đóng lại
    await expect(modal).not.toBeVisible({ timeout: 8000 });
  });
});
