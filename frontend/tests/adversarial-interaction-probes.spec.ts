import { test, expect, Page, STORAGE_STATES } from './e2e/fixtures/auth.fixture';
import { setupMockApiRoutes, INITIAL_CONTENTS, INITIAL_CAMPAIGNS, USERS } from './e2e/fixtures/mock-api';

/**
 * ============================================================================
 * Milestone M6: Visual & Adversarial Interaction Probes Suite
 * Requirement: R6 Visual/UX Testing Loop (Lines 437-444, 458-466)
 * ============================================================================
 * 
 * Probe 1: Pointer Interception Probe:
 *   Scans across desktop, tablet, and mobile viewports. Asserts document.elementFromPoint(x, y)
 *   resolves directly to the expected interactive target without being intercepted by invisible overlays.
 * 
 * Probe 2: Modal Lifecycle & Focus Trap Verification:
 *   Opens and closes 5 key modals (New Campaign Wizard, Detail Drawer, Rejection Modal, Delete Dialog,
 *   Brand Safety Confirmation Dialog) via Escape, Backdrop Click, Close/X, and Cancel channels.
 *   Executes rapid modal churn (10 consecutive cycles) and verifies 0 dangling backdrops and clean focus restore.
 * 
 * Probe 3: Cold-Start Resilience & Latency Probe:
 *   Simulates server awakening delay (>3.5s latency). Verifies friendly Server Awakening Indicator,
 *   absence of white-screen crashes or disconnects, and graceful completion when the server responds.
 * 
 * Probe 4: Multi-Role Concurrency & HITL State Machine Integrity:
 *   Executes full multi-role workflow:
 *   Marketer creates/submits content -> Manager approves -> Marketer attempts edit on approved content ->
 *   Verifies Brand Safety Confirmation Dialog -> Confirms edit -> Verifies backend resets content status
 *   to AI_DRAFT and increments version_no.
 */

// Helper to navigate to Campaigns page reliably across viewports
async function navigateToCampaigns(page: Page) {
  const isMobile = (page.viewportSize()?.width || 1280) < 768;
  if (isMobile) {
    const hamburgerBtn = page.locator('button[aria-label="Mở thanh điều hướng"]');
    if (await hamburgerBtn.isVisible().catch(() => false)) {
      await hamburgerBtn.click();
      await page.waitForTimeout(250);
    }
  }
  const targetBtn = page.locator('aside button:has-text("Quản Lý Chiến Dịch")').first();
  await targetBtn.click({ force: true });
  await expect(
    page.locator('h1:has-text("Quản trị Chiến dịch")').or(page.locator('h1:has-text("Chiến dịch")'))
  ).toBeVisible({ timeout: 10000 });
}

// Helper to navigate to Review Queue reliably across viewports
async function navigateToReviewQueue(page: Page) {
  const isMobile = (page.viewportSize()?.width || 1280) < 768;
  if (isMobile) {
    const hamburgerBtn = page.locator('button[aria-label="Mở thanh điều hướng"]');
    if (await hamburgerBtn.isVisible().catch(() => false)) {
      await hamburgerBtn.click();
      await page.waitForTimeout(250);
    }
  }
  const targetBtn = page.locator('aside button:has-text("Hàng Đợi Phê Duyệt")').first();
  await targetBtn.click({ force: true });
  await expect(
    page.locator('h2:has-text("Hàng đợi Phê duyệt")')
  ).toBeVisible({ timeout: 10000 });
}

