import { test as baseTest, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { test as authTest } from '../e2e/fixtures/auth.fixture';

/**
 * Wave 3 Adversarial Testing Suite:
 * - 320px viewport & 200% zoom reflow probe
 * - 0 horizontal scrollbar, 0 text clipping, 0 overlapping interactive elements
 * - Dynamic sub-components: AIDrawer, BrandKitModal, CampaignWizard, ReviewQueue reject modal, SocialPreviews, KPIGrid9, AIDoctor
 * - Color contrast ratios & missing labels
 * - Edge case dynamic viewport resizes
 */

const CORE_TABS = [
  { label: 'Bảng Điều Khiển', selector: 'text=Command Center Điều Phối' },
  { label: 'Quản Lý Chiến Dịch', selector: 'text=Quản trị Chiến dịch' },
  { label: 'Xưởng Sáng Tạo AI', selector: 'text=AI Marketing Copilot' },
  { label: 'Lịch Xuất Bản', selector: 'text=Lịch Xuất Bản' },
  { label: 'Hàng Đợi Phê Duyệt', selector: 'text=Hàng đợi Phê duyệt' },
  { label: 'Cài Đặt & Brand Kit', selector: 'text=Trung tâm Cài đặt' },
];

async function navigateToTab(page: Page, label: string) {
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
  const targetBtn = page.locator(`aside button:has-text("${label}")`).first();
  await targetBtn.click({ force: true });
  await page.waitForTimeout(400);
}

async function checkHorizontalScroll(page: Page, contextName: string) {
  return await page.evaluate((ctx) => {
    const docEl = document.documentElement;
    const body = document.body;
    const scrollWidth = Math.max(docEl.scrollWidth, body.scrollWidth);
    const innerWidth = window.innerWidth;
    const hasHorizontalOverflow = scrollWidth > innerWidth + 1; // 1px sub-pixel tolerance
    return {
      contextName: ctx,
      scrollWidth,
      innerWidth,
      hasHorizontalOverflow
    };
  }, contextName);
}

async function checkTextClipping(page: Page, contextName: string) {
  return await page.evaluate((ctx) => {
    const issues: any[] = [];
    const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, label, button, th, td');
    for (const el of Array.from(elements)) {
      const htmlEl = el as HTMLElement;
      if (htmlEl.offsetParent === null && htmlEl.offsetWidth === 0 && htmlEl.offsetHeight === 0) continue;
      const style = window.getComputedStyle(htmlEl);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
      const rect = htmlEl.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) continue;

      const hasOverflowHidden = style.overflow === 'hidden' || style.overflowX === 'hidden' || style.overflowY === 'hidden';
      const hasEllipsis = style.textOverflow === 'ellipsis';

      // Horizontal text clipping without ellipsis
      if (hasOverflowHidden && !hasEllipsis && htmlEl.scrollWidth > htmlEl.clientWidth + 6) {
        if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(htmlEl.tagName)) {
          issues.push({
            context: ctx,
            tag: htmlEl.tagName,
            text: htmlEl.innerText?.slice(0, 40),
            scrollWidth: htmlEl.scrollWidth,
            clientWidth: htmlEl.clientWidth,
            type: 'horizontal_clipping'
          });
        }
      }

      // Vertical text clipping
      const hasLineClamp = (style as any).webkitLineClamp && (style as any).webkitLineClamp !== 'none';
      if (hasOverflowHidden && !hasLineClamp && htmlEl.scrollHeight > htmlEl.clientHeight + 8 && htmlEl.clientHeight > 0) {
        if (!['INPUT', 'SELECT', 'TEXTAREA', 'DIV', 'BODY', 'HTML'].includes(htmlEl.tagName)) {
          issues.push({
            context: ctx,
            tag: htmlEl.tagName,
            text: htmlEl.innerText?.slice(0, 40),
            scrollHeight: htmlEl.scrollHeight,
            clientHeight: htmlEl.clientHeight,
            type: 'vertical_clipping'
          });
        }
      }
    }
    return issues;
  }, contextName);
}

