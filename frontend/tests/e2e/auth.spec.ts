import { test, expect } from '@playwright/test';

test.describe('Phân hệ Xác thực & Phân quyền (Auth & Access Control)', () => {
  test('Đăng nhập thất bại khi sai mật khẩu và hiển thị thông báo tiếng Việt', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('Đăng nhập');

    await page.fill('input[type="email"]', 'manager@marketflow.vn');
    await page.fill('input[type="password"]', 'WrongPassword123');
    await page.click('button[type="submit"]');

    // Thông báo lỗi từ API
    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 5000 });
    await expect(errorAlert).toContainText('Email hoặc mật khẩu không đúng');
  });

  test('Đăng nhập thành công với vai trò Quản lý (MANAGER) và đăng xuất', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'manager@marketflow.vn');
    await page.fill('input[type="password"]', 'Manager@123');
    await page.click('button[type="submit"]');

    // Chuyển hướng tới dashboard
    await expect(page).toHaveURL(/\/(dashboard)?$/, { timeout: 10000 });
    await expect(page.locator('h1')).toContainText('Tổng quan');

    // Manager thấy mục "Duyệt nội dung" trong sidebar
    await expect(page.locator('aside nav')).toContainText('Duyệt nội dung');

    // Mở menu tài khoản từ header và đăng xuất
    const userMenuButton = page.locator('header').getByRole('button').filter({ hasText: 'Nguyễn Văn Quản Lý' });
    await expect(userMenuButton).toBeVisible();
    await userMenuButton.click();

    const logoutBtn = page.getByRole('menuitem', { name: 'Đăng xuất' });
    await expect(logoutBtn).toBeVisible();
    await logoutBtn.click();

    await expect(page).toHaveURL(/\/login/, { timeout: 8000 });
  });

  test('Đăng nhập với vai trò Nhân viên (MARKETER) không thấy menu Duyệt nội dung', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'marketer@marketflow.vn');
    await page.fill('input[type="password"]', 'Marketer@123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/(dashboard)?$/, { timeout: 10000 });
    await expect(page.locator('h1')).toContainText('Tổng quan');

    // Marketer KHÔNG thấy mục "Duyệt nội dung" trên thanh điều hướng
    const navText = await page.locator('aside nav').textContent();
    expect(navText).not.toContain('Duyệt nội dung');
  });

  test('Kiểm tra chặn đăng nhập sai nhiều lần (Rate Limit)', async ({ page }) => {
    await page.goto('/login');
    for (let i = 0; i < 5; i++) {
      await page.fill('input[type="email"]', 'ratelimit_flow@marketflow.vn');
      await page.fill('input[type="password"]', 'WrongPass');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(150);
    }
    // Lần thứ 6 sẽ bị rate limit HTTP 429
    await page.fill('input[type="email"]', 'ratelimit_flow@marketflow.vn');
    await page.fill('input[type="password"]', 'WrongPass');
    await page.click('button[type="submit"]');

    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 5000 });
    const text = await errorAlert.textContent();
    expect(text?.toLowerCase()).toContain('thử lại');
  });
});
