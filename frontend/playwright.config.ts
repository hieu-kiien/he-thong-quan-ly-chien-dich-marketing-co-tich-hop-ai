import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for MarketFlow AI frontend
 * Standardized on Chromium default with Linux CI/CD compatibility
 *
 * ------------------------------------------------------------------
 * HAI CHE DO CHAY (E2E_MODE)
 * ------------------------------------------------------------------
 * - `E2E_MODE=mock` (mac dinh): frontend preview tinh, KHONG co backend.
 *   `tests/e2e/fixtures/mock-api.ts` intercept `**\/api\/\/v1\/**` va tra du
 *   lieu gia. Nhanh, on dinh, chay offline. Dung de bat loi UI regression.
 * - `E2E_MODE=live`: `scripts/start-e2e.mjs` khoi dong uvicorn that, BUILD LAI
 *   frontend voi `VITE_API_URL` tro toi backend that, roi preview. Fixture
 *   KHONG intercept API, dang nhap that qua form, va du lieu la du lieu that
 *   trong SQLite. Day moi la bang chung rang he thong thuc su chay.
 *
 * `webServer.command` tro ve `scripts/start-e2e.mjs` vi Playwright chi ho tro
 * MOT `webServer`, trong khi bo E2E can ca backend + frontend cung luc.
 * Script tu quyet dinh nen co bat backend hay khong theo `E2E_MODE`.
 */
const E2E_MODE = (process.env.E2E_MODE || 'mock').toLowerCase();
const IS_LIVE = E2E_MODE === 'live';

// Live mode phai build + khoi dong uvicorn + doi database truoc khi test bat dau,
// nen budget thoi gian cho webServer lon hon nhieu lan so voi mock mode.
const WEBSERVER_TIMEOUT_MS = Number(
  process.env.E2E_WEBSERVER_TIMEOUT_MS || (IS_LIVE ? 300_000 : 60_000)
);

if (process.env.E2E_LOG_MODE !== '0') {
  // eslint-disable-next-line no-console
  console.log(
    `[playwright] E2E_MODE=${E2E_MODE} (${IS_LIVE ? 'du lieu that, backend that' : 'du lieu gia, khong backend'})` +
      ` | webServer timeout=${WEBSERVER_TIMEOUT_MS}ms | baseURL=http://127.0.0.1:4173`
  );
}

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  expect: {
    timeout: 7000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    headless: true,
    viewport: { width: 1280, height: 720 },
    locale: 'vi-VN',
    timezoneId: 'Asia/Ho_Chi_Minh',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
        // Standard Chromium binary on Linux CI; msedge fallback on local Windows if no override
        ...(process.env.CI
          ? {}
          : process.env.PLAYWRIGHT_CHANNEL
          ? { channel: process.env.PLAYWRIGHT_CHANNEL }
          : { channel: 'msedge' }),
      },
    },
  ],
  webServer: {
    command: 'node scripts/start-e2e.mjs',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: WEBSERVER_TIMEOUT_MS,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
