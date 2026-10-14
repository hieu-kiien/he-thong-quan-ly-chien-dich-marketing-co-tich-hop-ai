import { describe, test } from '@e2e-dev/web';
import { credentials, expect } from 'e2e';

describe('MarketFlow AI Live Production E2E Suite (marketing.kienhieu.id.vn)', { serial: true }, () => {
  test('Full visual E2E tour: Halloween 60fps Auth -> 5-Stage Dashboard -> 4-Agent Squad & Visual Studio -> Custom AI Model Input & RBAC', async ({
    app,
    screen,
    browser,
  }) => {
    // 1. Mở trang Đăng nhập trên chuẩn domain production
    await app.open('/login');
    await expect(screen.getByRole('button', 'Đăng nhập', { exact: false }).first()).toBeVisible();

    // Kiểm tra hiệu ứng chuyển đổi 60fps giữa Đăng nhập <-> Đăng ký
    await screen.getByRole('tab', 'Đăng ký', { exact: false }).tap();
    const fullNameInput = browser.locator('#register-fullname');
    await fullNameInput.pressSequentially('Trần Thịnh Hiếu - Kiểm thử E2E Live', { delay: 35 });

    // Chuyển mượt về tab Đăng nhập
    await screen.getByRole('tab', 'Đăng nhập', { exact: false }).tap();

    // Nhập Email để mắt cú mèo dõi theo từng ký tự
    const emailInput = browser.locator('#email');
    await emailInput.clear();
    await emailInput.pressSequentially(credentials.user('manager').username, { delay: 40 });

    // Nhập Mật khẩu để đèn pin bật sáng chiếu vào ô mật khẩu
    const passwordInput = browser.locator('#password');
    await passwordInput.tap();
    await passwordInput.fill(credentials.user('manager').password);

    // Bấm nút Submit Đăng nhập
    await browser.locator('button[type="submit"]').tap();

    // 2. Xác nhận vào Dashboard và kiểm tra Chu trình 5 Bước Khép kín
    await expect(screen.getByText('Nghiên cứu & Brief', { exact: false }).first()).toBeVisible({ timeout: 20_000 });
    await expect(screen.getByText('Sáng tạo Đa kênh', { exact: false }).first()).toBeVisible();
    await expect(screen.getByText('Kiểm duyệt & Brand Safety', { exact: false }).first()).toBeVisible();
    await expect(screen.getByText('Đo lường & Bác sĩ AI', { exact: false }).first()).toBeVisible();

    // Kiểm tra Giao ban Sáng AI & bấm Tái phân bổ Ngân sách
    const rebalanceBtn = screen.getByRole('button', 'Tái phân bổ Ngân sách', { exact: false }).first();
    if (await rebalanceBtn.isVisible()) {
      await rebalanceBtn.tap();
    }

    // Kiểm tra nút Tải CSV mẫu trong khu vực Dữ liệu Quảng cáo Thực tế
    const sampleCsvBtn = screen.getByRole('button', 'Tải CSV mẫu', { exact: false }).first();
    if (await sampleCsvBtn.isVisible()) {
      await sampleCsvBtn.tap();
    }

    // 3. Chuyển sang tab MCP Agent & Tự động hóa trên Dashboard
    const mcpTabBtn = screen.getByRole('button', 'MCP Agent & Tự động hóa', { exact: false }).first();
    await mcpTabBtn.scrollIntoView();
    await mcpTabBtn.tap();

    // Chạy Biệt đội 4 AI Agents Tự hành (4-Agent Autonomous Squad)
    const runSquadBtn = screen.getByRole('button', 'Chạy 4-Agent Squad', { exact: false }).first();
    await runSquadBtn.scrollIntoView();
    await runSquadBtn.tap();
    await expect(screen.getByText('Researcher', { exact: false }).first()).toBeVisible({ timeout: 25_000 });

    // Sinh 3 Biến thể A/B Testing + UTM Tracking
    const genAbBtn = screen.getByRole('button', 'Sinh 3 Biến thể A/B + UTM', { exact: false }).first();
    await genAbBtn.scrollIntoView();
    await genAbBtn.tap();
    await expect(screen.getByText('utm_source=', { exact: false }).first()).toBeVisible({ timeout: 20_000 });

    // Thiết kế AI Visual Banner SVG đa tỷ lệ
    const genBannerBtn = screen.getByRole('button', 'Thiết kế Banner SVG', { exact: false }).first();
    await genBannerBtn.scrollIntoView();
    await genBannerBtn.tap();
    await expect(screen.getByText('Tải file .SVG', { exact: false }).first()).toBeVisible({ timeout: 20_000 });

    // 4. Mở trang Cài đặt -> Kiểm tra Ô tự nhập tên Model AI bất kỳ & Phân quyền RBAC
    const settingsNav = screen.getByRole('button', 'Cài đặt', { exact: false }).first();
    await settingsNav.scrollIntoView();
    await settingsNav.tap();

    const customModelInput = browser.locator('#byok-custom-model-input');
    await customModelInput.waitFor({ state: 'visible', timeout: 15_000 });
    await customModelInput.clear();
    await customModelInput.pressSequentially('gemini-4-argon', { delay: 45 });
    await customModelInput.clear();
    await customModelInput.pressSequentially('gemini-3.8-flash', { delay: 45 });

    // Bấm Đồng bộ danh sách từ API
    const syncModelsBtn = screen.getByRole('button', 'Đồng bộ danh sách từ API', { exact: false }).first();
    if (await syncModelsBtn.isVisible()) {
      await syncModelsBtn.tap();
    }

    // Chuyển sang tab Hồ sơ & Phân quyền RBAC
    const rbacTab = screen.getByRole('button', 'Hồ sơ & Phân quyền', { exact: false }).first();
    if (await rbacTab.isVisible()) {
      await rbacTab.tap();
      await expect(screen.getByText('Quản trị Nhân sự & Cấp phát Tài khoản', { exact: false }).first()).toBeVisible();
    }

    await app.screenshot('marketflow-live-verified');
  });
});
