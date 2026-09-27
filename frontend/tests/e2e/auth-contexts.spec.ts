import { test, expect } from './fixtures/auth.fixture';

test.describe('RBAC 4 Distinct Browser Contexts & Storage States', () => {

  test('Marketer context loads with MARKETER role and specific capabilities', async ({ marketerPage }) => {
    // 1. Verify user profile in sidebar
    await expect(marketerPage.locator('text=Chuyên Viên Tiếp Thị').first()).toBeVisible();
    await expect(marketerPage.locator('text=marketer@gmail.com').first()).toBeVisible();

    // 2. Verify Role Badge
    const roleBadge = marketerPage.locator('aside span:has-text("Marketer")').first();
    await expect(roleBadge).toBeVisible();

    // 3. Verify Marketer sees dashboard
    await expect(marketerPage.locator('text=Tổng quan Chiến dịch')).toBeVisible();

    // 4. Marketer can access AI Studio tab
    await marketerPage.click('button:has-text("Xưởng Sáng Tạo AI")');
    await expect(marketerPage.locator('text=AI Marketing Copilot').first()).toBeVisible();
  });

  test('Manager context loads with MANAGER role and approval badges', async ({ managerPage }) => {
    // 1. Verify user profile in sidebar
    await expect(managerPage.locator('text=Quản Lý Chiến Dịch').first()).toBeVisible();
    await expect(managerPage.locator('text=manager@gmail.com').first()).toBeVisible();

    // 2. Verify Role Badge shows Manager
    const roleBadge = managerPage.locator('aside span:has-text("Quản lý (Manager)")').first();
    await expect(roleBadge).toBeVisible();

    // 3. Manager has "Duyệt bài" badge on review queue menu
    await expect(managerPage.locator('aside span:has-text("Duyệt bài")').first()).toBeVisible();

    // 4. Manager can access Review Queue directly
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();
  });

  test('Client Approver context loads with CLIENT_APPROVER role and client scope', async ({ approverPage }) => {
    // 1. Verify user profile in sidebar
    await expect(approverPage.locator('text=Đại Diện Khách Hàng (Approver)').first()).toBeVisible();
    await expect(approverPage.locator('text=approver@gmail.com').first()).toBeVisible();

    // 2. Verify Role Badge shows Client Approver
    const roleBadge = approverPage.locator('aside span:has-text("Client Approver")').first();
    await expect(roleBadge).toBeVisible();

    // 3. Client Approver can view and review content
    await approverPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(approverPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();
  });

  test('Agency Manager context loads with AGENCY_MANAGER role and full permissions', async ({ agencyManagerPage }) => {
    // 1. Verify user profile in sidebar
    await expect(agencyManagerPage.locator('text=Giám Đốc Agency (Agency Mgr)').first()).toBeVisible();
    await expect(agencyManagerPage.locator('text=agency_mgr@gmail.com').first()).toBeVisible();

    // 2. Verify Role Badge shows Agency Manager
    const roleBadge = agencyManagerPage.locator('aside span:has-text("Agency Manager")').first();
    await expect(roleBadge).toBeVisible();

    // 3. Agency Manager also has "Duyệt bài" badge
    await expect(agencyManagerPage.locator('aside span:has-text("Duyệt bài")').first()).toBeVisible();

    // 4. Agency Manager can access Settings & Brand Kit
    await agencyManagerPage.click('button:has-text("Cài Đặt & Brand Kit")');
    await expect(agencyManagerPage.locator('text=Trung tâm Cài đặt').first()).toBeVisible();
  });

});
