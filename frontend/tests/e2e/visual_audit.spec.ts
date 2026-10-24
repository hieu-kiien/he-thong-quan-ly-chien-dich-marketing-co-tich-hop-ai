import { test, expect } from '@playwright/test';
import { loginAsManager, takeScreenshot } from './helpers';

test.describe('Kiểm tra Giao diện, Responsive & Quy chuẩn Ngôn ngữ (Visual & Contract Audit)', () => {
  const pagesToAudit = [
    { name: 'dashboard', path: '/' },
    { name: 'campaigns', path: '/campaigns' },
    { name: 'campaign-detail', path: '/campaigns/1' },
    { name: 'contents', path: '/contents' },
    { name: 'reviews', path: '/reviews' },
    { name: 'calendar', path: '/calendar' },
    { name: 'settings', path: '/settings' },
    { name: 'assistant', path: '/assistant' },
  ];

  test('Chụp ảnh kiểm tra Layout ở 1280px và 768px cho tất cả các trang chính', async ({ page }) => {
    await loginAsManager(page);

    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    for (const p of pagesToAudit) {
      // 1. Kiểm tra 1280px (Desktop)
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(p.path);
      await page.waitForTimeout(400);
      await takeScreenshot(page, `${p.name}-1280px`);

      // 2. Kiểm tra 768px (Tablet / Responsive)
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(p.path);
      await page.waitForTimeout(400);
      await takeScreenshot(page, `${p.name}-768px`);

      // Kiểm tra không có thanh cuộn ngang ngoài ý muốn trên toàn trang
      const hasHorizontalOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });
      expect(hasHorizontalOverflow, `Trang ${p.name} không bị tràn ngang ở 768px`).toBe(false);

      // 3. Kiểm tra quy tắc chống "tính năng ảo" & buzzwords (CONTRACT §0)
      const pageText = await page.innerText('body');
      expect(pageText).not.toContain('Copilot');
      expect(pageText).not.toContain('Doctor');
      expect(pageText).not.toContain('Enterprise');
      expect(pageText).not.toContain('Closed-loop');

      // Đảm bảo không có NaN
      expect(pageText).not.toContain('NaN');
    }

    // Không có lỗi console crash runtime nghiêm trọng
    const severeErrors = consoleErrors.filter(
      (err) => !err.includes('favicon') && !err.includes('ResizeObserver') && !err.includes('401')
    );
    expect(severeErrors).toHaveLength(0);
  });
});
