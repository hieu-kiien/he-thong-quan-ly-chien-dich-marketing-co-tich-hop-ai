import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';

describe('MarketFlow AI Live Production E2E Suite (marketing.kienhieu.id.vn)', { serial: true }, () => {
  test('1. Xác thực Đăng nhập 60fps & Tổng quan Điều hành Chiến dịch (Dashboard)', async ({
    app,
    screen,
    browser,
  }) => {
    await app.open('/');
    await expect(screen.getByRole('tab', 'Đăng nhập', { exact: false })).toBeVisible({ timeout: 20_000 });

    // Kiểm tra chuyển đổi mượt giữa Đăng nhập <-> Đăng ký tài khoản
    await screen.getByRole('tab', 'Đăng ký tài khoản', { exact: false }).tap();
    const fullNameInput = browser.locator('#register-fullname');
    await fullNameInput.fill('Kiểm thử E2E Production');

    // Quay về tab Đăng nhập và dùng nút 1-Click Quick-Login Quản lý
    await screen.getByRole('tab', 'Đăng nhập', { exact: false }).tap();
    await screen.getByRole('button', 'Quản lý', { exact: true }).tap();
    await browser.locator('button[type="submit"]').tap();

    // Xác nhận vào Dashboard và hiển thị đầy đủ 3 chế độ xem trên thanh điều hướng
    await expect(screen.getByTestId('dashboard-tab-overview')).toBeVisible({ timeout: 25_000 });
    await expect(screen.getByTestId('dashboard-tab-ad-accounts')).toBeVisible();
    await expect(screen.getByTestId('dashboard-tab-channels')).toBeVisible();

    // Kiểm tra chuyển sang tab So sánh kênh & Mẫu bài rồi quay về
    await screen.getByTestId('dashboard-tab-channels').tap();
    await expect(
      screen.getByRole('heading', 'Phân Tích Xu Hướng & Phân Bổ Đa Kênh', { exact: false })
    ).toBeVisible();
    await screen.getByTestId('dashboard-tab-overview').tap();
  });

  test('2. Kiểm thử toàn diện 4 Phân hệ Thương mại hóa SaaS & MarTech Thực chiến Việt Nam', async ({
    screen,
  }) => {
    // Mở trung tâm Tài khoản QC, KOL/KOC & POS trên Dashboard
    await screen.getByTestId('dashboard-tab-ad-accounts').tap();

    // Phân hệ 1: Tài khoản QC & POS Webhook
    await screen.getByRole('button', '1. Tài khoản QC & POS Webhook', { exact: false }).tap();
    await expect(
      screen.getByText('Tài khoản quảng cáo, Tự động đăng bài Fanpage & Bảo mật POS Webhook', { exact: false }).first()
    ).toBeVisible({ timeout: 15_000 });

    // Mở form Khóa bảo mật POS Webhook & Zalo/Email API
    const webhookBtn = screen.getByRole('button', 'Khóa Webhook & Zalo/Email API', { exact: false }).first();
    await webhookBtn.tap();
    await expect(
      screen.getByText('Cấu hình Khóa bảo mật POS Webhook', { exact: false }).first()
    ).toBeVisible();

    // Bấm Đồng bộ chi phí & đơn ngay (API /ad-accounts/sync)
    const syncBtn = screen.getByRole('button', 'Đồng bộ chi phí & đơn ngay', { exact: false }).first();
    await syncBtn.tap();

    // Phân hệ 2: KOL Affiliate & Điểm Hòa Vốn Sàn TMĐT (TikTok Shop / Shopee Break-Even ROAS)
    await screen.getByRole('button', '2. KOL Affiliate & Điểm Hòa Vốn Sàn TMĐT', { exact: false }).tap();
    await expect(
      screen.getByRole('heading', 'Bộ Tính Điểm Hòa Vốn (Break-Even ROAS)', { exact: false })
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      screen.getByText('ROAS Hòa Vốn Bắt Buộc', { exact: false }).first()
    ).toBeVisible();
    await expect(
      screen.getByRole('heading', 'Chiến dịch thuê KOL / KOC & Đối tác Affiliate bên thứ 3', { exact: false })
    ).toBeVisible();

    // Phân hệ 3: Phễu Zalo ZNS / Messenger 24h & Lịch Mùa Vụ Mega Sale Việt Nam
    await screen.getByRole('button', '3. Phễu Zalo ZNS / Messenger & Lịch Mega Sale VN', { exact: false }).tap();
    await expect(
      screen.getByRole('heading', 'Phễu Chốt Đơn Tin Nhắn', { exact: false })
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      screen.getByRole('heading', '1-Click Kịch Bản Mùa Vụ & Khung Giờ Vàng Mega Sale Việt Nam', { exact: false })
    ).toBeVisible();

    // Phân hệ 4: Gói Cước SaaS & Thanh toán VietQR Napas 247 / SePay Webhook
    await screen.getByRole('button', '4. Gói Cước SaaS & VietQR', { exact: false }).first().tap();
    await expect(
      screen.getByRole('heading', 'Gói Cước SaaS & Cổng Thanh Toán Tự Động VietQR Napas 247', { exact: false })
    ).toBeVisible({ timeout: 15_000 });
  });

  test('3. Kiểm thử điều hướng 7 Phân hệ Sidebar (Chiến dịch, AI Studio, Duyệt bài, Việc cần làm, Lịch đăng, Cài đặt)', async ({
    screen,
    browser,
  }) => {
    // 1. Danh sách chiến dịch
    await screen.getByTestId('sidebar-tab-campaigns').tap();
    await expect(screen.getByText('Chiến dịch', { exact: false }).first()).toBeVisible({ timeout: 15_000 });

    // 2. Viết bài & Tạo mẫu QC (AI Studio)
    await screen.getByTestId('sidebar-tab-ai_studio').tap();
    await expect(
      screen.getByRole('heading', 'Viết bài & Tạo mẫu quảng cáo', { exact: false })
    ).toBeVisible({ timeout: 15_000 });
    await screen.getByTestId('studio-tab-angle-matrix').tap();
    await screen.getByTestId('studio-tab-persona-critic').tap();

    // 3. Duyệt bài & Từ cấm (Review Queue)
    await screen.getByTestId('sidebar-tab-reviews').tap();
    await expect(screen.getByText('Duyệt', { exact: false }).first()).toBeVisible({ timeout: 15_000 });

    // 4. Việc cần làm (My Tasks)
    await screen.getByTestId('sidebar-tab-my_tasks').tap();
    await expect(screen.getByText('Việc', { exact: false }).first()).toBeVisible({ timeout: 15_000 });

    // 5. Lịch đăng bài (Marketing Calendar)
    await screen.getByTestId('sidebar-tab-calendar').tap();
    await expect(screen.getByText('Lịch', { exact: false }).first()).toBeVisible({ timeout: 15_000 });

    // 6. Cài đặt & Thương hiệu (Settings + BYOK Custom Model Input + RBAC)
    await screen.getByTestId('sidebar-tab-settings').tap();
    const customModelInput = browser.locator('#byok-custom-model-input');
    await customModelInput.waitFor({ state: 'visible', timeout: 15_000 });
    await customModelInput.fill('gemini-3.8-flash');

    const rbacTab = screen.getByRole('button', 'Hồ sơ & Phân quyền', { exact: false }).first();
    if (await rbacTab.isVisible()) {
      await rbacTab.tap();
      await expect(
        screen.getByText('Quản trị Nhân sự & Cấp phát Tài khoản', { exact: false }).first()
      ).toBeVisible();
    }
  });
});
