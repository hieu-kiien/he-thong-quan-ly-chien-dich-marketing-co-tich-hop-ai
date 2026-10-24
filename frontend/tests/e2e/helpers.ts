import { Page, expect } from '@playwright/test';
import * as path from 'path';

export async function loginAsManager(page: Page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'manager@marketflow.vn');
  await page.fill('input[type="password"]', 'Manager@123');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/(dashboard)?$/, { timeout: 10000 });
}

export async function loginAsMarketer(page: Page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'marketer@marketflow.vn');
  await page.fill('input[type="password"]', 'Marketer@123');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/(dashboard)?$/, { timeout: 10000 });
}

export async function takeScreenshot(page: Page, name: string) {
  const screenshotsDir = path.resolve('tests/e2e/screenshots');
  await page.screenshot({ path: path.join(screenshotsDir, `${name}.png`), fullPage: true });
}
