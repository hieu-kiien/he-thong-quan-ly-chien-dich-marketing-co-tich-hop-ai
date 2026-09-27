import { test, expect, Page } from './fixtures/auth.fixture';

/**
 * Challenger M5 Empirical Stress Test Suite:
 * - Objective 1: Pointer Interception Probe & DOM Cleanness
 * - Objective 2: Modal & Backdrop Lifecycle Verification (Wizard, Drawer, Delete Modal)
 * - Objective 3: Interactive Buttons, Switches & Focus Rings Accessibility
 */

async function navigateToCampaigns(page: Page) {
  const isMobile = (page.viewportSize()?.width || 1280) < 768;
  if (isMobile) {
    const aside = page.locator('aside');
    const isAsideOpen = await aside.evaluate((el) => el.classList.contains('translate-x-0')).catch(() => false);
    if (!isAsideOpen) {
      const hamburgerBtn = page.locator('button[aria-label="Mở thanh điều hướng"]');
      if (await hamburgerBtn.isVisible().catch(() => false)) {
        await hamburgerBtn.click();
        await page.waitForTimeout(300);
      }
    }
  }
  const targetBtn = page.locator('aside button:has-text("Quản Lý Chiến Dịch")').first();
  await targetBtn.click({ force: true });
  await page.waitForTimeout(500);
  // Wait until campaign management heading is visible
  await expect(page.locator('h1:has-text("Quản trị Chiến dịch")')).toBeVisible({ timeout: 10000 });
}

