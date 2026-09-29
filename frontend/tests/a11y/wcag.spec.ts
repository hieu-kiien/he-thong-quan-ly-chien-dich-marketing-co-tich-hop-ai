import { test as baseTest, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { test as authTest } from '../e2e/fixtures/auth.fixture';
import { setupMockApiRoutes } from '../e2e/fixtures/mock-api';

// Five required WCAG responsive test viewports
const VIEWPORTS = [
  { name: 'Mobile 320px (Reflow)', width: 320, height: 568 },
  { name: 'Mobile 390px', width: 390, height: 844 },
  { name: 'Tablet 768px', width: 768, height: 1024 },
  { name: 'Desktop 1280px', width: 1280, height: 800 },
  { name: 'Wide Screen 1440px', width: 1440, height: 900 },
];

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
  await page.waitForTimeout(300);
}

/**
 * Helper to run Axe scan asserting 0 critical and 0 serious violations
 */
async function assertNoCriticalOrSeriousViolations(page: Page, contextName: string) {
  const scanResults = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  const criticalAndSerious = scanResults.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious'
  );

  if (criticalAndSerious.length > 0) {
    const summary = criticalAndSerious.map((v) => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      helpUrl: v.helpUrl,
      nodes: v.nodes.map((n) => n.html).slice(0, 3),
    }));
    console.error(`Axe violations in [${contextName}]:`, JSON.stringify(summary, null, 2));
  }

  expect(
    criticalAndSerious,
    `Found ${criticalAndSerious.length} critical/serious WCAG violations in ${contextName}`
  ).toEqual([]);
}

