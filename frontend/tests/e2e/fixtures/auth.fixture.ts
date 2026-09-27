import { test as base, Page, BrowserContext } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { setupMockApiRoutes, USERS, MockUser } from './mock-api';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const AUTH_DIR = path.resolve(__dirname, '../.auth');

export const STORAGE_STATES = {
  marketer: path.join(AUTH_DIR, 'marketer.json'),
  manager: path.join(AUTH_DIR, 'manager.json'),
  approver: path.join(AUTH_DIR, 'client-approver.json'),
  agencyManager: path.join(AUTH_DIR, 'agency-manager.json'),
};

type AuthFixtures = {
  marketerPage: Page;
  managerPage: Page;
  approverPage: Page;
  agencyManagerPage: Page;
  loginAs: (page: Page, role: keyof typeof USERS) => Promise<void>;
};

export const test = base.extend<AuthFixtures>({
  loginAs: async ({}, use) => {
    await use(async (page: Page, role: keyof typeof USERS) => {
      const user = USERS[role];
      await page.goto('/');
      // If already logged in, log out
      const logoutBtn = page.locator('button[title="Đăng xuất"]');
      if (await logoutBtn.isVisible().catch(() => false)) {
        await logoutBtn.click();
      }

      await page.fill('input[type="email"]', user.email);
      await page.fill('input[type="password"]', `${role.charAt(0).toUpperCase() + role.slice(1)}@123`);
      await page.click('button[type="submit"]');
      // Wait for navigation into app
      await page.waitForSelector('text=MarketFlow AI', { timeout: 10000 });
    });
  },

  marketerPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: STORAGE_STATES.marketer,
      locale: 'vi-VN',
      timezoneId: 'Asia/Ho_Chi_Minh',
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const page = await context.newPage();
    await setupMockApiRoutes(page, { userRole: 'MARKETER' });
    await page.goto('/');
    try {
      await use(page);
    } finally {
      await context.close();
    }
  },

  managerPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: STORAGE_STATES.manager,
      locale: 'vi-VN',
      timezoneId: 'Asia/Ho_Chi_Minh',
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const page = await context.newPage();
    await setupMockApiRoutes(page, { userRole: 'MANAGER' });
    await page.goto('/');
    try {
      await use(page);
    } finally {
      await context.close();
    }
  },

  approverPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: STORAGE_STATES.approver,
      locale: 'vi-VN',
      timezoneId: 'Asia/Ho_Chi_Minh',
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const page = await context.newPage();
    await setupMockApiRoutes(page, { userRole: 'CLIENT_APPROVER' });
    await page.goto('/');
    try {
      await use(page);
    } finally {
      await context.close();
    }
  },

  agencyManagerPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: STORAGE_STATES.agencyManager,
      locale: 'vi-VN',
      timezoneId: 'Asia/Ho_Chi_Minh',
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const page = await context.newPage();
    await setupMockApiRoutes(page, { userRole: 'AGENCY_MANAGER' });
    await page.goto('/');
    try {
      await use(page);
    } finally {
      await context.close();
    }
  },
});

export { expect } from '@playwright/test';
