import { test, expect } from '@playwright/test';
import { IS_LIVE_MODE, LIVE_USERS } from './fixtures/auth.fixture';

/**
 * =========================================================================
 * PROBE: backend THAT co that su san sang khong? (chi chay o E2E_MODE=live)
 * =========================================================================
 * CI dung probe nay LAM DIEU KIEN cho quyet dinh "WCAG chay tren du lieu that
 * hay fallback ve du lieu gia". Neu dung mot `if: failure()` chung cho ca test,
 * thi mot loi WCAG that (vi du mot violation ton tai san trong app) se bi nham
 * nham la "backend khong len" va che mat loi that - dung thu che do ma bai
 * bao cao tin cuc dang gap pham.
 *
 * Voi `E2E_MODE=mock` probe nay bi SKIP (khong co backend de kiem tra).
 */
const BACKEND_ORIGIN = `http://127.0.0.1:${process.env.E2E_BACKEND_PORT || 8000}`;

const SKIP_REASON = 'Chi chay o E2E_MODE=live (E2E_MODE=mock khong co backend that de probe).';

test.describe('LIVE backend readiness probe', () => {
  test.skip(!IS_LIVE_MODE, SKIP_REASON);

  test('A. /health tra 200 va bao "healthy"', async ({ request }) => {
    test.setTimeout(30_000);
    const res = await request.get(`${BACKEND_ORIGIN}/health`);
    expect(res.status(), `GET ${BACKEND_ORIGIN}/health`).toBe(200);
    expect(await res.json()).toEqual({ status: 'healthy' });
  });

  test('B. Backend that cap JWT cho tai khoan seed (chuong minh CSDL da nap seed)', async ({ request }) => {
    test.setTimeout(30_000);
    const res = await request.post(`${BACKEND_ORIGIN}/api/v1/auth/login`, {
      data: {
        email: LIVE_USERS.manager.email,
        password: LIVE_USERS.manager.password,
      },
    });
    expect(res.status(), `POST /api/v1/auth/login (${LIVE_USERS.manager.email})`).toBe(200);

    const body = await res.json();
    expect(typeof body.access_token).toBe('string');
    // JWT co 3 phan tach bang dau cham - khong phai token gia cua storage state.
    expect(body.access_token.split('.')).toHaveLength(3);
    expect(body.user.email).toBe(LIVE_USERS.manager.email);
    expect(body.user.role).toBe('MANAGER');
  });
});
