import { test, expect } from './fixtures/auth.fixture';
import { setupMockApiRoutes, USERS, INITIAL_CAMPAIGNS } from './fixtures/mock-api';
import type { Page } from '@playwright/test';

/**
 * ============================================================================
 * PHÂN TRANG + HẠN MỨC — kiểm chứng bằng UI thật
 * ============================================================================
 *
 * Mục tiêu KHÔNG phải "API trả envelope" (đã có test backend cho phần đó) mà là
 * ba điều chỉ UI mới làm được:
 *
 * 1. **Điều khiển phân trang là thật**: bấm "Trang sau" phải ra danh sách KHÁC,
 *    đổi kích thước trang phải về trang 1, tổng phải khớp số server trả. Bộ điều
 *    khiển trang trí mà không đổi dữ liệu là lỗi nặng hơn không có bộ điều khiển.
 *
 * 2. **Trạng thái vô hiệu hóc / rỗng đúng**: nút "Trước" ở trang 1 phải tắt; màn
 *    hình không có bản ghi thì KHÔNG được có thanh phân trang.
 *
 * 3. **Trạng thái hết hạn mức nhìn thấy được**: khi server trả 429, người dùng
 *    phải thấy trần đã chạm, đã dùng bao nhiêu và hết hạn lúc nào.
 */

/**
 * Bộ chiến dịch đủ lớn để có nhiều trang. `INITIAL_CAMPAIGNS` chỉ có 3 bản ghi —
 * với `page_size=20` đó là đúng MỘT trang, nên mọi nút trang đều bị vô hiệu hóc và
 * test phân trang trở nên vô nghĩa. Dữ liệu phải lớn hơn trang thì phân trang mới
 * có ý nghĩa.
 */
const MANY_CAMPAIGNS = Array.from({ length: 25 }, (_, i) => ({
  ...INITIAL_CAMPAIGNS[i % INITIAL_CAMPAIGNS.length],
  id: 1000 + i,
  name: `Chiến dịch phân trang số ${String(i + 1).padStart(2, '0')}`,
  status: i % 3 === 0 ? 'ACTIVE' : i % 3 === 1 ? 'DRAFT' : 'PAUSED',
}));

/** Mở app với dữ liệu nhiều trang, không dùng fixture `*Page` (fixture dùng dữ liệu mặc định). */
async function openApp(page: Page, campaigns = MANY_CAMPAIGNS) {
  await setupMockApiRoutes(page, { userRole: 'MARKETER', customCampaigns: campaigns as never });
  await page.addInitScript(([u]) => {
    localStorage.setItem('access_token', 'token-marketer');
    localStorage.setItem('current_user', JSON.stringify(u));
    // workspace giả nhưng hợp lệ để thẻ hạn mức có nơi để đọc số liệu.
    localStorage.setItem('active_workspace_id', '1');
  }, [USERS.marketer as never]);
  await page.goto('/');
  await page.locator('button[aria-label="Quản Lý Chiến Dịch"]').first().click();
  await page.getByTestId('campaign-sort').waitFor({ state: 'visible', timeout: 30_000 });
}

async function firstRowText(page: Page): Promise<string> {
  const row = page.locator('table tbody tr').first();
  await row.waitFor({ state: 'visible', timeout: 30_000 });
  return ((await row.innerText()) || '').trim();
}

async function readTotal(page: Page): Promise<number> {
  const label = await page.getByTestId('pagination-total').innerText();
  return Number(label.match(/trên\s+(\d+)/)?.[1] ?? '-1');
}

