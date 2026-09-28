import { test as base, Page, Browser, BrowserContext } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { setupMockApiRoutes, USERS, MockUser } from './mock-api';

/**
 * =========================================================================
 * HAI CHE DO CHAY E2E
 * =========================================================================
 * `E2E_MODE=mock` (mac dinh)
 *   - KHONG co backend. `setupMockApiRoutes` intercept moi request tien do
 *     `/api/v1` va tra du lieu gia tu `mock-api.ts`.
 *   - Storage state `.auth/*.json` giu `access_token` gia ("token-manager-1"...).
 *   - Uu u: nhanh, khong can Python/DB/mang, bat loi UI regression o nhanh.
 *   - Nhuoc diem: KHONG chung minh gi ve backend that.
 *
 * `E2E_MODE=live`
 *   - Backend that (uvicorn) + SQLite that, xem `frontend/scripts/start-e2e.mjs`.
 *   - KHONG intercept API. Moi lan tao context deu dang nhap that qua form
 *     `LoginPage` bang tai khoan seed (`backend/seed/seed_data.py`), nen token
 *     la JWT do backend cap - khong phai chuoi gia.
 *   - Dung lai cho `tests/e2e/live-backend.spec.ts`: day moi la bang chung
 *     he thong thuc su chay tren du lieu that.
 *
 * Cac fixture `*Page` duoc giu nguyen ten de khong phai sua file test hien co.
 * Chúng tu chon duong `mock` hay `live` theo `E2E_MODE` mot cach minh bach.
 */
export const E2E_MODE = (process.env.E2E_MODE || 'mock').toLowerCase();
export const IS_LIVE_MODE = E2E_MODE === 'live';

/**
 * Tai khoan THAT do `backend/seed/seed_data.py` tao san.
 * Chi co 3 tai khoan nay duoc dam bao ton tai o moi moi truong E2E.
 */
export const LIVE_USERS = {
  manager: { email: 'manager@gmail.com', password: 'Manager@123', fullName: 'Nguyễn Văn Quản Lý' },
  marketer: { email: 'marketer@gmail.com', password: 'Marketer@123', fullName: 'Trần Thị Marketing' },
  approver: { email: 'approver@gmail.com', password: 'Approver@123', fullName: 'Đại Diện Khách Hàng (Approver)' },
} as const;

export type LiveRole = keyof typeof LIVE_USERS;

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
  loginAsLive: (page: Page, role: LiveRole) => Promise<void>;
};

/**
 * Dang nhap THAT qua form LoginPage.
 *
 * Khong dung `page.request.post('/api/v1/auth/login')` roi nhung storage state:
 * App.tsx/AuthContext khoi tao bang cach goi GET /auth/me de xac minh phien, nen
 * phai di qua dung luong UI cua nguoi dung moi chung minh phien la that.
 */
export async function performLiveLogin(page: Page, role: LiveRole): Promise<void> {
  const user = LIVE_USERS[role];
  if (!user) {
    throw new Error(
      `E2E_MODE=live khong ho tro role "${role}". ` +
        `Chi co: ${Object.keys(LIVE_USERS).join(', ')} (nhung tai khoan backend/seed/seed_data.py tao san).`
    );
  }

  await page.goto('/');
  await page.locator('#login-email').waitFor({ state: 'visible', timeout: 20_000 });
  await page.locator('#login-email').fill(user.email);
  await page.locator('#login-password').fill(user.password);
  await page.locator('button[type="submit"]').click();

  // Thanh dieu huong chi render sau khi `isAuthenticated` = true, tuc la sau khi
  // POST /auth/login thanh cong.
  await page.locator('aside').getByRole('button', { name: 'Bảng Điều Khiển' }).waitFor({
    state: 'visible',
    timeout: 20_000,
  });

  const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
  if (!token) {
    throw new Error(`Dang nhap that that bai cho ${user.email}: khong co access_token trong localStorage.`);
  }
}

type RoleSetup = {
  /** Key trong `USERS` cua mock-api.ts (dung cho storage state gia). */
  mockKey: keyof typeof USERS;
  /** Vai tro backend khi chay that. */
  liveRole?: LiveRole;
  /** userRole truyen cho `setupMockApiRoutes`. */
  mockUserRole?: 'MARKETER' | 'MANAGER' | 'CLIENT_APPROVER' | 'AGENCY_MANAGER';
};

async function createRolePageWithCleanup(
  browser: Browser,
  setup: RoleSetup,
  storageStateKey: keyof typeof STORAGE_STATES
): Promise<{ context: BrowserContext; page: Page }> {
  const baseOptions = {
    locale: 'vi-VN',
    timezoneId: 'Asia/Ho_Chi_Minh',
    permissions: ['clipboard-read', 'clipboard-write'] as ('clipboard-read' | 'clipboard-write')[],
  };

  if (IS_LIVE_MODE) {
    if (!setup.liveRole) {
      throw new Error(
        `E2E_MODE=live: fixture nay khong co tai khoan backend that (${setup.mockKey}). ` +
          `Hay chay fixture nay o E2E_MODE=mock, hoac them tai khoan vao seed_data.py.`
      );
    }
    const context = await browser.newContext(baseOptions);
    const page = await context.newPage();
    // KHONG goi setupMockApiRoutes: moi request deu ra backend that.
    await performLiveLogin(page, setup.liveRole);
    return { context, page };
  }

  const context = await browser.newContext({ ...baseOptions, storageState: STORAGE_STATES[storageStateKey] });
  const page = await context.newPage();
  await setupMockApiRoutes(page, { userRole: setup.mockUserRole });
  await page.goto('/');
  return { context, page };
}

/**
 * Wrapper bao quanh `use()` de luon `context.close()` du test fail hay pass.
 */
async function withRolePage<T>(
  browser: Browser,
  setup: RoleSetup,
  storageStateKey: keyof typeof STORAGE_STATES,
  use: (page: Page) => Promise<T>
): Promise<T> {
  const { context, page } = await createRolePageWithCleanup(browser, setup, storageStateKey);
  try {
    return await use(page);
  } finally {
    await context.close();
  }
}

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

  loginAsLive: async ({}, use) => {
    await use(async (page: Page, role: LiveRole) => {
      await performLiveLogin(page, role);
    });
  },

  marketerPage: async ({ browser }, use) => {
    await withRolePage(
      browser,
      { mockKey: 'marketer', liveRole: 'marketer', mockUserRole: 'MARKETER' },
      'marketer',
      use
    );
  },

  managerPage: async ({ browser }, use) => {
    await withRolePage(
      browser,
      { mockKey: 'manager', liveRole: 'manager', mockUserRole: 'MANAGER' },
      'manager',
      use
    );
  },

  approverPage: async ({ browser }, use) => {
    await withRolePage(
      browser,
      { mockKey: 'approver', liveRole: 'approver', mockUserRole: 'CLIENT_APPROVER' },
      'approver',
      use
    );
  },

  agencyManagerPage: async ({ browser }, use) => {
    await withRolePage(
      browser,
      { mockKey: 'agency_mgr', mockUserRole: 'AGENCY_MANAGER' },
      'agencyManager',
      use
    );
  },
});

export { expect } from '@playwright/test';
export type { MockUser };
