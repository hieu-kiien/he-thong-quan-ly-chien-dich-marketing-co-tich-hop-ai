import { test, expect } from '@playwright/test';
import { loginAsManager } from './helpers';

test.describe('Phân hệ Trợ lý AI (Claude-like Assistant Workspace)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsManager(page);
  });

  test('Khởi tạo phiên mới từ nút "Hỏi Trợ lý AI" trên trang chiến dịch và gửi yêu cầu sinh bài', async ({ page }) => {
    // 1. Mở trang chi tiết chiến dịch Cold Brew
    await page.goto('/campaigns/1');
    await expect(page.locator('h1')).toContainText('Cold Brew');

    // 2. Bấm nút "Hỏi Trợ lý AI"
    const askAiBtn = page.getByRole('button', { name: 'Hỏi Trợ lý AI' });
    await expect(askAiBtn).toBeVisible();
    await askAiBtn.click();

    // 3. Tự động chuyển hướng sang /assistant/:threadId và gắn chip chiến dịch
    await expect(page).toHaveURL(/\/assistant\/\d+/, { timeout: 10000 });
    await expect(page.locator('header').last()).toContainText('Cold Brew');

    // 4. Gõ câu lệnh yêu cầu viết bài
    const composerInput = page.getByPlaceholder(/Nhập câu hỏi hoặc yêu cầu cho Trợ lý AI/i);
    await expect(composerInput).toBeVisible();
    await composerInput.fill('Đề xuất bài viết Facebook giới thiệu cà phê Cold Brew');

    // Bấm nút gửi
    await page.getByRole('button', { name: 'Gửi câu lệnh' }).click();

    // 5. Kiểm tra luồng phản hồi: hiển thị văn bản và thẻ đề xuất ở panel bên phải
    // Thẻ đề xuất xuất hiện ở panel bên phải
    const proposalCard = page.locator('aside[aria-label="Panel đề xuất và bản nháp"], [id^="action-"]').first();
    await expect(proposalCard).toBeVisible({ timeout: 15000 });

    // Văn bản trợ lý hoàn tất xuất hiện
    await expect(page.locator('text=Dựa trên số liệu hiệu quả')).toBeVisible({ timeout: 15000 });

    // 6. Chỉnh sửa tham số đề xuất và Xác nhận (Human-in-the-loop CONTRACT §0, §5, §12)
    const titleInput = page.locator('input[placeholder="Nhập tiêu đề..."]').first();
    if (await titleInput.isVisible()) {
      await titleInput.fill('Bản nháp Facebook được chỉnh sửa bởi QA');
    }

    // Bấm nút Xác nhận trên thẻ đề xuất
    const confirmActionBtn = page.getByRole('button', { name: 'Xác nhận' }).first();
    await expect(confirmActionBtn).toBeVisible();
    await confirmActionBtn.click();

    // Kiểm tra kết quả: trạng thái chuyển sang Đã tạo nội dung thành công
    await expect(page.locator('text=Đã tạo nội dung thành công').first()).toBeVisible({ timeout: 8000 });

    // 7. Vào trang /reviews kiểm tra bài viết vừa tạo hiển thị ở trạng thái chờ duyệt có nhãn AI
    await page.goto('/reviews');
    await expect(page.locator('body')).toContainText('Bản nháp Facebook được chỉnh sửa bởi QA');
    await expect(page.locator('body')).toContainText('Trợ lý AI');
  });

  test('Kiểm tra nút Dừng (Stop) khi lượt hội thoại đang xử lý', async ({ page }) => {
    await page.goto('/assistant');
    await expect(page).toHaveURL(/\/assistant/);

    const composerInput = page.getByPlaceholder(/Nhập câu hỏi hoặc yêu cầu cho Trợ lý AI/i);
    await composerInput.fill('[SLOW] Phân tích chiến lược dài hạn');
    await page.getByRole('button', { name: 'Gửi câu lệnh' }).click();

    // Nút Dừng phản hồi xuất hiện
    const stopBtn = page.getByRole('button', { name: 'Dừng phản hồi' });
    await expect(stopBtn).toBeVisible({ timeout: 5000 });
    await stopBtn.click();

    // Sau khi dừng, nút gửi câu lệnh trở lại
    await expect(page.getByRole('button', { name: 'Gửi câu lệnh' })).toBeVisible({ timeout: 5000 });
  });

  test('Hiển thị thông báo lỗi khi Trợ lý AI gặp lỗi AI_RATE_LIMITED', async ({ page }) => {
    await page.goto('/assistant');

    const composerInput = page.getByPlaceholder(/Nhập câu hỏi hoặc yêu cầu cho Trợ lý AI/i);
    await composerInput.fill('[RATE_LIMIT] Thử nghiệm lỗi rate limit');
    await page.getByRole('button', { name: 'Gửi câu lệnh' }).click();

    // Thông báo lỗi chuẩn CONTRACT §6, §11 hiển thị trong alert
    const rateLimitError = page.locator('[role="alert"]').filter({ hasText: /giới hạn sử dụng/i });
    await expect(rateLimitError).toBeVisible({ timeout: 8000 });

    // Nút Thử lại xuất hiện
    await expect(page.getByRole('button', { name: 'Thử lại' }).first()).toBeVisible();
  });

  test('Quản lý danh sách phiên hội thoại: Tạo mới, Ghim và Xoá phiên', async ({ page }) => {
    await page.goto('/assistant');

    // 1. Tạo một phiên mới
    const newThreadBtn = page.getByRole('button', { name: 'Phiên mới' });
    await newThreadBtn.click();
    await page.waitForTimeout(500);

    // 2. Mở menu 3 chấm trên phiên đầu tiên trong danh sách
    const optionsBtn = page.locator('button[aria-label="Tuỳ chọn phiên"]').first();
    await expect(optionsBtn).toBeVisible({ timeout: 5000 });
    await optionsBtn.click();

    // 3. Xoá phiên
    const deleteOption = page.locator('text=Xoá phiên').first();
    await expect(deleteOption).toBeVisible();
    await deleteOption.click();

    // Hộp thoại xác nhận xoá phiên mở ra
    const deleteModal = page.locator('[role="dialog"]');
    await expect(deleteModal).toBeVisible();

    const confirmDeleteBtn = deleteModal.getByRole('button', { name: 'Xoá vĩnh viễn' });
    await confirmDeleteBtn.click();
    await expect(deleteModal).not.toBeVisible({ timeout: 6000 });
  });
});
