import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';

const cdpUrl = process.env.E2E_CDP_ENDPOINT;

export default {
  tests: 'e2e-tests/**/*.e2e.ts',
  targets: [
    {
      name: 'live-domain',
      engine: web({
        browser: 'chromium',
        viewport: null,
        ...(cdpUrl ? { connect: { cdpEndpoint: async () => cdpUrl } } : {}),
      }),
      app: {
        url: 'https://marketing.kienhieu.id.vn',
        environment: 'production',
      },
    },
  ],
  workers: 1,
  timeout: 180_000,
  actionTimeout: 30_000,
  assertionTimeout: 15_000,
  trace: 'on',
  video: 'on',
  credentials: {
    manager: {
      username: 'manager@gmail.com',
      password: () => process.env.E2E_MANAGER_PASSWORD ?? 'Manager@123',
    },
  },
} satisfies E2EConfig;