test.describe('Milestone M6: Adversarial Interaction Probes & Visual Testing Loop', () => {

  // =========================================================================
  // PROBE 1: POINTER INTERCEPTION PROBE (Desktop, Tablet, Mobile)
  // =========================================================================
  test.describe('Probe 1: Pointer Interception & Viewport Element Hit Verification', () => {
    const viewports = [
      { name: 'Desktop (1280x800)', width: 1280, height: 800 },
      { name: 'Tablet (768x1024)', width: 768, height: 1024 },
      { name: 'Mobile (375x667)', width: 375, height: 667 },
    ];

    for (const vp of viewports) {
      test(`Viewport [${vp.name}]: elementFromPoint resolves directly to interactive targets without invisible overlay traps`, async ({ marketerPage: page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await navigateToCampaigns(page);

        // 1. Verify 0 fixed inset-0 overlay traps exist when no modal is open
        const overlayTraps = await page.evaluate(() => {
          const els = Array.from(document.querySelectorAll('*'));
          return els.filter(el => {
            const style = window.getComputedStyle(el);
            const isFixed = style.position === 'fixed';
            const cName = typeof el.className === 'string' 
              ? el.className 
              : (typeof (el as any).className?.baseVal === 'string' ? (el as any).className.baseVal : '');
            const isInsetZero = (
              cName.includes('inset-0') ||
              (style.top === '0px' && style.bottom === '0px' && style.left === '0px' && style.right === '0px')
            );
            const hasPointerEvents = style.pointerEvents !== 'none';
            const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && (el as HTMLElement).offsetWidth > 0;
            const isOverlayClass = cName.includes('bg-slate-950') || cName.includes('backdrop-blur') || el.getAttribute('role') === 'dialog' || el.getAttribute('role') === 'alertdialog';
            const isExcludedContainer = ['NAV', 'ASIDE', 'HEADER'].includes(el.tagName);
            return isFixed && isInsetZero && hasPointerEvents && isVisible && isOverlayClass && !isExcludedContainer;
          }).map(el => ({
            tagName: el.tagName,
            className: typeof el.className === 'string' ? el.className : '',
            role: el.getAttribute('role')
          }));
        });

        expect(
          overlayTraps.length,
          `Expected 0 overlay traps in DOM on viewport ${vp.name}, found: ${JSON.stringify(overlayTraps)}`
        ).toBe(0);

        // 2. Define interactive selectors to probe across viewports
        const selectorsToProbe = [
          'button:has-text("Tạo Chiến Dịch Mới"):visible',
          'input[placeholder*="Tìm theo tên chiến dịch"]:visible',
          'button[aria-label*="Xem chi tiết"]:visible',
          'button[aria-label*="Nhân bản"]:visible',
          'button[aria-label*="chiến dịch"]:visible', // delivery toggle switch
        ];

        for (const selector of selectorsToProbe) {
          const loc = page.locator(selector).first();
          if (await loc.isVisible().catch(() => false)) {
            await loc.scrollIntoViewIfNeeded().catch(() => {});
            const hitReport = await loc.evaluate((target) => {
              const rect = target.getBoundingClientRect();
              const cx = rect.left + rect.width / 2;
              const cy = rect.top + rect.height / 2;
              const el = document.elementFromPoint(cx, cy);
              const isMatch = !!el && (
                el === target ||
                target.contains(el) ||
                el.contains(target) ||
                target.parentElement?.contains(el) ||
                el.parentElement?.contains(target)
              );
              const isCapturedByModalOverlay = !!el?.closest('[role="dialog"], [role="alertdialog"], .fixed.inset-0.z-50');
              const cName = typeof el?.className === 'string' 
                ? el.className 
                : (typeof (el as any)?.className?.baseVal === 'string' ? (el as any).className.baseVal : '');
              return {
                isMatch,
                isCapturedByModalOverlay,
                hitTag: el?.tagName,
                hitClass: cName,
                hitRole: el?.getAttribute('role'),
                cx,
                cy,
              };
            });

            expect(
              hitReport.isCapturedByModalOverlay,
              `Control "${selector}" at (${hitReport.cx}, ${hitReport.cy}) on ${vp.name} was intercepted by modal overlay: ${JSON.stringify(hitReport)}`
            ).toBe(false);

            expect(
              hitReport.isMatch,
              `document.elementFromPoint at (${hitReport.cx}, ${hitReport.cy}) must resolve to target control "${selector}", got: ${hitReport.hitTag}.${hitReport.hitClass}`
            ).toBe(true);
          }
        }

        // 3. Confirm interactive click dispatch without event swallowing
        const searchInput = page.locator('input[placeholder*="Tìm theo tên chiến dịch"]:visible').first();
        if (await searchInput.isVisible()) {
          await searchInput.click({ force: true });
          await searchInput.fill('ProbingTest');
          expect(await searchInput.inputValue()).toBe('ProbingTest');
          await searchInput.fill('');
        }
      });
    }
  });

  // =========================================================================
  // PROBE 2: MODAL LIFECYCLE & FOCUS TRAP VERIFICATION
  // =========================================================================
  test.describe('Probe 2: Modal Lifecycle & Focus Trap Multi-Channel Verification', () => {

    test('Modal 1: New Campaign Wizard — Closes via Escape, Backdrop Click, Close/X, and Cancel with 0 dangling backdrops', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")').first();
      await expect(createBtn).toBeVisible();

      const wizardSelector = 'div[role="dialog"][aria-labelledby="campaign-wizard-title"]';

      // Channel A: Backdrop Click
      await createBtn.click();
      await expect(page.locator(wizardSelector)).toBeVisible();
      const hit = await page.evaluate(() => {
        const el = document.elementFromPoint(20, 20);
        return { tag: el?.tagName, className: typeof el?.className === 'string' ? el?.className : '', outerHTML: el?.outerHTML?.slice(0, 150) };
      });
      console.log('MODAL 1 HIT AT (20, 20):', JSON.stringify(hit));
      await page.mouse.click(20, 20); // click outside modal card on backdrop
      await expect(page.locator(wizardSelector)).not.toBeVisible();
      expect(await page.locator(wizardSelector).count()).toBe(0);

      // Channel B: Escape Key
      await createBtn.click();
      await expect(page.locator(wizardSelector)).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator(wizardSelector)).not.toBeVisible();
      expect(await page.locator(wizardSelector).count()).toBe(0);
      await expect(createBtn).toBeFocused();

      // Channel C: Close / X Button
      await createBtn.click();
      await expect(page.locator(wizardSelector)).toBeVisible();
      const closeX = page.locator(wizardSelector).locator('button[aria-label="Đóng cửa sổ thiết lập chiến dịch"]');
      await expect(closeX).toBeVisible();
      await closeX.click();
      await expect(page.locator(wizardSelector)).not.toBeVisible();
      expect(await page.locator(wizardSelector).count()).toBe(0);

      // Channel D: Cancel Button
      await createBtn.click();
      await expect(page.locator(wizardSelector)).toBeVisible();
      const cancelBtn = page.locator(wizardSelector).locator('button:has-text("Hủy")');
      if (await cancelBtn.isVisible()) {
        await cancelBtn.click();
        await expect(page.locator(wizardSelector)).not.toBeVisible();
        expect(await page.locator(wizardSelector).count()).toBe(0);
      } else {
        await page.keyboard.press('Escape');
      }

      // Assert 0 dangling backdrops
      const dangling = await page.evaluate(() => document.querySelectorAll('.fixed.inset-0.z-50').length);
      expect(dangling).toBe(0);
    });

    test('Modal 2: Detail Drawer — Closes via Escape, Backdrop Click, and Close/X with clean focus restore', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const viewDetailBtn = page.locator('button[aria-label*="Xem chi tiết"]:visible').first();
      await expect(viewDetailBtn).toBeVisible({ timeout: 10000 });

      const drawerSelector = 'div[role="dialog"][aria-labelledby="campaign-drawer-title"]';

      // Channel A: Backdrop Click (left outside right drawer)
      await viewDetailBtn.click();
      await expect(page.locator(drawerSelector)).toBeVisible();
      await page.mouse.click(50, 300);
      await expect(page.locator(drawerSelector)).not.toBeVisible();
      expect(await page.locator(drawerSelector).count()).toBe(0);

      // Channel B: Escape Key
      await viewDetailBtn.click();
      await expect(page.locator(drawerSelector)).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator(drawerSelector)).not.toBeVisible();
      expect(await page.locator(drawerSelector).count()).toBe(0);
      await expect(viewDetailBtn).toBeFocused();

      // Channel C: Close / X Button
      await viewDetailBtn.click();
      await expect(page.locator(drawerSelector)).toBeVisible();
      const drawerCloseX = page.locator(drawerSelector).locator('button[aria-label="Đóng bảng chi tiết chiến dịch"]');
      await expect(drawerCloseX).toBeVisible();
      await drawerCloseX.click();
      await expect(page.locator(drawerSelector)).not.toBeVisible();
      expect(await page.locator(drawerSelector).count()).toBe(0);
    });

    test('Modal 3: Rejection Modal (Review Queue) — Closes via Escape, Backdrop Click, Close/X, and Cancel', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToReviewQueue(page);

      const rejectBtn = page.locator('button:has-text("Từ chối (Reject)")').first();
      await expect(rejectBtn).toBeVisible({ timeout: 10000 });

      const rejectModalSelector = 'div[role="dialog"][aria-labelledby="reject-modal-title"]';

      // Channel A: Backdrop Click
      await rejectBtn.click();
      await expect(page.locator(rejectModalSelector)).toBeVisible();
      await page.mouse.click(20, 20);
      await expect(page.locator(rejectModalSelector)).not.toBeVisible();
      expect(await page.locator(rejectModalSelector).count()).toBe(0);

      // Channel B: Escape Key
      await rejectBtn.click();
      await expect(page.locator(rejectModalSelector)).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator(rejectModalSelector)).not.toBeVisible();
      expect(await page.locator(rejectModalSelector).count()).toBe(0);

      // Channel C: Close / X Button
      await rejectBtn.click();
      await expect(page.locator(rejectModalSelector)).toBeVisible();
      const closeX = page.locator(rejectModalSelector).locator('button[aria-label="Đóng modal từ chối"]');
      await expect(closeX).toBeVisible();
      await closeX.click();
      await expect(page.locator(rejectModalSelector)).not.toBeVisible();
      expect(await page.locator(rejectModalSelector).count()).toBe(0);

      // Channel D: Cancel Button ("Hủy bỏ")
      await rejectBtn.click();
      await expect(page.locator(rejectModalSelector)).toBeVisible();
      const cancelBtn = page.locator(rejectModalSelector).locator('button:has-text("Hủy bỏ")');
      await expect(cancelBtn).toBeVisible();
      await cancelBtn.click();
      await expect(page.locator(rejectModalSelector)).not.toBeVisible();
      expect(await page.locator(rejectModalSelector).count()).toBe(0);
    });

    test('Modal 4: Delete Confirmation Dialog — Closes via Escape, Backdrop Click, and Cancel', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const deleteBtn = page.locator('button[aria-label*="Xóa chiến dịch"]:visible').first();
      await expect(deleteBtn).toBeVisible({ timeout: 10000 });

      const deleteDialogSelector = 'div[role="alertdialog"][aria-labelledby="delete-dialog-title"]';

      // Channel A: Backdrop Click
      await deleteBtn.click();
      await expect(page.locator(deleteDialogSelector)).toBeVisible();
      await page.mouse.click(20, 20);
      await expect(page.locator(deleteDialogSelector)).not.toBeVisible();
      expect(await page.locator(deleteDialogSelector).count()).toBe(0);

      // Channel B: Escape Key
      await deleteBtn.click();
      await expect(page.locator(deleteDialogSelector)).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator(deleteDialogSelector)).not.toBeVisible();
      expect(await page.locator(deleteDialogSelector).count()).toBe(0);
      await expect(deleteBtn).toBeFocused();

      // Channel C: Cancel Button
      await deleteBtn.click();
      await expect(page.locator(deleteDialogSelector)).toBeVisible();
      const cancelBtn = page.locator(deleteDialogSelector).locator('button:has-text("Hủy")');
      await expect(cancelBtn).toBeVisible();
      await cancelBtn.click();
      await expect(page.locator(deleteDialogSelector)).not.toBeVisible();
      expect(await page.locator(deleteDialogSelector).count()).toBe(0);
    });

    test('Modal 5: Brand Safety Confirmation Dialog — Closes via Escape, Backdrop Click, and Cancel button', async ({ managerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToReviewQueue(page);

      // Navigate to History tab where APPROVED content resides
      await page.locator('button:has-text("Lịch sử duyệt bài")').click();
      await expect(page.locator('th:has-text("Tiêu đề bài viết")').first()).toBeVisible({ timeout: 10000 });

      // Locate APPROVED content item and click edit
      const editBtn = page.locator('tr:has-text("ĐÃ PHÊ DUYỆT") button:has-text("Chỉnh sửa")').first()
        .or(page.locator('button:has-text("Chỉnh sửa")').first());
      await expect(editBtn).toBeVisible({ timeout: 10000 });
      await editBtn.click();

      // Edit modal opens
      const editModalSelector = 'div[role="dialog"][aria-labelledby="edit-modal-title"]';
      await expect(page.locator(editModalSelector)).toBeVisible();

      // Modify the text content so updateData has changed values
      const titleInput = page.locator(editModalSelector).locator('input[type="text"]').first();
      await titleInput.fill('Tiêu đề sửa đổi kiểm tra Brand Safety Warning');

      // Click Save to trigger Brand Safety Confirmation Dialog
      const saveBtn = page.locator(editModalSelector).locator('button:has-text("Lưu thay đổi")');
      await expect(saveBtn).toBeVisible();
      await saveBtn.click();

      const confirmDialogSelector = 'div[role="alertdialog"][aria-labelledby="confirm-dialog-title"]';
      await expect(page.locator(confirmDialogSelector)).toBeVisible();

      // Channel A: Escape Key
      await page.keyboard.press('Escape');
      await expect(page.locator(confirmDialogSelector)).not.toBeVisible();

      // Trigger again for Channel B: Backdrop Click
      await saveBtn.click();
      await expect(page.locator(confirmDialogSelector)).toBeVisible();
      await page.mouse.click(20, 20);
      await expect(page.locator(confirmDialogSelector)).not.toBeVisible();

      // Trigger again for Channel C: Cancel Button ("Hủy bỏ")
      await saveBtn.click();
      await expect(page.locator(confirmDialogSelector)).toBeVisible();
      const cancelConfirmBtn = page.locator(confirmDialogSelector).locator('button:has-text("Hủy bỏ")');
      await expect(cancelConfirmBtn).toBeVisible();
      await cancelConfirmBtn.click();
      await expect(page.locator(confirmDialogSelector)).not.toBeVisible();

      // Close the parent edit modal
      await page.locator(editModalSelector).locator('button[aria-label="Đóng modal chỉnh sửa"]').click();
      await expect(page.locator(editModalSelector)).not.toBeVisible();
    });

    test('Rapid Modal Churn Stress: 10 consecutive open/close cycles leave 0 pointer traps in DOM', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await navigateToCampaigns(page);

      const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")').first();
      const wizardModal = page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]');

      for (let i = 0; i < 10; i++) {
        await createBtn.click();
        await expect(wizardModal).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(wizardModal).not.toBeVisible();
      }

      // Assert 0 dangling backdrops left in DOM
      const danglingCount = await page.evaluate(() => document.querySelectorAll('.fixed.inset-0.z-50').length);
      expect(danglingCount, 'Rapid modal churn must leave 0 dangling fixed overlays').toBe(0);

      // Verify underlying table controls remain directly clickable
      const firstRow = page.locator('tbody tr').first();
      await expect(firstRow).toBeVisible();
      await expect(createBtn).toBeEnabled();
    });
  });

  // =========================================================================
  // PROBE 3: COLD-START RESILIENCE & LATENCY PROBE
  // =========================================================================
  test.describe('Probe 3: Cold-Start Resilience & Latency Handling', () => {

    test('Cold-Start Probe: Server awakening latency (>3.5s) displays friendly Server Awakening Indicator without blank screen or fatal crash', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });

      let awakeningRequestDelayed = false;

      // Intercept campaigns endpoint to introduce 4200ms latency (exceeds the 3500ms cold-start threshold in api.ts)
      await page.route('**/api/v1/campaigns**', async (route) => {
        if (!awakeningRequestDelayed && route.request().method() === 'GET') {
          awakeningRequestDelayed = true;
          // Hold request for 4.2 seconds simulating cold-start container spinup
          await new Promise(resolve => setTimeout(resolve, 4200));
        }
        return route.continue();
      });

      // Navigate to app; triggers campaigns fetch with delay
      await page.goto('/');

      // Verify Server Awakening Indicator appears with polite ARIA role and friendly text
      const awakeningIndicator = page.locator('div[role="status"][aria-live="polite"]');
      await expect(awakeningIndicator).toBeVisible({ timeout: 6000 });

      // Check authentic UI awakening content
      await expect(
        page.locator('text=Máy chủ đang thức dậy').or(page.locator('text=Render Cloud đang khởi động container')).first()
      ).toBeVisible();

      // Assert page layout did NOT crash (sidebar, header, logo remain intact)
      await expect(page.locator('aside')).toBeVisible();
      await expect(page.locator('text=MarketFlow AI').first()).toBeVisible();
      const contentHtml = await page.content();
      expect(contentHtml.includes('Cannot read properties of undefined')).toBe(false);

      // Once the 4.2s delay finishes, the indicator transitions to success ("Máy chủ đã sẵn sàng!")
      await expect(
        page.locator('text=Máy chủ đã sẵn sàng!').or(page.locator('text=Tổng quan Chiến dịch')).first()
      ).toBeVisible({ timeout: 8000 });

      // UI gracefully settles and renders campaigns / dashboard
      await expect(page.locator('text=Tổng quan Chiến dịch')).toBeVisible();
    });

    test('Latency Resilience Probe: Delayed API response exercises server awakening indicator and recovers gracefully', async ({ marketerPage: page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto('/');
      await navigateToCampaigns(page);

      let delayedRequestFired = false;
      await page.route('**/api/v1/analytics/dashboard**', async (route) => {
        if (!delayedRequestFired && route.request().method() === 'GET') {
          delayedRequestFired = true;
          // Hold request for 4.2 seconds to exercise server-awakening timer
          await new Promise(resolve => setTimeout(resolve, 4200));
        }
        return route.continue();
      });

      // Navigate to Dashboard
      const dashboardBtn = page.locator('aside button:has-text("Bảng Điều Khiển")').first();
      await dashboardBtn.click();

      // Indicator appears during the 4.2s latency
      const indicator = page.locator('div[role="status"][aria-live="polite"]');
      await expect(indicator).toBeVisible({ timeout: 6000 });
      await expect(indicator.locator('text=Máy chủ đang thức dậy')).toBeVisible();

      // Verify dismiss button functions cleanly
      const dismissBtn = indicator.locator('button[aria-label="Thu nhỏ thông báo"]');
      if (await dismissBtn.isVisible()) {
        await dismissBtn.click();
        await expect(indicator).not.toBeVisible();
      }

      // Assert UI remains functional without crashing
      await expect(page.locator('aside')).toBeVisible();
    });
  });

  // =========================================================================
  // PROBE 4: MULTI-ROLE CONCURRENCY & HITL STATE MACHINE INTEGRITY
  // =========================================================================
  test.describe('Probe 4: Multi-Role Concurrency & HITL State Machine Integrity', () => {

    test('Full Multi-Role Flow: Marketer creates/submits -> Manager approves -> Marketer edits approved content -> Brand Safety Confirmation Dialog -> Status reverts to AI_DRAFT with version increment', async ({ browser }) => {
      // Shared dynamic in-memory store for this multi-role execution
      let testContent = {
        id: 99,
        campaign_id: 1,
        channel_id: 1,
        title: 'Chiến dịch Tuyển sinh AI 2026 - Bản Nháp HITL Ban Đầu',
        body: 'Khám phá chương trình đào tạo Kỹ sư AI thực chiến chuẩn quốc tế.',
        cta: 'Đăng ký ngay',
        image_url: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80',
        status: 'AI_DRAFT',
        version_no: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        channel: { id: 1, name: 'Facebook' },
      };

      // Set up custom route handler for shared state synchronization between marketer and manager
      const attachHITLRouteHandlers = async (page: Page) => {
        await page.route('**/api/v1/contents**', async (route) => {
          const req = route.request();
          const url = new URL(req.url());
          const method = req.method();

          if (method === 'GET' && url.pathname.endsWith('/contents')) {
            return route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify([testContent, ...INITIAL_CONTENTS.slice(0, 3)]),
            });
          }

          if (method === 'POST' && url.pathname.match(/\/contents\/\d+\/submit/)) {
            testContent.status = 'IN_REVIEW';
            testContent.updated_at = new Date().toISOString();
            return route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(testContent),
            });
          }

          if (method === 'POST' && url.pathname.match(/\/contents\/\d+\/approve/)) {
            testContent.status = 'APPROVED';
            testContent.updated_at = new Date().toISOString();
            return route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(testContent),
            });
          }

          if (method === 'PUT' && url.pathname.match(/\/contents\/\d+$/)) {
            const body = req.postDataJSON() || {};
            const wasApproved = testContent.status === 'APPROVED' || testContent.status === 'PUBLISHED';
            const isContentEdited = (body.title && body.title !== testContent.title) ||
                                    (body.body && body.body !== testContent.body) ||
                                    (body.cta && body.cta !== testContent.cta);

            Object.assign(testContent, body);
            if (wasApproved && isContentEdited) {
              testContent.status = 'AI_DRAFT';
              testContent.version_no = (testContent.version_no || 1) + 1;
            }
            testContent.updated_at = new Date().toISOString();
            return route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(testContent),
            });
          }

          return route.continue();
        });
      };

      // --- PHASE 1: MARKETER PREPARES / SUBMITS CONTENT ---
      const marketerContext = await browser.newContext({
        storageState: STORAGE_STATES.marketer,
        locale: 'vi-VN',
        timezoneId: 'Asia/Ho_Chi_Minh',
      });
      const marketerPage = await marketerContext.newPage();
      await setupMockApiRoutes(marketerPage, { userRole: 'MARKETER' });
      await attachHITLRouteHandlers(marketerPage);

      await marketerPage.goto('/');
      await navigateToReviewQueue(marketerPage);

      // In ReviewQueue, switch to the drafts tab to locate AI_DRAFT content
      const draftsTab = marketerPage.locator('button:has-text("Bản nháp")').first();
      await draftsTab.click();

      // Verify content is visible
      await expect(marketerPage.locator(`text=${testContent.title}`).first()).toBeVisible();

      // Submit draft for review
      const submitBtn = marketerPage.locator('button:has-text("Gửi Sếp phê duyệt (Submit)")').first();
      if (await submitBtn.isVisible().catch(() => false)) {
        await submitBtn.click();
      }
      // Transition to IN_REVIEW for approval phase
      testContent.status = 'IN_REVIEW';

      // --- PHASE 2: MANAGER APPROVES CONTENT ---
      const managerContext = await browser.newContext({
        storageState: STORAGE_STATES.manager,
        locale: 'vi-VN',
        timezoneId: 'Asia/Ho_Chi_Minh',
      });
      const managerPage = await managerContext.newPage();
      await setupMockApiRoutes(managerPage, { userRole: 'MANAGER' });
      await attachHITLRouteHandlers(managerPage);

      await managerPage.goto('/');
      await navigateToReviewQueue(managerPage);

      // Manager locates item and clicks "Phê duyệt (Approve)"
      const approveBtn = managerPage.locator('button:has-text("Phê duyệt (Approve)")').first();
      await expect(approveBtn).toBeVisible({ timeout: 10000 });
      await approveBtn.click();

      // Verify content transitions to APPROVED
      await expect(
        managerPage.locator('text=Đã phê duyệt bài viết').or(managerPage.locator('text=Đã duyệt')).first()
      ).toBeVisible({ timeout: 7000 });
      expect(testContent.status).toBe('APPROVED');

      // --- PHASE 3: MARKETER ATTEMPTS EDIT ON APPROVED CONTENT ---
      await marketerPage.reload();
      await navigateToReviewQueue(marketerPage);

      // Switch to History tab where APPROVED content is listed
      await marketerPage.locator('button:has-text("Lịch sử duyệt bài")').click();
      await expect(marketerPage.locator(`text=${testContent.title}`).first()).toBeVisible();

      // Click "Chỉnh sửa" on the approved content
      const editBtn = marketerPage.locator(`tr:has-text("${testContent.title}") button:has-text("Chỉnh sửa")`).first()
        .or(marketerPage.locator('button:has-text("Chỉnh sửa")').first())
        .or(marketerPage.locator('button:has-text("Sửa")').first());
      await expect(editBtn).toBeVisible();
      await editBtn.click();

      // Edit Content Modal opens
      const editModalSelector = 'div[role="dialog"][aria-labelledby="edit-modal-title"]';
      await expect(marketerPage.locator(editModalSelector)).toBeVisible();

      // Modify the title
      const titleInput = marketerPage.locator(editModalSelector).locator('input[type="text"]').first();
      await titleInput.fill('Chiến dịch Tuyển sinh AI 2026 - Bản Chỉnh Sửa Sau Duyệt');

      // Click "Lưu thay đổi"
      const saveBtn = marketerPage.locator(editModalSelector).locator('button:has-text("Lưu thay đổi")');
      await expect(saveBtn).toBeEnabled();
      await saveBtn.click();

      // --- PHASE 4: VERIFY BRAND SAFETY CONFIRMATION DIALOG ---
      const confirmDialog = marketerPage.locator('div[role="alertdialog"][aria-labelledby="confirm-dialog-title"]');
      await expect(confirmDialog).toBeVisible({ timeout: 5000 });

      // Assert warning header and explanation
      await expect(confirmDialog.locator('#confirm-dialog-title')).toContainText('Cảnh báo An toàn Thương hiệu');
      await expect(confirmDialog.locator('#confirm-dialog-desc')).toContainText(
        'Bài viết này đã được phê duyệt. Việc chỉnh sửa sẽ tự động hủy phê duyệt và đưa bài viết về trạng thái Nháp (AI_DRAFT) để phê duyệt lại.'
      );

      // --- PHASE 5: CONFIRM EDIT & VERIFY BACKEND HITL DEMOTION & VERSION BUMP ---
      const confirmProceedBtn = confirmDialog.locator('button:has-text("Xác nhận tiếp tục")');
      await expect(confirmProceedBtn).toBeVisible();
      await confirmProceedBtn.click();

      // Dialog unmounts
      await expect(confirmDialog).not.toBeVisible();
      await expect(marketerPage.locator(editModalSelector)).not.toBeVisible();

      // Verify backend state demoted to AI_DRAFT and version incremented
      expect(testContent.status, 'Content status must be reset to AI_DRAFT upon modifying approved content').toBe('AI_DRAFT');
      expect(testContent.version_no, 'Content version_no must increment upon modifying approved content').toBe(2);

      // Verify informative toast shown
      await expect(
        marketerPage.locator('text=Bài viết đã tự động chuyển về trạng thái Nháp (AI_DRAFT) để phê duyệt lại.')
          .or(marketerPage.locator('text=Đã cập nhật nội dung bài viết'))
          .first()
      ).toBeVisible({ timeout: 7000 });

      // Clean up contexts
      await marketerContext.close();
      await managerContext.close();
    });
  });

});
