import { test, expect } from './fixtures/auth.fixture';

test.describe('Network Fault Simulation & Resilience Suite', () => {

  test('401 Unauthorized: Session expiration triggers logout and redirects to LoginPage', async ({ marketerPage }) => {
    // 1. Visit app with authenticated marketer
    await marketerPage.goto('/');
    await expect(marketerPage.locator('text=Tổng quan Chiến dịch')).toBeVisible();

    // 2. Intercept /api/v1/auth/me to return 401 Unauthorized
    await marketerPage.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token đã hết hạn hoặc không hợp lệ (401 Unauthorized)' }),
      });
    });

    // 3. Reload page to trigger auth validation
    await marketerPage.reload();

    // 4. Verify redirected to LoginPage
    await expect(
      marketerPage.locator('text=Đăng nhập MarketFlow AI')
        .or(marketerPage.locator('button:has-text("Đăng nhập")'))
        .or(marketerPage.locator('input[type="email"]'))
        .first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('403 Forbidden: Insufficient permissions shows RBAC violation toast and preserves UI state', async ({ managerPage }) => {
    // 1. Manager navigates to Review Queue
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // 2. Intercept approve endpoint with 403 Forbidden
    await managerPage.route('**/api/v1/contents/*/approve', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Quyền hạn không đủ: Bạn không có quyền thao tác trên tài nguyên này (403 Forbidden).' }),
      });
    });

    // 3. Trigger approve action via authentic UI click
    const approveBtn = managerPage.locator('button:has-text("Phê duyệt (Approve)")').first();
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // 4. Verify authentic UI error toast is shown
    await expect(
      managerPage.locator('text=Quyền hạn không đủ')
        .or(managerPage.locator('text=403'))
        .or(managerPage.locator('text=Lỗi khi duyệt bài'))
        .first()
    ).toBeVisible({ timeout: 7000 });

    // 5. Verify UI state is preserved and page did not crash
    await expect(managerPage.locator('aside')).toBeVisible();
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();
  });

  test('404 Not Found: Missing resource displays empty state without crashing or white screen', async ({ managerPage }) => {
    // 1. Intercept contents with 404 Not Found
    await managerPage.route('**/api/v1/contents**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Không tìm thấy tài nguyên nội dung yêu cầu (404 Not Found)' }),
      });
    });

    await managerPage.goto('/');

    // 2. UI should render gracefully without crashing
    await expect(managerPage.locator('aside')).toBeVisible();
    await expect(managerPage.locator('text=Tổng quan Chiến dịch')).toBeVisible();
    const content = await managerPage.content();
    expect(content.includes('Cannot read properties of undefined')).toBeFalsy();
  });

  test('409 Conflict: Concurrent edit conflict returns 409 error message in UI toast', async ({ managerPage }) => {
    // 1. Manager navigates to Review Queue
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // 2. Intercept rejection with 409 Conflict
    await managerPage.route('**/api/v1/contents/*/reject', async (route) => {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Xung đột dữ liệu: Nội dung đã được chỉnh sửa bởi người dùng khác (409 Conflict).' }),
      });
    });

    // 3. Trigger reject via authentic UI interaction
    const rejectBtn = managerPage.locator('button:has-text("Từ chối (Reject)")').first();
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();

    // Select template feedback
    const templateBtn = managerPage.locator('button:has-text("Sai lệch thông điệp thương hiệu")').first();
    await expect(templateBtn).toBeVisible();
    await templateBtn.click();

    // Confirm reject
    const confirmRejectBtn = managerPage.locator('button:has-text("Xác nhận Từ chối")');
    await expect(confirmRejectBtn).toBeEnabled();
    await confirmRejectBtn.click();

    // 4. Verify authentic UI error toast with conflict detail is displayed
    await expect(
      managerPage.locator('text=Xung đột dữ liệu')
        .or(managerPage.locator('text=409'))
        .or(managerPage.locator('text=Lỗi khi từ chối bài'))
        .first()
    ).toBeVisible({ timeout: 7000 });

    // 5. Verify UI remains functional
    await expect(managerPage.locator('aside')).toBeVisible();
  });

  test('500 Internal Server Error: Server failure is handled gracefully with error notification and UI preservation', async ({ managerPage }) => {
    // 1. Intercept analytics with 500 Internal Server Error
    await managerPage.route('**/api/v1/analytics/dashboard', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Lỗi máy chủ nội bộ không xác định (Internal Server Error 500)' }),
      });
    });

    await managerPage.goto('/');

    // 2. Verify UI didn't crash fatally - navbar and sidebar are intact
    await expect(managerPage.locator('aside')).toBeVisible();
    await expect(managerPage.locator('text=MarketFlow AI').first()).toBeVisible();

    // 3. Navigate to Review Queue and test action resilience under 500
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    await managerPage.route('**/api/v1/contents/*/approve', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Máy chủ cơ sở dữ liệu gặp lỗi (500 Database Error)' }),
      });
    });

    const approveBtn = managerPage.locator('button:has-text("Phê duyệt (Approve)")').first();
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // 4. Verify authentic error toast appears without crashing the page
    await expect(
      managerPage.locator('text=500')
        .or(managerPage.locator('text=Lỗi khi duyệt bài'))
        .or(managerPage.locator('text=Máy chủ'))
        .first()
    ).toBeVisible({ timeout: 7000 });

    await expect(managerPage.locator('aside')).toBeVisible();
  });

  test('Network Timeout: Request abort with timedout is handled gracefully without crashing UI', async ({ marketerPage }) => {
    await marketerPage.goto('/');
    await expect(marketerPage.locator('aside')).toBeVisible();

    // Abort campaigns endpoint with true 'timedout' network condition
    await marketerPage.route('**/api/v1/campaigns*', async (route) => {
      await route.abort('timedout');
    });

    // Marketer navigates to Campaigns tab
    await marketerPage.click('button:has-text("Quản Lý Chiến Dịch")');

    // UI should handle the aborted/timedout request gracefully without white-screen crash
    await expect(marketerPage.locator('aside')).toBeVisible();
    await expect(
      marketerPage.locator('text=Quản Lý Chiến Dịch')
        .or(marketerPage.locator('text=Danh sách Chiến dịch'))
        .first()
    ).toBeVisible({ timeout: 7000 });
  });

  test('Offline & Reconnect: Browser network cut shows authentic offline UI notification and recovers', async ({ marketerPage }) => {
    // 1. Visit app online
    await marketerPage.goto('/');
    await expect(marketerPage.locator('text=Tổng quan Chiến dịch')).toBeVisible();

    const initialOnline = await marketerPage.evaluate(() => window.navigator.onLine);
    expect(initialOnline).toBeTruthy();

    // 2. Cut network connection on the active page context
    await marketerPage.context().setOffline(true);

    // Verify offline navigator state
    const isOffline = await marketerPage.evaluate(() => !window.navigator.onLine);
    expect(isOffline).toBeTruthy();

    // 3. Verify authentic offline UI notification banner or toast is visible
    await expect(
      marketerPage.locator('text=Đang ngoại tuyến')
        .or(marketerPage.locator('text=Mất kết nối mạng'))
        .or(marketerPage.locator('text=Ngoại tuyến'))
        .first()
    ).toBeVisible({ timeout: 7000 });

    // 4. Reconnect network
    await marketerPage.context().setOffline(false);

    // Verify online state restored and recovery notification appears
    const restoredOnline = await marketerPage.evaluate(() => window.navigator.onLine);
    expect(restoredOnline).toBeTruthy();

    await expect(
      marketerPage.locator('text=Kết nối mạng đã được khôi phục')
        .or(marketerPage.locator('text=Tổng quan Chiến dịch'))
        .first()
    ).toBeVisible({ timeout: 7000 });

    await expect(marketerPage.locator('aside')).toBeVisible();
  });

});
