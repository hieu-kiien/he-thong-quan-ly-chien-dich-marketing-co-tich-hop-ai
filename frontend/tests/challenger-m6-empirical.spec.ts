import { test, expect } from './e2e/fixtures/auth.fixture';

/**
 * Challenger M6 Empirical Audit Test Suite
 * Independent empirical stress tests proving flaws and measuring oracle validity.
 */

test.describe('Challenger M6: Empirical Audit & Oracle Validation', () => {

  test('Oracle Flaw 1: Probe 1 crashes with SyntaxError on Document.querySelector due to Playwright pseudo-selectors', async ({ marketerPage: page }) => {
    await page.goto('/');
    
    // Demonstrate exact error in Worker M6 line 132:
    const invalidSelector = 'button:has-text("Tạo Chiến Dịch Mới"):visible';
    let caughtError: string | null = null;
    try {
      await page.evaluate((sel) => {
        document.querySelector(sel);
      }, invalidSelector);
    } catch (err: any) {
      caughtError = err.message;
    }

    expect(caughtError).not.toBeNull();
    expect(caughtError).toContain('SyntaxError');
    expect(caughtError).toContain('is not a valid selector');
  });

  test('Oracle Validation: document.elementFromPoint accurately detects invisible interception layer when correctly evaluated', async ({ marketerPage: page }) => {
    await page.goto('/');
    const campaignBtn = page.locator('aside button:has-text("Quản Lý Chiến Dịch")').first();
    await campaignBtn.click({ force: true });
    await expect(page.locator('h1:has-text("Quản trị Chiến dịch")').or(page.locator('h1:has-text("Chiến dịch")'))).toBeVisible();

    const targetButton = page.locator('button:has-text("Tạo Chiến Dịch Mới")').first();
    await expect(targetButton).toBeVisible();
    const box = await targetButton.boundingBox();
    expect(box).not.toBeNull();
    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;

    // 1. Without invisible trap: elementFromPoint resolves to target button or its child
    const initialHit = await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      return { tagName: el?.tagName, text: el?.textContent?.trim() };
    }, { x: cx, y: cy });
    expect(initialHit.text).toContain('Tạo Chiến Dịch Mới');

    // 2. Inject adversarial invisible overlay covering the screen
    await page.evaluate(() => {
      const trap = document.createElement('div');
      trap.id = 'adversarial-clickjack-trap';
      trap.setAttribute('style', 'position: fixed; inset: 0; z-index: 999999; background: transparent; pointer-events: auto;');
      document.body.appendChild(trap);
    });

    // 3. Probe with elementFromPoint: MUST detect interception by adversarial overlay
    const interceptedHit = await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      return { id: el?.id, tagName: el?.tagName };
    }, { x: cx, y: cy });

    expect(interceptedHit.id).toBe('adversarial-clickjack-trap');

    // 4. Remove trap and verify pointer recovery
    await page.evaluate(() => {
      document.getElementById('adversarial-clickjack-trap')?.remove();
    });

    const recoveredHit = await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      return { text: el?.textContent?.trim() };
    }, { x: cx, y: cy });
    expect(recoveredHit.text).toContain('Tạo Chiến Dịch Mới');
  });

  test('Oracle Flaw 2: ReviewQueue Rejection Modal lacks backdrop click dismissal handler', async ({ managerPage: page }) => {
    await page.goto('/');
    const targetBtn = page.locator('aside button:has-text("Hàng Đợi Phê Duyệt")').first();
    await targetBtn.click({ force: true });
    await expect(page.locator('h2:has-text("Hàng đợi Phê duyệt")')).toBeVisible();

    const rejectBtn = page.locator('button:has-text("Từ chối (Reject)")').first();
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();

    const rejectModal = page.locator('div[role="dialog"][aria-labelledby="reject-modal-title"]');
    await expect(rejectModal).toBeVisible();

    // Click outside on backdrop (top-left 20, 20)
    await page.mouse.click(20, 20);

    // Modal STILL remains visible because ReviewQueue.tsx line 677 backdrop div has no onClick
    const isStillVisible = await rejectModal.isVisible();
    expect(isStillVisible).toBe(true);

    // Close via close button to clean up
    await page.locator('button[aria-label="Đóng modal từ chối"]').click();
    await expect(rejectModal).not.toBeVisible();
  });

  test('Oracle Flaw 3: Non-existent sidebar button "Hiệu Quả & ROI"', async ({ marketerPage: page }) => {
    await page.goto('/');
    const analyticsBtn = page.locator('aside button:has-text("Hiệu Quả & ROI")');
    const count = await analyticsBtn.count();
    expect(count, 'Button "Hiệu Quả & ROI" should not exist in Sidebar.tsx').toBe(0);
  });

  test('Stress Test: 20 consecutive modal open/close cycles on New Campaign Wizard confirm zero orphaned backdrops and unlocked pointer', async ({ marketerPage: page }) => {
    await page.goto('/');
    const campaignBtn = page.locator('aside button:has-text("Quản Lý Chiến Dịch")').first();
    await campaignBtn.click({ force: true });
    await expect(page.locator('h1:has-text("Quản trị Chiến dịch")').or(page.locator('h1:has-text("Chiến dịch")'))).toBeVisible();

    const createBtn = page.locator('button:has-text("Tạo Chiến Dịch Mới")').first();
    const wizardModal = page.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]');

    for (let i = 0; i < 20; i++) {
      await createBtn.click();
      await expect(wizardModal).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(wizardModal).not.toBeVisible();
    }

    // Assert 0 dangling backdrops
    const dangling = await page.evaluate(() => document.querySelectorAll('.fixed.inset-0.z-50').length);
    expect(dangling).toBe(0);

    // Assert pointer interaction is unlocked: click table row and search input
    const searchInput = page.locator('input[placeholder*="Tìm theo tên chiến dịch"]:visible').first();
    await searchInput.click();
    await searchInput.fill('StressPass');
    expect(await searchInput.inputValue()).toBe('StressPass');
    await searchInput.fill('');
  });

});
