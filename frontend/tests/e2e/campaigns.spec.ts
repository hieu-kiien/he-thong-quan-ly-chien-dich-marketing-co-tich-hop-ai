import { test, expect } from '@playwright/test';
import { loginAsManager } from './helpers';

test.describe('Phân hệ Quản lý Chiến dịch (Campaigns Management)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsManager(page);
  });

  test('Danh sách chiến dịch, tìm kiếm và bộ lọc trạng thái', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('h1')).toContainText('Chiến dịch');

    // Chờ danh sách nạp từ seed demo
    const tableRows = page.locator('tbody tr');
    await expect(tableRows.first()).toBeVisible({ timeout: 5000 });
    const countInitial = await tableRows.count();
    expect(countInitial).toBeGreaterThanOrEqual(1);

    // Lọc theo từ khoá tìm kiếm
    const searchInput = page.getByPlaceholder('Tìm theo tên chiến dịch...');
    await searchInput.fill('Cold Brew');
    await page.waitForTimeout(500); // Chờ debounce 350ms
    await expect(page.locator('tbody')).toContainText('Cold Brew');

    // Xoá tìm kiếm
    await searchInput.fill('');
    await page.waitForTimeout(500);

    // Lọc theo trạng thái
    const statusSelect = page.locator('select').first();
    await statusSelect.selectOption('ACTIVE');
    await page.waitForTimeout(500);
    await expect(page.locator('tbody')).toContainText('Đang chạy');
  });

  test('Tạo mới chiến dịch với kiểm tra hợp lệ ngày kết thúc >= ngày bắt đầu', async ({ page }) => {
    await page.goto('/campaigns/new');
    await expect(page.locator('h1')).toContainText('Tạo chiến dịch mới');

    // 1. Điền các trường cơ bản
    await page.getByLabel(/Tên chiến dịch/i).fill('Chiến dịch Mùa Đông 2026');
    await page.getByLabel(/Mục tiêu/i).first().selectOption('SALES');
    await page.getByLabel(/Mục tiêu cụ thể/i).fill('Tăng doanh thu dòng cà phê nóng 25%');
    await page.getByLabel(/Đối tượng mục tiêu/i).fill('Khách hàng văn phòng và gia đình trẻ');
    await page.getByLabel(/Sản phẩm \/ dịch vụ/i).fill('Cà phê phin giấy An Nam');

    // Chọn ít nhất một kênh
    await page.locator('input[type="checkbox"]').first().check();

    // Điền ngày kết thúc nhỏ hơn ngày bắt đầu
    const startDateInput = page.getByLabel(/Ngày bắt đầu/i);
    const endDateInput = page.getByLabel(/Ngày kết thúc/i);

    await startDateInput.fill('2026-12-15');
    await endDateInput.fill('2026-12-01'); // Ngày kết thúc < ngày bắt đầu
    await page.getByRole('textbox', { name: 'Ngân sách', exact: true }).fill('15000000');

    // Bấm Tạo chiến dịch để kích hoạt validation
    await page.getByRole('button', { name: 'Tạo chiến dịch' }).click();

    // Hệ thống chặn và hiển thị lỗi validation tiếng Việt
    const errorAlert = page.locator('p[role="alert"]').first();
    await expect(errorAlert).toBeVisible({ timeout: 5000 });

    // Sửa lại ngày kết thúc hợp lệ
    await endDateInput.fill('2026-12-31');
    await page.getByRole('button', { name: 'Tạo chiến dịch' }).click();

    // Chuyển hướng thành công
    await expect(page).toHaveURL(/\/campaigns(\/\d+)?$/, { timeout: 10000 });
  });

  test('Xem chi tiết chiến dịch và chuyển đổi qua các tab', async ({ page }) => {
    await page.goto('/campaigns');
    // Bấm vào chiến dịch đầu tiên trong danh sách
    const firstCampaignLink = page.locator('tbody tr td a').first();
    await firstCampaignLink.click();

    await expect(page).toHaveURL(/\/campaigns\/\d+/, { timeout: 8000 });

    // Tab 2: Nội dung & Lịch
    const tabContents = page.getByRole('tab', { name: 'Nội dung & Lịch' });
    await tabContents.click();
    await expect(page.getByText('Danh sách nội dung')).toBeVisible();

    // Tab 3: Số liệu & Báo cáo
    const tabMetrics = page.getByRole('tab', { name: 'Số liệu & Báo cáo' });
    await tabMetrics.click();
    await expect(page.getByText('Lịch sử số liệu thực tế')).toBeVisible();

    // Tab 1: Thông tin chung
    const tabInfo = page.getByRole('tab', { name: 'Thông tin chung' });
    await tabInfo.click();
    await expect(page.getByText('Mục tiêu chiến dịch')).toBeVisible();
  });

  test('Xoá chiến dịch đã phát sinh dữ liệu bị chặn (409 Conflict)', async ({ page }) => {
    await page.goto('/campaigns');
    // Tìm chiến dịch có dữ liệu (seed campaign Cold Brew)
    const searchInput = page.getByPlaceholder('Tìm theo tên chiến dịch...');
    await searchInput.fill('Cold Brew');
    await page.waitForTimeout(500);

    // Bấm nút xoá trên dòng chiến dịch Cold Brew
    const deleteBtn = page.locator('tbody tr').first().getByRole('button', { name: 'Xoá chiến dịch' });
    await deleteBtn.click();

    // Hộp thoại xác nhận xoá mở ra
    const confirmModal = page.locator('[role="dialog"]');
    await expect(confirmModal).toBeVisible();

    // Bấm nút Xác nhận xoá trong ConfirmDialog
    const submitConfirmBtn = confirmModal.getByRole('button', { name: 'Xác nhận xoá' });
    await submitConfirmBtn.click();

    // Hệ thống chặn xoá và hiển thị cảnh báo xung đột dữ liệu (CONTRACT §4)
    const conflictWarning = page.locator('text=không thể xoá');
    await expect(conflictWarning).toBeVisible({ timeout: 6000 });

    // Hộp thoại có nút chuyển trạng thái sang Đã huỷ
    const cancelOptionBtn = confirmModal.getByRole('button', { name: 'Chuyển trạng thái sang Đã huỷ' });
    await expect(cancelOptionBtn).toBeVisible();
  });
});