// ---------------------------------------------------------------------------
// 1. ĐIỀU KHIỂN PHÂN TRANG THẬT
// ---------------------------------------------------------------------------
test.describe('Phân trang', () => {
  test('trang 1 vô hiệu hóa nút Trước và hiện tổng số bản ghi', async ({ page }) => {
    await openApp(page);
    await expect(page.getByTestId('pagination')).toBeVisible();

    // Trang đầu tiên không có trang trước.
    await expect(page.getByTestId('pagination-prev')).toBeDisabled();
    await expect(page.getByTestId('pagination-next')).toBeEnabled();

    // Tổng phải là số THẬT của tập đã lọc, không phải số dòng của trang.
    const label = await page.getByTestId('pagination-total').innerText();
    expect(label).toContain('chiến dịch');
    expect(await readTotal(page)).toBe(25);
    // "Hiển thị 1-20 trên 25" — số dòng của trang không được vượt tổng.
    expect(label).toMatch(/Hiển thị 1-20 trên 25/);
  });

  test('bấm Trang sau ra danh sách khác và bật nút Trước', async ({ page }) => {
    await openApp(page);
    const firstName = await firstRowText(page);

    await page.getByTestId('pagination-next').click();
    await expect(page.getByTestId('pagination-page-2')).toHaveAttribute('aria-current', 'page');
    await expect(page.getByTestId('pagination-prev')).toBeEnabled();

    // Phần cốt lõi: dữ liệu PHẢI khác. Bộ điều khiển trang trí sẽ bị bắt ở đây.
    expect(await firstRowText(page)).not.toBe(firstName);
    // Trang 2 chỉ còn 5 dòng (25 - 20) và nút "Sau" phải tắt.
    await expect(page.getByTestId('pagination-total')).toContainText('Hiển thị 21-25 trên 25');
    await expect(page.getByTestId('pagination-next')).toBeDisabled();
  });

  test('nút Trước quay lại đúng danh sách ban đầu', async ({ page }) => {
    await openApp(page);
    const firstName = await firstRowText(page);

    await page.getByTestId('pagination-next').click();
    await expect(page.getByTestId('pagination-page-2')).toHaveAttribute('aria-current', 'page');
    await page.getByTestId('pagination-prev').click();

    await expect(page.getByTestId('pagination-page-1')).toHaveAttribute('aria-current', 'page');
    expect(await firstRowText(page)).toBe(firstName);
  });

  test('đổi kích thước trang quay về trang 1', async ({ page }) => {
    await openApp(page);
    await page.getByTestId('pagination-next').click();
    await expect(page.getByTestId('pagination-page-2')).toHaveAttribute('aria-current', 'page');

    await page.getByTestId('pagination-page-size').selectOption('10');

    // Giữ nguyên trang 2 rồi đổi page_size sẽ ra một trang không tồn tại và danh
    // sách trống — đúng cái lỗi mà bộ chọn kích thước trang phải chặn.
    await expect(page.getByTestId('pagination-page-1')).toHaveAttribute('aria-current', 'page');
    await expect(page.getByTestId('pagination-prev')).toBeDisabled();
    await expect(page.getByTestId('pagination-total')).toContainText('Hiển thị 1-10 trên 25');
  });

  test('tìm kiếm lọc trước rồi mới phân trang — tổng theo kết quả lọc', async ({ page }) => {
    await openApp(page);
    expect(await readTotal(page)).toBe(25);

    // Lọc theo trạng thái: ACTIVE chiếm 1/3 danh sách seed.
    await page.locator('button[aria-label="Đang chạy"], button:has-text("Đang chạy")').first().click();
    await expect(page.getByTestId('pagination-total')).toContainText('trên 9');
    // 9 bản ghi vẫn nằm gọn trong một trang 20 -> không có trang sau.
    await expect(page.getByTestId('pagination-next')).toBeDisabled();
  });

  test('sắp xếp đổi thứ tự hiển thị', async ({ page }) => {
    await openApp(page);
    const firstAsc = await firstRowText(page);

    await page.getByTestId('campaign-sort').selectOption('name_asc');
    await page.waitForTimeout(600);
    const firstAscSorted = await firstRowText(page);

    await page.getByTestId('campaign-sort').selectOption('name_desc');
    await page.waitForTimeout(600);
    const firstDesc = await firstRowText(page);

    expect(firstAscSorted).not.toBe(firstDesc);
    // "Chiến dịch phân trang số 25" là bản ghi đầu khi sắp A→Z.
    expect(firstAscSorted).toContain('số 01');
    expect(firstDesc).toContain('số 25');
    expect(firstAsc).toBeTruthy();
  });

  test('màn hình không có bản ghi thì KHÔNG hiện thanh phân trang', async ({ page }) => {
    await openApp(page);
    await page
      .locator('input[aria-label="Tìm theo tên chiến dịch, sản phẩm, đối tượng"]')
      .fill('khong-co-chien-dich-nao-khop');

    await expect(page.getByText('Không tìm thấy chiến dịch phù hợp')).toBeVisible({ timeout: 30_000 });
    // Quy tắc: danh sách rỗng thì không có thanh "Trang 1/1" vô nghĩa.
    await expect(page.getByTestId('pagination')).toHaveCount(0);
  });

  test('bộ điều khiển phân trang kích hoạt được bằng bàn phím', async ({ page }) => {
    await openApp(page);
    const next = page.getByTestId('pagination-next');
    await expect(next).toBeEnabled();

    // `press` tự focus rồi gõ phím — kiểm chứng nút là điều khiển thật, bấm
    // được bằng Enter chứ không chỉ bằng chuột.
    await next.press('Enter');
    await expect(page.getByTestId('pagination-page-2')).toHaveAttribute('aria-current', 'page');
  });

  test('danh sách tác vụ cũng phân trang được', async ({ page }) => {
    await setupMockApiRoutes(page, { userRole: 'MARKETER' });
    await page.addInitScript(([u]) => {
      localStorage.setItem('access_token', 'token-marketer');
      localStorage.setItem('current_user', JSON.stringify(u));
    }, [USERS.marketer as never]);
    await page.goto('/');

    await page.locator('button[aria-label="Tác Vụ Của Tôi"]').first().click();
    const pagination = page.getByTestId('pagination').first();
    await expect(pagination).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('pagination-total').first()).toContainText('tác vụ');
    await expect(page.getByTestId('pagination-prev').first()).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// 2. HẠN MỨC: THẺ ĐẾM NGƯỢC + TRẠNG THÁI ĐÃ HẾT
// ---------------------------------------------------------------------------
test.describe('Hạn mức gói miễn phí', () => {
  test('hiện hạn mức kèm số đã dùng và đồng hồ đặt lại', async ({ page }) => {
    await openApp(page);
    await expect(page.getByTestId('quota-badge')).toBeVisible({ timeout: 30_000 });

    await expect(page.getByTestId('quota-row-ai_jobs_per_day')).toBeVisible();
    await expect(page.getByTestId('quota-row-campaigns')).toBeVisible();

    // Hạn mức AI job có cửa sổ trượt nên phải nói rõ đặt lại lúc nào.
    await expect(page.getByTestId('quota-reset-ai_jobs_per_day')).toContainText('Đặt lại');
    // Hạn mức tích luỹ thì KHÔNG tự đặt lại — UI phải nói đúng điều đó.
    await expect(page.getByTestId('quota-reset-campaigns')).toContainText('Không tự đặt lại');
  });

  test('khi hết hạn mức, thẻ lỗi nêu rõ trần / đã dùng / không tự đặt lại', async ({ page }) => {
    await openApp(page);

    // Buộc backend trả 429 với đúng thân lỗi mà `app/services/quota.py` sinh ra.
    await page.route('**/api/v1/campaigns', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        headers: { 'Retry-After': '1800' },
        body: JSON.stringify({
          detail: {
            error: 'quota_exceeded',
            limit_code: 'campaigns',
            message:
              'Bạn đã dùng hết hạn mức chiến dịch của gói miễn phí (25/25). Hạn mức này KHÔNG tự đặt lại — hãy xoá bản ghi cũ hoặc liên hệ quản trị viên để được nâng hạn mức.',
            used: 25,
            limit: 25,
            remaining: 0,
            requested: 1,
            scope: 'workspace',
            resets_at: null,
            would_be_used: 26,
          },
        }),
      });
    });

    await page.locator('button:has-text("Tạo Chiến Dịch Mới")').first().click();
    await page.fill('input[placeholder*="Nhập tên chiến dịch"]', 'Chiến dịch vượt hạn mức');
    await page.locator('button:has-text("Tiếp theo")').first().click();
    await page.locator('button:has-text("Tiếp theo")').first().click();
    await page.locator('button:has-text("Tiếp theo")').first().click();
    await page.locator('button:has-text("Hoàn tất & Khởi tạo Chiến dịch")').first().click();

    const card = page.getByTestId('quota-error');
    await expect(card).toBeVisible({ timeout: 30_000 });
    // Nói rõ vì sao bị chặn và còn bao nhiêu — không phải một 429 trần.
    await expect(card).toContainText('25/25');
    await expect(card).toContainText('không tự đặt lại');
    // Thẻ lỗi phải còn trên màn hình để người dùng đọc, không biến mất sau vài giây
    // như một toast.
    await expect(page.getByTestId('quota-error-banner')).toBeVisible();
    await expect(page.getByTestId('quota-error-banner')).toContainText('Thử lại');
  });
});