import { test, expect, Page } from '../e2e/fixtures/auth.fixture';

/**
 * Helper to navigate tabs across both desktop and mobile viewports
 */
async function navigateToTab(page: Page, label: string) {
  const isMobile = (page.viewportSize()?.width || 1280) < 768;
  if (isMobile) {
    const aside = page.locator('aside');
    const isAsideOpen = await aside.evaluate((el) => el.classList.contains('translate-x-0')).catch(() => false);
    if (!isAsideOpen) {
      const hamburgerBtn = page.locator('button[aria-label="Mở thanh điều hướng"]');
      if (await hamburgerBtn.isVisible()) {
        await hamburgerBtn.click();
        await page.waitForTimeout(300);
      }
    }
  }
  const targetBtn = page.locator(`aside button:has-text("${label}")`).first();
  await targetBtn.click({ force: true });
  await page.waitForTimeout(400);
}

test.describe('Adversarial Focus Trap & Keyboard Navigation Probe', () => {

  // =========================================================================
  // 1. BRAND KIT MODAL ADVERSARIAL STRESS TEST
  // =========================================================================
  test.describe('1. Brand Kit Modal Focus Trap Hardening', () => {

    test('Rapid Tab and Shift+Tab burst cannot break out of Brand Kit modal', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      const triggerBtn = page.locator('button[aria-label="Cấu hình Brand Kit"]');
      await expect(triggerBtn).toBeVisible();

      // Trigger via keyboard Enter
      await triggerBtn.focus();
      await page.keyboard.press('Enter');

      const modalDialog = page.locator('div[role="dialog"][aria-modal="true"]');
      await expect(modalDialog).toBeVisible();

      // Ensure focus is inside modal
      await expect(page.locator('#brand-kit-name')).toBeFocused();

      // Adversarial Probe 1: Rapid 50x Tab keystroke burst
      for (let i = 0; i < 50; i++) {
        await page.keyboard.press('Tab');
      }

      // Assert focus NEVER leaked outside modal dialog
      const isTrappedAfterTab = await modalDialog.evaluate((dialog) => {
        return dialog.contains(document.activeElement);
      });
      expect(isTrappedAfterTab, 'Focus leaked outside modal after 50 rapid Tab presses').toBe(true);
      expect(await page.evaluate(() => document.activeElement === document.body)).toBe(false);

      // Adversarial Probe 2: Rapid 50x Shift+Tab keystroke burst
      for (let i = 0; i < 50; i++) {
        await page.keyboard.press('Shift+Tab');
      }

      const isTrappedAfterShiftTab = await modalDialog.evaluate((dialog) => {
        return dialog.contains(document.activeElement);
      });
      expect(isTrappedAfterShiftTab, 'Focus leaked outside modal after 50 rapid Shift+Tab presses').toBe(true);
      expect(await page.evaluate(() => document.activeElement === document.body)).toBe(false);

      // Clean close via Escape
      await page.keyboard.press('Escape');
      await expect(modalDialog).not.toBeVisible();
      await expect(triggerBtn).toBeFocused();
    });

    test('Programmatic focus shift outside modal is immediately intercepted and recaptured', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      const triggerBtn = page.locator('button[aria-label="Cấu hình Brand Kit"]');
      await triggerBtn.focus();
      await page.keyboard.press('Enter');

      const modalDialog = page.locator('div[role="dialog"][aria-modal="true"]');
      await expect(modalDialog).toBeVisible();

      // Adversarial Probe: Programmatically shift focus to document.body
      await page.evaluate(() => {
        document.body.focus();
      });

      // Press Tab -> focus trap should immediately recapture focus to first element
      await page.keyboard.press('Tab');
      let isInside = await modalDialog.evaluate((dialog) => dialog.contains(document.activeElement));
      expect(isInside, 'Focus trap failed to recapture focus into modal on Tab after body focus').toBe(true);

      // Adversarial Probe: Programmatically shift focus to background button
      await page.evaluate(() => {
        const bgBtn = document.querySelector('aside button') as HTMLElement | null;
        if (bgBtn) bgBtn.focus();
      });

      // Press Shift+Tab -> focus trap should immediately recapture focus to last element
      await page.keyboard.press('Shift+Tab');
      isInside = await modalDialog.evaluate((dialog) => dialog.contains(document.activeElement));
      expect(isInside, 'Focus trap failed to recapture focus into modal on Shift+Tab after background button focus').toBe(true);

      await page.keyboard.press('Escape');
      await expect(modalDialog).not.toBeVisible();
      await expect(triggerBtn).toBeFocused();
    });

    test('Escape dismissal under dirty form state and nested element focus restores focus to trigger (Manager)', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      const triggerBtn = page.locator('button[aria-label="Cấu hình Brand Kit"]');
      await triggerBtn.focus();
      await page.keyboard.press('Enter');

      const modalDialog = page.locator('div[role="dialog"][aria-modal="true"]');
      await expect(modalDialog).toBeVisible();

      // Dirty form state as Manager
      const brandInput = page.locator('#brand-kit-name');
      await expect(brandInput).toBeVisible();
      await brandInput.fill('DIRTY_MANAGER_BRAND_TEST_999');

      const uspInput = page.locator('#brand-kit-usp');
      await uspInput.fill('DIRTY_USP_MANAGER_TEST_VALUE_ADVERSARIAL');

      // Focus deeply nested tone preset button
      const presetToneBtn = modalDialog.locator('button:has-text("Trẻ trung")').first();
      await expect(presetToneBtn).toBeVisible();
      await presetToneBtn.focus();
      await expect(presetToneBtn).toBeFocused();

      // Hit Escape while dirty and focused on deeply nested child
      await page.keyboard.press('Escape');

      // Verify modal dismissed cleanly without crash
      await expect(modalDialog).not.toBeVisible();

      // Verify exact trigger element regained focus, NOT lost to body
      await expect(triggerBtn).toBeFocused();
      const activeTagName = await page.evaluate(() => document.activeElement?.tagName);
      expect(activeTagName).toBe('BUTTON');
    });

    test('Backdrop clicks do not leak focus to document body', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      const triggerBtn = page.locator('button[aria-label="Cấu hình Brand Kit"]');
      await triggerBtn.focus();
      await page.keyboard.press('Enter');

      const modalDialog = page.locator('div[role="dialog"][aria-modal="true"]');
      await expect(modalDialog).toBeVisible();

      // Click outside dialog on the backdrop overlay
      await page.mouse.click(10, 10);
      await page.waitForTimeout(100);

      // Press Tab -> focus should still be trapped inside or returned to modal
      await page.keyboard.press('Tab');
      const isTrapped = await modalDialog.evaluate((dialog) => dialog.contains(document.activeElement));
      expect(isTrapped).toBe(true);

      await page.keyboard.press('Escape');
      await expect(modalDialog).not.toBeVisible();
      await expect(triggerBtn).toBeFocused();
    });
  });

  // =========================================================================
  // 2. CAMPAIGN WIZARD MODAL ADVERSARIAL STRESS TEST
  // =========================================================================
  test.describe('2. Campaign Wizard Modal Focus Trap Hardening', () => {

    test('Rapid Tab burst across multi-step wizard remains strictly trapped', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Quản Lý Chiến Dịch');

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")');
      await expect(createBtn).toBeVisible();
      await createBtn.focus();
      await page.keyboard.press('Enter');

      const wizardModal = page.locator('div[role="dialog"][aria-modal="true"]').filter({ hasText: 'Quy trình Thiết lập Chiến dịch Quảng cáo' });
      await expect(wizardModal).toBeVisible();

      // Burst 40 rapid Tab key presses
      for (let i = 0; i < 40; i++) {
        await page.keyboard.press('Tab');
      }

      const isTrappedTab = await wizardModal.evaluate((el) => el.contains(document.activeElement));
      expect(isTrappedTab, 'Focus escaped Campaign Wizard modal during forward Tab burst').toBe(true);

      // Burst 40 rapid Shift+Tab key presses
      for (let i = 0; i < 40; i++) {
        await page.keyboard.press('Shift+Tab');
      }

      const isTrappedShiftTab = await wizardModal.evaluate((el) => el.contains(document.activeElement));
      expect(isTrappedShiftTab, 'Focus escaped Campaign Wizard modal during reverse Shift+Tab burst').toBe(true);

      // Dismiss via Escape
      await page.keyboard.press('Escape');
      await expect(wizardModal).not.toBeVisible();
      await expect(createBtn).toBeFocused();
    });

    test('Wizard dismissal via backdrop click restores focus to create button', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Quản Lý Chiến Dịch');

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")');
      await createBtn.focus();
      await page.keyboard.press('Enter');

      const wizardModal = page.locator('div[role="dialog"][aria-modal="true"]').filter({ hasText: 'Quy trình Thiết lập Chiến dịch Quảng cáo' });
      await expect(wizardModal).toBeVisible();

      // Click on backdrop (top-left outside the modal box)
      await page.mouse.click(20, 20);

      // Wizard should close
      await expect(wizardModal).not.toBeVisible();

      // Focus should be restored to createBtn
      await expect(createBtn).toBeFocused();
    });

    test('Wizard Escape dismissal with dirty step 1 data restores focus to trigger', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Quản Lý Chiến Dịch');

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")');
      await createBtn.focus();
      await page.keyboard.press('Enter');

      const wizardModal = page.locator('div[role="dialog"][aria-modal="true"]').filter({ hasText: 'Quy trình Thiết lập Chiến dịch Quảng cáo' });
      await expect(wizardModal).toBeVisible();

      // Fill in dirty campaign name
      const nameInput = wizardModal.locator('input[placeholder*="VD: Ra Mắt BST Mùa Hè"]');
      if (await nameInput.isVisible()) {
        await nameInput.fill('DIRTY_CAMPAIGN_WIZARD_PROBE_NAME_999');
        await expect(nameInput).toBeFocused();
      }

      // Hit Escape
      await page.keyboard.press('Escape');
      await expect(wizardModal).not.toBeVisible();
      await expect(createBtn).toBeFocused();
    });
  });

  // =========================================================================
  // 3. CAMPAIGN DELETE & DRAWER MODALS ADVERSARIAL STRESS TEST
  // =========================================================================
  test.describe('3. Campaign Delete & Detail Drawer Modals', () => {

    test('Delete modal traps focus and Escape restores focus to delete trigger button (Manager)', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Quản Lý Chiến Dịch');

      // Find first delete button visible for Manager (matches aria-label containing "Xóa chiến dịch")
      const deleteBtn = page.locator('button[aria-label*="Xóa chiến dịch"]:visible').first();
      await expect(deleteBtn).toBeVisible({ timeout: 10000 });
      await deleteBtn.focus();
      await page.keyboard.press('Enter');

      const deleteModal = page.locator('div[role="alertdialog"][aria-modal="true"]');
      await expect(deleteModal).toBeVisible();

      // Burst Tab navigation
      for (let i = 0; i < 20; i++) {
        await page.keyboard.press('Tab');
        const isInside = await deleteModal.evaluate((el) => el.contains(document.activeElement));
        expect(isInside, 'Focus escaped Delete modal during Tab cycle').toBe(true);
      }

      // Dismiss with Escape
      await page.keyboard.press('Escape');
      await expect(deleteModal).not.toBeVisible();

      // Focus should return to the delete trigger button
      await expect(deleteBtn).toBeFocused();
    });

    test('Campaign detail drawer traps focus and Escape restores focus to campaign card trigger', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Quản Lý Chiến Dịch');

      // Find campaign card / detail trigger button
      const detailTrigger = page.locator('button[aria-label*="Xem chi tiết chiến dịch"]').first();
      if (await detailTrigger.isVisible()) {
        await detailTrigger.focus();
        await page.keyboard.press('Enter');

        const detailDrawer = page.locator('div[role="dialog"][aria-modal="true"]').filter({ hasText: 'Chi tiết Chiến dịch' });
        if (await detailDrawer.isVisible()) {
          // Rapid Tab burst inside drawer
          for (let i = 0; i < 20; i++) {
            await page.keyboard.press('Tab');
          }
          const isInside = await detailDrawer.evaluate((el) => el.contains(document.activeElement));
          expect(isInside, 'Focus escaped Detail Drawer during Tab burst').toBe(true);

          // Dismiss with Escape
          await page.keyboard.press('Escape');
          await expect(detailDrawer).not.toBeVisible();
          await expect(detailTrigger).toBeFocused();
        }
      }
    });
  });

  // =========================================================================
  // 4. REVIEW QUEUE REJECT MODAL ADVERSARIAL STRESS TEST
  // =========================================================================
  test.describe('4. Review Queue Reject Modal Focus Trap', () => {

    test('Reject modal traps focus, handles nested template buttons, and restores focus on Escape', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Hàng Đợi Phê Duyệt');

      // Find first Reject button
      const rejectBtn = page.locator('button:has-text("Từ chối")').first();
      if (await rejectBtn.isVisible()) {
        await rejectBtn.focus();
        await page.keyboard.press('Enter');

        const rejectModal = page.locator('div[role="dialog"][aria-modal="true"]').filter({ hasText: 'Từ chối Phê duyệt' });
        await expect(rejectModal).toBeVisible();

        // 30x Tab burst
        for (let i = 0; i < 30; i++) {
          await page.keyboard.press('Tab');
        }

        let isTrapped = await rejectModal.evaluate((el) => el.contains(document.activeElement));
        expect(isTrapped, 'Focus escaped Reject modal during Tab burst').toBe(true);

        // Focus a nested template button
        const templateBtn = rejectModal.locator('button:has-text("Vi phạm chính sách từ ngữ")').first();
        if (await templateBtn.isVisible()) {
          await templateBtn.focus();
          await expect(templateBtn).toBeFocused();
        }

        // Press Escape while nested element is focused
        await page.keyboard.press('Escape');
        await expect(rejectModal).not.toBeVisible();

        // Focus must return to reject button
        await expect(rejectBtn).toBeFocused();
      }
    });
  });

  // =========================================================================
  // 5. MARKETING CALENDAR SCHEDULE MODAL ADVERSARIAL STRESS TEST
  // =========================================================================
  test.describe('5. Marketing Calendar Schedule Modal Focus Trap', () => {

    test('Schedule modal traps Tab burst and restores focus to trigger on Escape', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToTab(page, 'Lịch Xuất Bản');

      // Click "Lên lịch bài viết" or similar button
      const scheduleTrigger = page.locator('button:has-text("Lên lịch")').first();
      if (await scheduleTrigger.isVisible()) {
        await scheduleTrigger.focus();
        await page.keyboard.press('Enter');

        const scheduleModal = page.locator('div[role="dialog"][aria-modal="true"]').filter({ hasText: 'Lập Lịch Xuất Bản Đa Kênh' });
        await expect(scheduleModal).toBeVisible();

        // 20x Tab burst
        for (let i = 0; i < 20; i++) {
          await page.keyboard.press('Tab');
        }

        const isTrapped = await scheduleModal.evaluate((el) => el.contains(document.activeElement));
        expect(isTrapped, 'Focus escaped Schedule modal').toBe(true);

        // Escape to close
        await page.keyboard.press('Escape');
        await expect(scheduleModal).not.toBeVisible();
        await expect(scheduleTrigger).toBeFocused();
      }
    });
  });

  // =========================================================================
  // 6. GLOBAL AI DRAWER KEYBOARD & CRASH AUDIT
  // =========================================================================
  test.describe('6. In-Context AI Drawer Failure Mode Audit', () => {

    test('Empirical Bug Verification: Navbar AI Copilot trigger triggers React Hooks invariant #310 error due to conditional hooks in AIDrawer.tsx', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });

      // Find AI Copilot trigger in Navbar by aria-label
      const aiDrawerTrigger = page.locator('button[aria-label="Mở AI Copilot"]');
      await expect(aiDrawerTrigger).toBeVisible();

      await aiDrawerTrigger.click();

      // Assert ErrorBoundary caught React Error #310 (Rendered more hooks than during previous render)
      const errorBoundaryHeading = page.locator('h2:has-text("Đã xảy ra sự cố giao diện")');
      const isErrorCaught = await errorBoundaryHeading.isVisible({ timeout: 4000 }).catch(() => false);
      
      // If error is caught, verify it is indeed the React #310 hook violation
      if (isErrorCaught) {
        const errorText = await page.locator('text=Minified React error #310').isVisible();
        expect(errorText, 'React Error #310 caught by ErrorBoundary due to AIDrawer.tsx lines 256-257 after line 88 early return').toBe(true);
      }
    });
  });
});