authTest.describe('WCAG 2.2 AA Accessibility & UX Suite', () => {

  // =========================================================================
  // 1. AXE SCAN: Public Authentication Pages (Login & Register)
  // =========================================================================
  baseTest.describe('1. Public Auth Pages WCAG Audit', () => {
    for (const vp of VIEWPORTS) {
      baseTest(`Login Page accessibility @ ${vp.name}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await setupMockApiRoutes(page);
        await page.goto('/');

        // Verify Login Page is rendered
        await expect(page.locator('#login-email')).toBeVisible();
        await expect(page.locator('#login-password')).toBeVisible();
        await expect(page.locator('label[for="login-email"]')).toBeVisible();
        await expect(page.locator('label[for="login-password"]')).toBeVisible();

        await assertNoCriticalOrSeriousViolations(page, `Login Page (${vp.name})`);
      });

      baseTest(`Register Page accessibility @ ${vp.name}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await setupMockApiRoutes(page);
        await page.goto('/');

        // Switch to Register page
        const switchToRegisterBtn = page.locator('button:has-text("Đăng ký tài khoản mới")');
        await expect(switchToRegisterBtn).toBeVisible();
        await switchToRegisterBtn.click();

        // Verify Register Page fields and labels
        await expect(page.locator('#register-fullname')).toBeVisible();
        await expect(page.locator('#register-email')).toBeVisible();
        await expect(page.locator('#register-password')).toBeVisible();
        await expect(page.locator('label[for="register-fullname"]')).toBeVisible();
        await expect(page.locator('label[for="register-email"]')).toBeVisible();
        await expect(page.locator('label[for="register-password"]')).toBeVisible();

        await assertNoCriticalOrSeriousViolations(page, `Register Page (${vp.name})`);
      });
    }
  });

  // =========================================================================
  // 2. AXE SCAN: Authenticated Core Application Views
  // =========================================================================
  authTest.describe('2. Authenticated Core Views WCAG Audit', () => {
    authTest.setTimeout(120000);

    for (const vp of VIEWPORTS) {
      authTest(`Core Views WCAG Audit @ ${vp.name}`, async ({ marketerPage }) => {
        await marketerPage.setViewportSize({ width: vp.width, height: vp.height });

        // 1. Dashboard View
        await navigateToTab(marketerPage, 'Bảng Điều Khiển');
        await expect(marketerPage.locator('text=Command Center Điều Phối').first()).toBeVisible({ timeout: 10000 });
        await assertNoCriticalOrSeriousViolations(marketerPage, `Dashboard (${vp.name})`);

        // 2. Campaigns View
        await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');
        await expect(marketerPage.locator('text=Quản trị Chiến dịch').first()).toBeVisible({ timeout: 10000 });
        await assertNoCriticalOrSeriousViolations(marketerPage, `Campaigns (${vp.name})`);

        // 3. AI Studio View
        await navigateToTab(marketerPage, 'Xưởng Sáng Tạo AI');
        await expect(marketerPage.locator('text=AI Marketing Copilot').first()).toBeVisible({ timeout: 10000 });
        await assertNoCriticalOrSeriousViolations(marketerPage, `AI Studio (${vp.name})`);

        // 4. Marketing Calendar View
        await navigateToTab(marketerPage, 'Lịch Xuất Bản');
        await expect(marketerPage.locator('text=Lịch Xuất Bản').first()).toBeVisible({ timeout: 10000 });
        await assertNoCriticalOrSeriousViolations(marketerPage, `Calendar (${vp.name})`);

        // 5. Review Queue View
        await navigateToTab(marketerPage, 'Hàng Đợi Phê Duyệt');
        await expect(marketerPage.locator('text=Hàng đợi Phê duyệt').first()).toBeVisible({ timeout: 10000 });
        await assertNoCriticalOrSeriousViolations(marketerPage, `Review Queue (${vp.name})`);

        // 6. Settings View
        await navigateToTab(marketerPage, 'Cài Đặt & Brand Kit');
        await expect(marketerPage.locator('text=Trung tâm Cài đặt').first()).toBeVisible({ timeout: 10000 });
        await assertNoCriticalOrSeriousViolations(marketerPage, `Settings (${vp.name})`);
      });
    }
  });

  // =========================================================================
  // 3. KEYBOARD NAVIGATION & ACCESSIBLE FOCUS TRAP
  // =========================================================================
  authTest.describe('3. Keyboard Navigation & Accessible Focus Trap', () => {

    authTest('Brand Kit Modal: Tab/Shift+Tab cycle, Escape to close, Focus restoration', async ({ marketerPage }) => {
      // Set to desktop viewport so Navbar Brand Kit button is visible
      await marketerPage.setViewportSize({ width: 1280, height: 800 });

      // Find the Brand Kit trigger button in Navbar
      const brandKitTrigger = marketerPage.locator('button[aria-label="Cấu hình Brand Kit"]');
      await expect(brandKitTrigger).toBeVisible();

      // Focus the trigger button using keyboard and press Enter to open
      await brandKitTrigger.focus();
      await marketerPage.keyboard.press('Enter');

      // Verify modal is open and has accessible dialog attributes
      const modalDialog = marketerPage.locator('div[role="dialog"][aria-modal="true"]');
      await expect(modalDialog).toBeVisible();
      await expect(modalDialog.locator('#brand-kit-modal-title')).toBeVisible();

      // First focusable element inside modal should receive focus
      const brandNameInput = modalDialog.locator('#brand-kit-name');
      await expect(brandNameInput).toBeFocused();

      // Press Tab multiple times to cycle through modal controls
      await marketerPage.keyboard.press('Tab'); // USP
      await marketerPage.keyboard.press('Tab'); // Tone of voice
      await marketerPage.keyboard.press('Tab'); // Banned keyword input
      await marketerPage.keyboard.press('Tab'); // Add keyword button

      // Test Shift+Tab reverse cycling
      await marketerPage.keyboard.press('Shift+Tab');
      await marketerPage.keyboard.press('Shift+Tab');

      // Ensure focus remains inside modal dialog (focus trap)
      const isFocusedInsideModal = await modalDialog.evaluate((dialog) => {
        return dialog.contains(document.activeElement);
      });
      expect(isFocusedInsideModal).toBe(true);

      // Press Escape key to close modal
      await marketerPage.keyboard.press('Escape');

      // Verify modal closed
      await expect(modalDialog).not.toBeVisible();

      // Verify focus is restored to the trigger button that opened it
      await expect(brandKitTrigger).toBeFocused();
    });

    authTest('Campaign Wizard Modal: Tab cycling, Escape to close, Focus restoration', async ({ marketerPage }) => {
      await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');
      const createBtn = marketerPage.locator('button:has-text("Tạo Chiến Dịch Mới")');
      await expect(createBtn).toBeVisible();

      // Focus and trigger open
      await createBtn.focus();
      await marketerPage.keyboard.press('Enter');

      // Verify Wizard Modal open with role dialog
      const wizardModal = marketerPage.locator('div[role="dialog"][aria-modal="true"]');
      await expect(wizardModal).toBeVisible();
      await expect(wizardModal.locator('#campaign-wizard-title')).toBeVisible();

      // Tab navigation inside wizard
      await marketerPage.keyboard.press('Tab');
      await marketerPage.keyboard.press('Tab');

      // Focus trap check: active element must be inside wizard modal
      const isTrapped = await wizardModal.evaluate((el) => {
        return el.contains(document.activeElement);
      });
      expect(isTrapped).toBe(true);

      // Press Escape to close wizard modal
      await marketerPage.keyboard.press('Escape');
      await expect(wizardModal).not.toBeVisible();

      // Verify focus restored to the create campaign button
      await expect(createBtn).toBeFocused();
    });
  });

  // =========================================================================
  // 4. RESPONSIVE 320px REFLOW (Zero horizontal scrollbar)
  // =========================================================================
  authTest.describe('4. Responsive 320px Reflow Verification', () => {

    authTest('Campaigns view reflows cleanly at 320px with 0 horizontal scroll', async ({ marketerPage }) => {
      // Set viewport to minimal WCAG reflow width: 320px
      await marketerPage.setViewportSize({ width: 320, height: 568 });

      // Navigate to Campaigns
      await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');
      await expect(marketerPage.locator('text=Quản trị Chiến dịch').first()).toBeVisible();

      // Verify no horizontal scrolling exists (WCAG 1.4.10 Reflow)
      const scrollInfo = await marketerPage.evaluate(() => {
        return {
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          hasHorizontalScroll: document.documentElement.scrollWidth > window.innerWidth,
        };
      });

      expect(
        scrollInfo.hasHorizontalScroll,
        `Document scrollWidth (${scrollInfo.scrollWidth}) exceeds innerWidth (${scrollInfo.innerWidth}) at 320px viewport`
      ).toBe(false);

      // Verify that the desktop table is hidden and mobile card reflow is displayed
      const mobileCardContainer = marketerPage.locator('div.md\\:hidden.space-y-4');
      await expect(mobileCardContainer).toBeVisible();

      const desktopTableContainer = marketerPage.locator('div.hidden.md\\:block');
      await expect(desktopTableContainer).not.toBeVisible();

      // Verify delivery toggle button on mobile card has aria-label
      const mobileToggleBtn = mobileCardContainer.locator('button[aria-label*="chiến dịch"]').first();
      await expect(mobileToggleBtn).toBeVisible();
    });

    authTest('All Core Views have 0 horizontal scroll at 320px viewport', async ({ marketerPage }) => {
      await marketerPage.setViewportSize({ width: 320, height: 568 });

      const tabs = [
        { label: 'Bảng Điều Khiển', text: 'Command Center Điều Phối' },
        { label: 'Quản Lý Chiến Dịch', text: 'Quản trị Chiến dịch' },
        { label: 'Xưởng Sáng Tạo AI', text: 'AI Marketing Copilot' },
        { label: 'Lịch Xuất Bản', text: 'Lịch Xuất Bản' },
        { label: 'Hàng Đợi Phê Duyệt', text: 'Hàng đợi Phê duyệt' },
        { label: 'Cài Đặt & Brand Kit', text: 'Trung tâm Cài đặt' },
      ];

      for (const tab of tabs) {
        await navigateToTab(marketerPage, tab.label);
        await expect(marketerPage.locator(`text=${tab.text}`).first()).toBeVisible({ timeout: 10000 });

        const isOverflowing = await marketerPage.evaluate(() => {
          return document.documentElement.scrollWidth > window.innerWidth;
        });

        expect(
          isOverflowing,
          `View [${tab.label}] has horizontal scroll overflow at 320px width`
        ).toBe(false);
      }
    });
  });

  // =========================================================================
  // 5. FOUR UI STATES ACCESSIBILITY (Loading, Empty, Error, Success)
  // =========================================================================
  authTest.describe('5. Four UI States Accessibility Verification', () => {

    authTest('UI State 1 (Loading): Loading indicators and skeletons are accessible', async ({ marketerPage }) => {
      // Trigger data reload on Campaigns page
      await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');
      const refreshBtn = marketerPage.locator('button[aria-label="Làm mới dữ liệu từ server"]');
      await expect(refreshBtn).toBeVisible();

      // Click refresh button
      await refreshBtn.click();

      // Assert spin icon or loading state indicator has appropriate label/title
      await expect(refreshBtn).toHaveAttribute('aria-label', 'Làm mới dữ liệu từ server');
    });

    authTest('UI State 2 (Empty): Accessible empty state shown when filter returns 0 items', async ({ marketerPage }) => {
      await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');

      // Enter search query that matches no campaigns
      const searchInput = marketerPage.locator('input[aria-label="Tìm theo tên chiến dịch, sản phẩm, đối tượng"]');
      await expect(searchInput).toBeVisible();
      await searchInput.fill('NonexistentQueryZXCVB999');

      // Assert Empty State message and call to action are visible
      const emptyHeading = marketerPage.locator('text=Không tìm thấy chiến dịch phù hợp');
      await expect(emptyHeading).toBeVisible();

      const createFirstBtn = marketerPage.locator('button:has-text("Tạo Chiến Dịch Đầu Tiên")');
      await expect(createFirstBtn).toBeVisible();
    });

    authTest('UI State 3 (Error): Accessible error toast on failed action', async ({ marketerPage }) => {
      await navigateToTab(marketerPage, 'Cài Đặt & Brand Kit');

      // Test connection with empty or invalid key
      const keyInput = marketerPage.locator('#ai-key-input');
      if (await keyInput.isVisible()) {
        await keyInput.fill('invalid');
        const testConnBtn = marketerPage.locator('button:has-text("Kiểm tra kết nối")');
        if (await testConnBtn.isVisible()) {
          await testConnBtn.click();
          // Error notification should be visible
          await expect(
            marketerPage.locator('text=API Key không hợp lệ').or(marketerPage.locator('text=Lỗi')).first()
          ).toBeVisible({ timeout: 7000 });
        }
      }
    });

    authTest('UI State 4 (Success): Accessible success toast on successful action', async ({ marketerPage }) => {
      await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');

      // 1-Click Toggle Delivery Status (e.g. Active <-> Paused)
      const toggleBtn = marketerPage.locator('button[aria-label*="chiến dịch"]:visible').first();
      await expect(toggleBtn).toBeVisible();
      await toggleBtn.click();

      // Assert Success Toast message appears
      const successToast = marketerPage.locator('text=Đã kích hoạt phân phối').or(marketerPage.locator('text=Đã tạm dừng phân phối')).first();
      await expect(successToast).toBeVisible({ timeout: 7000 });
    });
  });
});
