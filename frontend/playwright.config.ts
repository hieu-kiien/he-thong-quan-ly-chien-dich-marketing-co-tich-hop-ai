import { defineConfig, devices } from '@playwright/test';

/**
 * Cấu hình kiểm thử E2E Playwright cho MarketFlow v2.
 * Giả định các dịch vụ nền đã chạy trước (hoặc chạy qua npm run test:e2e):
 * - Backend: http://127.0.0.1:8000
 * - Fake Runner: http://127.0.0.1:8100
 * - Frontend Vite: http://localhost:5173
 */
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'off',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
      },
    },
  ],
});