async function checkInteractiveOverlap(page: Page, contextName: string) {
  return await page.evaluate((ctx) => {
    const interactiveElements = Array.from(
      document.querySelectorAll('button, input, select, textarea, a[href]')
    ) as HTMLElement[];

    const visibleItems: { el: HTMLElement; rect: DOMRect; label: string }[] = [];
    for (const el of interactiveElements) {
      if (el.offsetParent === null && el.offsetWidth === 0 && el.offsetHeight === 0) continue;
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || style.pointerEvents === 'none') continue;
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) continue;
      // Onscreen bounds
      if (rect.bottom < 0 || rect.top > window.innerHeight || rect.right < 0 || rect.left > window.innerWidth) continue;

      visibleItems.push({
        el,
        rect,
        label: el.innerText || el.getAttribute('aria-label') || el.getAttribute('name') || el.tagName
      });
    }

    const collisions: any[] = [];
    for (let i = 0; i < visibleItems.length; i++) {
      for (let j = i + 1; j < visibleItems.length; j++) {
        const a = visibleItems[i];
        const b = visibleItems[j];

        if (a.el.contains(b.el) || b.el.contains(a.el)) continue;

        const xOverlap = Math.max(0, Math.min(a.rect.right, b.rect.right) - Math.max(a.rect.left, b.rect.left));
        const yOverlap = Math.max(0, Math.min(a.rect.bottom, b.rect.bottom) - Math.max(a.rect.top, b.rect.top));
        const overlapArea = xOverlap * yOverlap;

        if (overlapArea > 80) {
          collisions.push({
            context: ctx,
            elemA: { tag: a.el.tagName, label: a.label.slice(0, 30), rect: { x: Math.round(a.rect.x), y: Math.round(a.rect.y), w: Math.round(a.rect.width), h: Math.round(a.rect.height) } },
            elemB: { tag: b.el.tagName, label: b.label.slice(0, 30), rect: { x: Math.round(b.rect.x), y: Math.round(b.rect.y), w: Math.round(b.rect.width), h: Math.round(b.rect.height) } },
            overlapArea: Math.round(overlapArea)
          });
        }
      }
    }
    return collisions;
  }, contextName);
}

