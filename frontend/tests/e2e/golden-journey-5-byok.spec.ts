import { test, expect } from './fixtures/auth.fixture';

test.describe('Golden Journey 5: BYOK Key Lifecycle (Admin/Agency Manager)', () => {

  test('BYOK Vault: Full Key Lifecycle - Validate, Test Connection, Save AES-128, Toggle & Revoke', async ({ agencyManagerPage }) => {
    // 1. Navigate to Settings -> BYOK tab
    await agencyManagerPage.goto('/');
    
    // Click Settings menu item in Sidebar
    const settingsMenu = agencyManagerPage.locator('aside button, aside a').filter({ hasText: 'Cài Đặt & Brand Kit' });
    await expect(settingsMenu).toBeVisible();
    await settingsMenu.click();

    // Verify Settings page loaded
    await expect(agencyManagerPage.locator('text=Trung tâm Cài đặt & Quản trị Doanh nghiệp')).toBeVisible();
    await expect(agencyManagerPage.locator('text=Cấu hình Khóa API Riêng (Bring Your Own Key - BYOK)')).toBeVisible();

    // 2. Submit invalid API key -> validation fails with informative error message
    const keyInput = agencyManagerPage.locator('input[placeholder*="AIzaSy..."]');
    await expect(keyInput).toBeVisible();
    await keyInput.fill('invalid_gemini_key_xyz');

    const testBtn = agencyManagerPage.locator('button:has-text("Kiểm tra kết nối trực tiếp")');
    await expect(testBtn).toBeVisible();
    await testBtn.click();

    // Verify error feedback
    await expect(
      agencyManagerPage.locator('text=Kiểm tra kết nối thất bại')
        .or(agencyManagerPage.locator('text=API Key không hợp lệ'))
        .first()
    ).toBeVisible({ timeout: 5000 });

    // 3. Submit valid mock key -> connection test succeeds with latency display
    await keyInput.fill('AIzaSyD-mock-gemini-valid-key-2026');
    await testBtn.click();

    // Verify success feedback with latency
    await expect(agencyManagerPage.locator('text=Kết nối thành công').first()).toBeVisible({ timeout: 5000 });
    await expect(agencyManagerPage.locator('text=124ms').or(agencyManagerPage.locator('text=ms)')).first()).toBeVisible();

    // 4. Save Key -> displays AES-128 masked representation
    const saveBtn = agencyManagerPage.locator('button:has-text("Lưu Cấu Hình Khóa AI")');
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Verify success message
    await expect(
      agencyManagerPage.locator('text=Khóa API đã được mã hóa Fernet AES-128 và lưu trữ thành công!').first()
    ).toBeVisible({ timeout: 5000 });

    // Verify key in active keys table with masked preview
    const keysTable = agencyManagerPage.locator('table');
    await expect(keysTable).toBeVisible();
    await expect(keysTable.locator('text=AIzaSy...').first()).toBeVisible();
    await expect(keysTable.locator('text=GEMINI').first()).toBeVisible();
    await expect(keysTable.locator('text=Đang hoạt động').first()).toBeVisible();

    // 5. Toggle Key (Pause/Resume) - Genuine assertion without conditional skips
    const toggleBtn = keysTable.locator('button:has-text("Tắt")').first();
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();
    await expect(keysTable.locator('text=Tạm dừng').or(keysTable.locator('button:has-text("Bật")')).first()).toBeVisible({ timeout: 5000 });

    // 6. Revoke/Delete Key
    agencyManagerPage.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    const deleteBtn = keysTable.locator('button:has-text("Xóa")').first();
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();

    // Verify deletion notification or table updated
    await expect(
      agencyManagerPage.locator('text=Đã xóa cấu hình khóa AI thành công!')
        .or(agencyManagerPage.locator('text=Chưa có khóa tùy biến nào'))
    ).toBeVisible({ timeout: 5000 });
  });

  test('BYOK Vault: Empty key input prevents test connection and displays validation error', async ({ agencyManagerPage }) => {
    await agencyManagerPage.goto('/');
    const settingsMenu = agencyManagerPage.locator('aside button, aside a').filter({ hasText: 'Cài Đặt & Brand Kit' });
    await settingsMenu.click();

    // Empty input -> test connection button is disabled or triggers validation
    const keyInput = agencyManagerPage.locator('input[placeholder*="AIzaSy..."]');
    await keyInput.fill('');

    const testBtn = agencyManagerPage.locator('button:has-text("Kiểm tra kết nối trực tiếp")');
    await expect(testBtn).toBeDisabled();
  });

});