test.describe('Milestone M5 Challenger Empirical Tests: Pointer Interaction & Modal Lifecycles', () => {

  // =========================================================================
  // 1. POINTER INTERCEPTION PROBE & CLEAN DOM INSPECTION
  // =========================================================================
  test.describe('1. Pointer Interception & Clean DOM Inspection', () => {
    test('When no modal is open, 0 elements with fixed inset-0 or z-50 with pointer capture exist in DOM', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      // Verify that no modal or drawer is currently open
      const wizardModal = page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]');
      const drawerModal = page.locator('div[role="dialog"][aria-labelledby="campaign-drawer-title"]');
      const deleteModal = page.locator('div[role="alertdialog"][aria-labelledby="delete-dialog-title"]');

      expect(await wizardModal.count()).toBe(0);
      expect(await drawerModal.count()).toBe(0);
      expect(await deleteModal.count()).toBe(0);

      // Inspect entire DOM for any elements with fixed inset-0
      const fixedInsetZeroElements = await page.evaluate(() => {
        const els = Array.from(document.querySelectorAll('*'));
        return els.filter(el => {
          const style = window.getComputedStyle(el);
          const isFixed = style.position === 'fixed';
          const isInsetZero = (
            el.classList.contains('inset-0') || 
            (style.top === '0px' && style.bottom === '0px' && style.left === '0px' && style.right === '0px')
          );
          const hasPointerEvents = style.pointerEvents !== 'none';
          const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && (el as HTMLElement).offsetWidth > 0;
          return isFixed && isInsetZero && hasPointerEvents && isVisible;
        }).map(el => ({
          tagName: el.tagName,
          className: el.className,
          id: el.id,
          role: el.getAttribute('role'),
        }));
      });

      // Filter out root navbar/sidebar if fixed, check specifically for overlay traps
      const overlayTraps = fixedInsetZeroElements.filter(el => 
        !['NAV', 'ASIDE', 'HEADER'].includes(el.tagName) && 
        (el.className.includes('bg-slate-950') || el.role === 'dialog' || el.role === 'alertdialog' || el.className.includes('z-50'))
      );

      expect(overlayTraps.length, `Expected 0 overlay traps in DOM when modals are closed, found: ${JSON.stringify(overlayTraps)}`).toBe(0);

      // Empirically probe elementFromPoint across key interactive controls on the Campaigns page
      const interactiveTargets = [
        'button:has-text("Tạo Chiến Dịch Mới"):visible',
        'input[placeholder*="Tìm theo tên chiến dịch"]:visible',
        'button[aria-label*="Xem chi tiết"]:visible',
        'button[aria-label*="Nhân bản"]:visible',
        'button[aria-label*="Mở AI sáng tạo"]:visible',
        'button[aria-label*="chiến dịch"]:visible', // delivery toggle
      ];

      for (const selector of interactiveTargets) {
        const locator = page.locator(selector).first();
        await expect(locator).toBeVisible();
        const box = await locator.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          const centerX = box.x + box.width / 2;
          const centerY = box.y + box.height / 2;

          const hitTargetInfo = await page.evaluate(({ x, y }) => {
            const el = document.elementFromPoint(x, y);
            const isModalOverlay = !!el?.closest('[role="dialog"], [role="alertdialog"], .fixed.inset-0.z-50');
            return {
              tagName: el?.tagName,
              className: el?.className,
              ariaLabel: el?.getAttribute('aria-label'),
              isModalOverlay,
            };
          }, { x: centerX, y: centerY });

          expect(hitTargetInfo.isModalOverlay, `Element at (${centerX}, ${centerY}) was captured by modal overlay!`).toBe(false);
        }
      }
    });

    test('Clicks on campaign table rows, action buttons, and filters dispatch directly without pointer swallowing', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      // 1. Search input responsiveness
      const searchInput = page.locator('input[placeholder*="Tìm theo tên chiến dịch"]:visible').first();
      await expect(searchInput).toBeVisible();
      await searchInput.click();
      await searchInput.fill('Tuyển sinh');
      expect(await searchInput.inputValue()).toBe('Tuyển sinh');
      await page.waitForTimeout(200);
      await searchInput.fill(''); // clear
      await page.waitForTimeout(200);

      // 2. View mode switcher responsiveness
      const gridViewBtn = page.locator('button[title="Dạng lưới thẻ (Grid View)"]');
      const tableViewBtn = page.locator('button[title="Dạng bảng dữ liệu (Table View)"]');
      if (await gridViewBtn.isVisible()) {
        await gridViewBtn.click();
        await page.waitForTimeout(200);
        // Verify grid cards are rendered
        const gridCard = page.locator('.grid div[class*="rounded-2xl"]').first();
        await expect(gridCard).toBeVisible();

        // Switch back to table view
        await tableViewBtn.click();
        await page.waitForTimeout(200);
        const tableElement = page.locator('table');
        await expect(tableElement).toBeVisible();
      }

      // 3. Status filter buttons responsiveness
      const filterRunningBtn = page.locator('button:has-text("Đang chạy")');
      if (await filterRunningBtn.isVisible()) {
        await filterRunningBtn.click();
        await page.waitForTimeout(200);
        const filterAllBtn = page.locator('button:has-text("Tất cả")');
        await filterAllBtn.click();
        await page.waitForTimeout(200);
      }

      // 4. Objective filter select responsiveness
      const objectiveSelect = page.locator('select[aria-label="Lọc theo mục tiêu chiến dịch"]:visible').first();
      if (await objectiveSelect.isVisible()) {
        await objectiveSelect.selectOption('SALES');
        await page.waitForTimeout(200);
        await objectiveSelect.selectOption('ALL');
      }
    });
  });

  // =========================================================================
  // 2. MODAL & BACKDROP LIFECYCLE VERIFICATION
  // =========================================================================
  test.describe('2. Modal & Backdrop Lifecycle Verification', () => {

    test('Wizard Modal: Backdrop click, Escape key, and close button trigger state reset and immediate unmount', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")');
      await expect(createBtn).toBeVisible();

      // --- LIFECYCLE SUBTEST 1: BACKDROP CLICK ---
      await createBtn.click();
      const wizardModal = page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]');
      await expect(wizardModal).toBeVisible();

      // Locate the backdrop element specifically
      const wizardBackdrop = wizardModal.locator('.bg-slate-950\\/60');
      await expect(wizardBackdrop).toBeVisible();

      // Click on backdrop outside modal container (e.g. top-left corner 25, 25)
      await page.mouse.click(25, 25);
      await expect(wizardModal).not.toBeVisible();
      // Ensure backdrop is unmounted completely from DOM, not merely hidden
      expect(await page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]').count()).toBe(0);

      // Verify underlying table is immediately interactive
      await expect(createBtn).toBeEnabled();

      // --- LIFECYCLE SUBTEST 2: ESCAPE KEY ---
      await createBtn.click();
      await expect(wizardModal).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(wizardModal).not.toBeVisible();
      expect(await page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]').count()).toBe(0);
      await expect(createBtn).toBeFocused();

      // --- LIFECYCLE SUBTEST 3: CLOSE "X" BUTTON ---
      await createBtn.click();
      await expect(wizardModal).toBeVisible();
      const closeBtn = wizardModal.locator('button[aria-label="Đóng cửa sổ thiết lập chiến dịch"]');
      await expect(closeBtn).toBeVisible();
      await closeBtn.click();
      await expect(wizardModal).not.toBeVisible();
      expect(await page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]').count()).toBe(0);
    });

    test('Detail Drawer: Backdrop click, Escape key, and close button trigger state reset and immediate unmount', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const viewDetailBtn = page.locator('button[aria-label*="Xem chi tiết"]:visible').first();
      await expect(viewDetailBtn).toBeVisible({ timeout: 10000 });

      // --- LIFECYCLE SUBTEST 1: BACKDROP CLICK ---
      await viewDetailBtn.click();
      const drawer = page.locator('div[role="dialog"][aria-labelledby="campaign-drawer-title"]');
      await expect(drawer).toBeVisible();

      // Click on backdrop area (left side of screen where drawer does not cover, e.g. x: 50, y: 300)
      await page.mouse.click(50, 300);
      await expect(drawer).not.toBeVisible();
      expect(await page.locator('div[role="dialog"][aria-labelledby="campaign-drawer-title"]').count()).toBe(0);

      // --- LIFECYCLE SUBTEST 2: ESCAPE KEY ---
      await viewDetailBtn.click();
      await expect(drawer).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(drawer).not.toBeVisible();
      expect(await page.locator('div[role="dialog"][aria-labelledby="campaign-drawer-title"]').count()).toBe(0);
      await expect(viewDetailBtn).toBeFocused();

      // --- LIFECYCLE SUBTEST 3: CLOSE "X" BUTTON ---
      await viewDetailBtn.click();
      await expect(drawer).toBeVisible();
      const drawerCloseBtn = drawer.locator('button[aria-label="Đóng bảng chi tiết chiến dịch"]');
      await expect(drawerCloseBtn).toBeVisible();
      await drawerCloseBtn.click();
      await expect(drawer).not.toBeVisible();
      expect(await page.locator('div[role="dialog"][aria-labelledby="campaign-drawer-title"]').count()).toBe(0);
    });

    test('Delete Confirmation Modal (Manager): Backdrop click, Escape key, and cancel button trigger state reset and immediate unmount', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const deleteBtn = page.locator('button[aria-label*="Xóa chiến dịch"]:visible').first();
      await expect(deleteBtn).toBeVisible({ timeout: 10000 });

      // --- LIFECYCLE SUBTEST 1: BACKDROP CLICK ---
      await deleteBtn.click();
      const deleteModal = page.locator('div[role="alertdialog"][aria-labelledby="delete-dialog-title"]');
      await expect(deleteModal).toBeVisible();

      // Click outside dialog in backdrop area
      await page.mouse.click(25, 25);
      await expect(deleteModal).not.toBeVisible();
      expect(await page.locator('div[role="alertdialog"][aria-labelledby="delete-dialog-title"]').count()).toBe(0);

      // --- LIFECYCLE SUBTEST 2: ESCAPE KEY ---
      await deleteBtn.click();
      await expect(deleteModal).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(deleteModal).not.toBeVisible();
      expect(await page.locator('div[role="alertdialog"][aria-labelledby="delete-dialog-title"]').count()).toBe(0);
      await expect(deleteBtn).toBeFocused();

      // --- LIFECYCLE SUBTEST 3: CANCEL BUTTON ---
      await deleteBtn.click();
      await expect(deleteModal).toBeVisible();
      const cancelBtn = deleteModal.locator('button:has-text("Hủy")');
      await expect(cancelBtn).toBeVisible();
      await cancelBtn.click();
      await expect(deleteModal).not.toBeVisible();
      expect(await page.locator('div[role="alertdialog"][aria-labelledby="delete-dialog-title"]').count()).toBe(0);
    });

    test('Rapid Modal Churn Stress: 10 consecutive rapid open/close cycles leave 0 pointer traps in DOM', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")');
      const wizardModal = page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]');

      for (let i = 0; i < 10; i++) {
        await createBtn.click();
        await expect(wizardModal).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(wizardModal).not.toBeVisible();
      }

      // Check remaining fixed inset-0 elements
      const danglingTraps = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('.fixed.inset-0.z-50')).length;
      });
      expect(danglingTraps).toBe(0);

      // Table row remains interactive
      const firstRow = page.locator('tbody tr').first();
      await expect(firstRow).toBeVisible();
    });
  });

  // =========================================================================
  // 3. INTERACTIVE BUTTONS, SWITCHES & ACCESSIBLE FOCUS RINGS
  // =========================================================================
  test.describe('3. Accessible Focus Rings & Responsive Target Sizes', () => {

    test('Interactive delivery switches and table action buttons have responsive target sizes and accessible focus rings', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      // Check delivery toggle switch target size and focus ring
      const toggleSwitch = page.locator('button[aria-label*="chiến dịch"]:visible').first();
      await expect(toggleSwitch).toBeVisible();

      const switchBox = await toggleSwitch.boundingBox();
      expect(switchBox).not.toBeNull();
      if (switchBox) {
        // Switch size should be at least 30x18px
        expect(switchBox.width).toBeGreaterThanOrEqual(30);
        expect(switchBox.height).toBeGreaterThanOrEqual(18);
      }

      // Focus switch via keyboard and inspect computed focus ring
      await toggleSwitch.focus();
      const hasFocusStyles = await toggleSwitch.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const hasOutline = style.outlineStyle !== 'none' && style.outlineWidth !== '0px';
        const hasBoxShadow = style.boxShadow !== 'none' && style.boxShadow.length > 0;
        return {
          hasOutline,
          hasBoxShadow,
          outline: style.outline,
          boxShadow: style.boxShadow,
          className: el.className,
        };
      });

      // Assert that either ring (box-shadow) or outline is applied on focus
      expect(
        hasFocusStyles.hasOutline || hasFocusStyles.hasBoxShadow || hasFocusStyles.className.includes('focus:ring-2'),
        'Delivery switch must exhibit visible focus indicator (outline or box-shadow ring)'
      ).toBe(true);

      // Toggle switch action responsiveness
      const initialText = await toggleSwitch.locator('..').locator('span').last().innerText();
      await toggleSwitch.click();
      await page.waitForTimeout(600);
      const afterText = await toggleSwitch.locator('..').locator('span').last().innerText();
      expect(afterText.length).toBeGreaterThan(0);

      // Check table action buttons (Eye, Copy, AI)
      const actionButtons = [
        page.locator('button[aria-label*="Xem chi tiết"]:visible').first(),
        page.locator('button[aria-label*="Nhân bản"]:visible').first(),
        page.locator('button[aria-label*="Mở AI sáng tạo"]:visible').first(),
      ];

      for (const btn of actionButtons) {
        await expect(btn).toBeVisible();
        const box = await btn.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          // Standard touch target minimum >= 24px
          expect(box.width).toBeGreaterThanOrEqual(24);
          expect(box.height).toBeGreaterThanOrEqual(24);
        }

        // Test focus ring
        await btn.focus();
        const btnFocus = await btn.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return {
            hasOutline: style.outlineStyle !== 'none' && style.outlineWidth !== '0px',
            hasBoxShadow: style.boxShadow !== 'none' && style.boxShadow.length > 0,
            className: el.className,
          };
        });

        expect(
          btnFocus.hasOutline || btnFocus.hasBoxShadow || btnFocus.className.includes('focus:ring-2'),
          `Action button ${await btn.getAttribute('aria-label')} missing focus ring`
        ).toBe(true);
      }
    });

    test('Card Grid View switches and buttons maintain accessible targets and focus indicators', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      // Switch to Grid View
      const gridViewBtn = page.locator('button[title="Dạng lưới thẻ (Grid View)"]');
      if (await gridViewBtn.isVisible()) {
        await gridViewBtn.click();
        await page.waitForTimeout(300);

        // Find status toggle in Grid card
        const gridSwitch = page.locator('.grid button[aria-label*="chiến dịch"]:visible').first();
        await expect(gridSwitch).toBeVisible();

        const gridBox = await gridSwitch.boundingBox();
        expect(gridBox).not.toBeNull();
        if (gridBox) {
          expect(gridBox.width).toBeGreaterThanOrEqual(24);
          expect(gridBox.height).toBeGreaterThanOrEqual(14);
        }

        // Focus via keyboard
        await gridSwitch.focus();
        const focusVisibleApplied = await gridSwitch.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return (
            (style.outlineStyle !== 'none' && style.outlineWidth !== '0px') ||
            (style.boxShadow !== 'none' && style.boxShadow.length > 0)
          );
        });

        expect(focusVisibleApplied).toBe(true);
      }
    });
  });
});