authTest.describe('Wave 3 Adversarial A11y & Viewport Probe Suite', () => {

  // =========================================================================
  // PROBE 1: 320px Viewport at 100% and 200% Zoom Reflow
  // =========================================================================
  authTest('Probe 1: 320px Viewport & 200% Zoom: 0 horizontal scroll, 0 clipping, 0 collision', async ({ marketerPage }) => {
    authTest.setTimeout(120000);
    // Set minimal viewport to 320px
    await marketerPage.setViewportSize({ width: 320, height: 568 });
    await marketerPage.waitForTimeout(500);

    const findings = {
      overflowIssues: [] as any[],
      clippingIssues: [] as any[],
      overlapCollisions: [] as any[]
    };

    for (const tab of CORE_TABS) {
      await navigateToTab(marketerPage, tab.label);
      await marketerPage.waitForTimeout(400);

      // --- 100% Zoom ---
      const scroll100 = await checkHorizontalScroll(marketerPage, `${tab.label} @ 100%`);
      if (scroll100.hasHorizontalOverflow) findings.overflowIssues.push(scroll100);

      const clip100 = await checkTextClipping(marketerPage, `${tab.label} @ 100%`);
      if (clip100.length > 0) findings.clippingIssues.push(...clip100);

      const overlap100 = await checkInteractiveOverlap(marketerPage, `${tab.label} @ 100%`);
      if (overlap100.length > 0) findings.overlapCollisions.push(...overlap100);

      // --- 200% Zoom ---
      await marketerPage.evaluate(() => {
        document.body.style.zoom = '200%';
      });
      await marketerPage.waitForTimeout(400);

      const scroll200 = await checkHorizontalScroll(marketerPage, `${tab.label} @ 200% Zoom`);
      if (scroll200.hasHorizontalOverflow) findings.overflowIssues.push(scroll200);

      const clip200 = await checkTextClipping(marketerPage, `${tab.label} @ 200% Zoom`);
      if (clip200.length > 0) findings.clippingIssues.push(...clip200);

      const overlap200 = await checkInteractiveOverlap(marketerPage, `${tab.label} @ 200% Zoom`);
      if (overlap200.length > 0) findings.overlapCollisions.push(...overlap200);

      // Reset zoom
      await marketerPage.evaluate(() => {
        document.body.style.zoom = '100%';
      });
      await marketerPage.waitForTimeout(200);
    }

    console.log('=== PROBE 1 AUDIT RESULTS ===');
    console.log('Overflow Issues count:', findings.overflowIssues.length, JSON.stringify(findings.overflowIssues, null, 2));
    console.log('Clipping Issues count:', findings.clippingIssues.length, JSON.stringify(findings.clippingIssues, null, 2));
    console.log('Overlap Collisions count:', findings.overlapCollisions.length, JSON.stringify(findings.overlapCollisions, null, 2));

    expect(findings.overflowIssues, `Found ${findings.overflowIssues.length} horizontal overflow issues`).toEqual([]);
    expect(findings.clippingIssues, `Found ${findings.clippingIssues.length} text clipping issues`).toEqual([]);
    expect(findings.overlapCollisions, `Found ${findings.overlapCollisions.length} overlapping interactive elements`).toEqual([]);
  });

  // =========================================================================
  // PROBE 2: AIDrawer Missing Form Labels & Accessibility
  // =========================================================================
  authTest('Probe 2: AIDrawer Missing Form Labels & Multi-tab Forms', async ({ marketerPage }) => {
    authTest.setTimeout(60000);
    await marketerPage.setViewportSize({ width: 1280, height: 800 });
    await navigateToTab(marketerPage, 'Bảng Điều Khiển');
    await marketerPage.waitForTimeout(500);

    // Open AI Drawer via Campaign table "AI Viết" button
    const aiWriteBtn = marketerPage.locator('button:has-text("AI Viết")').first();
    await expect(aiWriteBtn).toBeVisible({ timeout: 10000 });
    await aiWriteBtn.click();

    // Verify AIDrawer header visible
    const drawerTitle = marketerPage.locator('h3:has-text("AI Marketing Copilot")');
    await expect(drawerTitle).toBeVisible({ timeout: 10000 });

    // Run Axe scan on AIDrawer
    const scanResult = await new AxeBuilder({ page: marketerPage })
      .include('.fixed.inset-0.z-50')
      .withRules(['color-contrast', 'label', 'button-name', 'select-name'])
      .analyze();

    console.log('=== AIDrawer Axe Violations ===', JSON.stringify(scanResult.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, nodes: v.nodes.map(n => n.html) })), null, 2));

    // Specifically verify omniBrief textarea has accessible label
    const omniBriefTextarea = marketerPage.locator('textarea[placeholder*="Bản tóm tắt chiến dịch"]').or(marketerPage.locator('textarea[placeholder*="Chiến dịch tuyển sinh"]')).first();
    if (await omniBriefTextarea.isVisible()) {
      const hasLabel = await omniBriefTextarea.evaluate((el) => {
        const id = el.id;
        const hasAriaLabel = el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby');
        const hasMatchingLabel = id ? !!document.querySelector(`label[for="${id}"]`) : false;
        const wrappedByLabel = !!el.closest('label');
        return hasAriaLabel || hasMatchingLabel || wrappedByLabel;
      });
      console.log('omniBrief textarea accessible label attached:', hasLabel);
      expect(hasLabel, 'omniBrief textarea lacks accessible label (WCAG 4.1.2 / 3.3.2)').toBe(true);
    }

    expect(scanResult.violations, `AIDrawer has ${scanResult.violations.length} violations`).toEqual([]);
  });

  // =========================================================================
  // PROBE 3: Campaign Wizard Color Contrast Ratios
  // =========================================================================
  authTest('Probe 3: Campaign Creation Wizard Color Contrast Ratios (WCAG 1.4.3)', async ({ marketerPage }) => {
    authTest.setTimeout(60000);
    await marketerPage.setViewportSize({ width: 1280, height: 800 });
    await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');

    const createBtn = marketerPage.locator('button:has-text("Tạo Chiến Dịch Mới")');
    await createBtn.click();

    const wizardModal = marketerPage.locator('div[role="dialog"][aria-labelledby="campaign-wizard-title"]');
    await expect(wizardModal).toBeVisible();

    // Check Step 1 contrast violations
    const stepScan = await new AxeBuilder({ page: marketerPage })
      .include('div[role="dialog"]')
      .withRules(['color-contrast'])
      .analyze();

    console.log('=== Campaign Wizard Step 1 Contrast Violations ===', JSON.stringify(stepScan.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, nodes: v.nodes.map(n => ({ html: n.html, failureSummary: n.failureSummary })) })), null, 2));

    expect(stepScan.violations, `Wizard Step 1 has ${stepScan.violations.length} contrast violations`).toEqual([]);
  });

  // =========================================================================
  // PROBE 4: Social Previews & Sub-components Missing Labels
  // =========================================================================
  authTest('Probe 4: Social Previews & Image Picker Missing Labels', async ({ managerPage }) => {
    authTest.setTimeout(60000);
    await managerPage.setViewportSize({ width: 1280, height: 800 });
    await navigateToTab(managerPage, 'Hàng Đợi Phê Duyệt');

    // Run Axe scan on ReviewQueue
    const scanResult = await new AxeBuilder({ page: managerPage })
      .withRules(['color-contrast', 'label', 'button-name'])
      .analyze();

    console.log('=== ReviewQueue & Social Previews Violations ===', JSON.stringify(scanResult.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, nodes: v.nodes.map(n => n.html) })), null, 2));

    expect(scanResult.violations, `ReviewQueue has ${scanResult.violations.length} violations`).toEqual([]);
  });

  // =========================================================================
  // PROBE 5: Edge Case Dynamic Viewport Resizing
  // =========================================================================
  authTest('Probe 5: Rapid Dynamic Resizes (1440px -> 300px -> Landscape -> 1440px)', async ({ marketerPage }) => {
    authTest.setTimeout(60000);
    const errors: string[] = [];
    marketerPage.on('pageerror', (err) => errors.push(err.message));

    await navigateToTab(marketerPage, 'Quản Lý Chiến Dịch');

    const testSizes = [
      { name: 'Desktop 1440px', width: 1440, height: 900 },
      { name: 'Tablet 768px', width: 768, height: 1024 },
      { name: 'Mobile 390px', width: 390, height: 844 },
      { name: 'Min 320px', width: 320, height: 568 },
      { name: 'Extreme Narrow 300px', width: 300, height: 600 },
      { name: 'Landscape Mobile 568x320', width: 568, height: 320 },
      { name: 'Back to Desktop 1280px', width: 1280, height: 800 },
    ];

    for (const size of testSizes) {
      await marketerPage.setViewportSize({ width: size.width, height: size.height });
      await marketerPage.waitForTimeout(200);

      // Assert 0 horizontal overflow (for widths >= 320px)
      if (size.width >= 320) {
        const scrollInfo = await checkHorizontalScroll(marketerPage, size.name);
        expect(
          scrollInfo.hasHorizontalOverflow,
          `[${size.name}] Viewport resize caused horizontal scroll: ${scrollInfo.scrollWidth} > ${scrollInfo.innerWidth}`
        ).toBe(false);
      }
    }

    // Assert zero uncaught JavaScript runtime exceptions occurred during rapid resizing
    expect(errors, `Uncaught page errors during resizing: ${errors.join('; ')}`).toEqual([]);
  });
});
