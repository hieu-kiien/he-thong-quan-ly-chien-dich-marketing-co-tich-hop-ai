import { test, expect, BrowserContext, Page } from '@playwright/test';
import { IS_LIVE_MODE, LIVE_USERS, performLiveLogin } from './fixtures/auth.fixture';

/**
 * =========================================================================
 * E2E THAT - CHAY TREN BACKEND THAT (E2E_MODE=live)
 * =========================================================================
 * Day la mau chay "trong suot" (non-opaque-box) ma README cong bo:
 *   1. Backend FastAPI that (uvicorn) + SQLite that, khong co `route.fulfill()`
 *      nao canh duong tien do `/api/v1`.
 *   2. Frontend duoc BUILD LAI voi `VITE_API_URL` tro toi backend that
 *      (xem `frontend/scripts/start-e2e.mjs`).
 *   3. Dang nhap that qua form bang tai khoan seed `manager@gmail.com` /
 *      `marketer@gmail.com`, nen token la JWT do backend cap.
 *   4. Moi thao tac deu doc/ghi qua API that nen test chi PASS khi ca he
 *      thong that su song.
 *
 * VOI `E2E_MODE=mock`, toan bo file nay bi SKIP. Ly do: khong co backend that
 * thi khong the chung minh gi. Chay no tren du lieu gia chi tao cam giac an
 * toan - dung la thu che do ma bai test hien co dang gap pham.
 *
 * RANG BUOC THAT (khong phai loi cua test):
 *   Backend yeu cau MARKETER phai la `owner` hoac `CampaignMember` cua chi danhich
 *   moi duoc tao noi dung (xem `app/api/v1/contents.py` ->
 *   `check_campaign_access_for_content`). Vi vay trong test 3, Marketer tao chi
 *   danhich rieng de so huu no roi sinh noi dung tren chinh chi danhich do.
 *   Manager van duyet duoc vi MANAGER la thanh vien cua Workspace 1.
 *
 * DU LIEU UNIQUE: moi lan chay sinh mot `RUN_STAMP` moi, nen ten chi danhich /
 *   tieu de noi dung khong bao gio trung nhau -> chay lai nhieu lan van an.
 *
 * TUYEN CHON ASSERTION: file nay khong phu thuoc toast (tu tat sau 4 giay).
 *   Moi khong doan deu kiem tra DOM/du lieu lai tu API that, nen test khong
 *   phụ thuoc thoi gian hien thi cua thong bao.
 */

const SKIP_REASON =
  'Chi chay o E2E_MODE=live. O E2E_MODE=mock khong co backend that, ' +
  'test nay se chi kiem tra UI tren du lieu gia (khong chung minh gi ve he thong).';

// Cac test sau phai chay dung thu tu va chia se trang thai
// (chi danhich -> noi dung -> duyet -> logout).
test.describe.configure({ mode: 'serial' });

const RUN_STAMP = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();
const MANAGER_CAMPAIGN = `E2E-LIVE Manager ${RUN_STAMP}`;
const MARKETER_CAMPAIGN = `E2E-LIVE Marketer ${RUN_STAMP}`;
const CONTENT_TITLE = `E2E-LIVE Bai Viet ${RUN_STAMP}`;

let managerContext: BrowserContext;
let managerPage: Page;
let marketerContext: BrowserContext;
let marketerPage: Page;

const contextOptions = {
  locale: 'vi-VN',
  timezoneId: 'Asia/Ho_Chi_Minh',
  viewport: { width: 1280, height: 720 },
};

/** O dong cua bang "Quan tri Chien dich" chua ten chien dich `name`. */
function campaignCell(page: Page, name: string) {
  return page.locator('td', { hasText: name });
}

/** Doc so luong bai "Cho phe duyet" tu badge cua tab trong Review Queue. */
async function readPendingCount(page: Page): Promise<number> {
  const raw = await page
    .getByRole('button', { name: /Chờ phê duyệt/ })
    .locator('span')
    .last()
    .innerText();
  return Number(raw.trim());
}

/** Tao 1 chi danhich qua wizard 4 buoc cua trang "Quan Ly Chien Dich". */
async function createCampaignViaUi(page: Page, name: string): Promise<void> {
  await page.getByTestId('sidebar-tab-campaigns').click();
  await expect(page.getByRole('heading', { name: /Quản trị Chiến dịch Tiếp thị/ })).toBeVisible();

  await page.getByRole('button', { name: 'Tạo Chiến Dịch Mới' }).click();
  await expect(page.locator('#campaign-wizard-title')).toBeVisible();

  await page.locator('#wizard-campaign-name').fill(name);

  // Wizard 4 buoc: Buoc 1 (Ten) -> 2 (Kenh & Doi tuong) -> 3 (Sinh Mau QC) -> 4 (Xac nhan)
  for (let step = 0; step < 3; step += 1) {
    await page.getByRole('button', { name: 'Tiếp theo' }).click();
  }
  await page.getByRole('button', { name: 'Hoàn tất & Khởi tạo Chiến dịch' }).click();

  // Modal dong lai => POST /campaigns da thanh cong (rollback se giu modal mo).
  await expect(page.locator('#campaign-wizard-title')).toBeHidden({ timeout: 30_000 });
  // Bang duoc tai lai tu GET /campaigns nen hang moi phai xuat hien ngay.
  await expect(campaignCell(page, name)).toHaveCount(1, { timeout: 30_000 });
}

test.describe('LIVE E2E: quy trinh nghiep vu tren backend that', () => {
  test.skip(!IS_LIVE_MODE, SKIP_REASON);

  test.beforeAll(async ({ browser }) => {
    managerContext = await browser.newContext(contextOptions);
    managerPage = await managerContext.newPage();

    marketerContext = await browser.newContext(contextOptions);
    marketerPage = await marketerContext.newPage();
  });

  test.afterAll(async () => {
    await managerContext?.close();
    await marketerContext?.close();
  });

  test('1. Manager dang nhap THAT (manager@gmail.com) va thay Dashboard', async () => {
    test.setTimeout(90_000);

    // Chua dang nhap: phai thay form LoginPage that.
    await managerPage.goto('/');
    await expect(managerPage.locator('#login-email')).toBeVisible();
    await expect(managerPage.getByRole('heading', { name: 'MarketFlow AI' })).toBeVisible();

    await performLiveLogin(managerPage, 'manager');

    // Khong con form dang nhap => da vao trong app.
    await expect(managerPage.locator('#login-email')).toHaveCount(0);

    // Dashboard la tab mac dinh, so lieu do tu GET /analytics/dashboard that.
    await expect(managerPage.getByRole('heading', { name: 'Command Center Điều Phối' })).toBeVisible();
    await expect(managerPage.getByText(LIVE_USERS.manager.email).first()).toBeVisible();
    await expect(managerPage.getByText('Quản lý (Manager)')).toBeVisible();

    // Backend that cap token JWT, khong phai token gia cua file storage state.
    const token = await managerPage.evaluate(() => window.localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
    expect(token).not.toBe('token-manager-1');
    expect(String(token).split('.')).toHaveLength(3);

    // Danh sach chien dich doc tu GET /campaigns that (khong phai mock-api.ts).
    await managerPage.getByTestId('sidebar-tab-campaigns').click();
    await expect(managerPage.getByRole('heading', { name: /Quản trị Chiến dịch Tiếp thị/ })).toBeVisible();
    // Ten chien dich co stamp la duy nhat theo tung lan chay => chua ton tai.
    await expect(campaignCell(managerPage, MANAGER_CAMPAIGN)).toHaveCount(0);
  });

  test('2. Manager tao chi danhich moi qua UI - xuat hien sau khi reload', async () => {
    test.setTimeout(120_000);

    await createCampaignViaUi(managerPage, MANAGER_CAMPAIGN);

    // Reload lau thu du lieu thay dung state React => chung minh backend da ghi
    // xuong CSDL that (khong phai state tam trong bo nho).
    await managerPage.reload();
    await managerPage.getByTestId('sidebar-tab-campaigns').click();

    const cell = campaignCell(managerPage, MANAGER_CAMPAIGN);
    await expect(cell).toHaveCount(1, { timeout: 30_000 });
    await expect(cell).toBeVisible();

    // Tim theo ten phai ra duy nhat 1 dong -> khong dung du lieu lan chay truoc.
    await managerPage
      .getByPlaceholder('Tìm theo tên chiến dịch, sản phẩm, đối tượng...')
      .fill(MANAGER_CAMPAIGN);
    await expect(campaignCell(managerPage, MANAGER_CAMPAIGN)).toHaveCount(1);
  });

  test('3. Marketer tao noi dung, gui duyet - noi dung xuat hien o Review Queue', async () => {
    test.setTimeout(180_000);

    // Context rieng cho Marketer: dang nhap THAT qua form (token JWT tu backend).
    await performLiveLogin(marketerPage, 'marketer');
    await expect(marketerPage.getByText('Marketer').first()).toBeVisible();

    // Marketer can so huu chi danhich de duoc tao noi dung (xem ghi chu dau file).
    await createCampaignViaUi(marketerPage, MARKETER_CAMPAIGN);

    // So bai IN_REVIEW truoc khi tao, de chung minh review queue THAT SU TANG.
    await marketerPage.getByRole('button', { name: /Hàng Đợi Phê Duyệt/ }).first().click();
    await expect(
      marketerPage.getByRole('heading', { name: 'Hàng đợi Phê Duyệt Nội Dung' })
    ).toBeVisible();
    const pendingBefore = await readPendingCount(marketerPage);

    // --- Tao noi dung qua AI Studio: POST /ai/draft -> POST /contents -> POST /contents/{id}/submit
    await marketerPage.getByTestId('sidebar-tab-ai_studio').click();
    await marketerPage.getByRole('button', { name: /Đơn kênh \(AIDA\/PAS\)/ }).click();

    const campaignSelect = marketerPage.locator('#ai-studio-campaign-select');
    await expect(campaignSelect).toBeVisible();
    const option = campaignSelect.locator('option').filter({ hasText: MARKETER_CAMPAIGN });
    await expect(option).toHaveCount(1);
    const optionValue = await option.first().getAttribute('value');
    expect(optionValue).toBeTruthy();
    await campaignSelect.selectOption(String(optionValue));

    await marketerPage.getByRole('button', { name: /Viết Ngay Bản Nháp Hoàn Chỉnh/ }).click();
    await expect(marketerPage.getByText('Bản Nháp AI Hoàn Chỉnh')).toBeVisible({ timeout: 90_000 });

    await marketerPage
      .getByRole('button', { name: 'Lưu vào Chiến dịch & Gửi Sếp duyệt ngay (HITL)' })
      .click();
    await expect(
      marketerPage.getByText(
        /Đã lưu bài viết vào Chiến dịch & Đưa vào Hàng đợi duyệt thành công \(IN_REVIEW\)!/
      )
    ).toBeVisible({ timeout: 60_000 });

    // --- Bai viet da vao Review Queue that ---
    await marketerPage.getByRole('button', { name: /Hàng Đợi Phê Duyệt/ }).first().click();
    await expect
      .poll(() => readPendingCount(marketerPage), { timeout: 30_000 })
      .toBe(pendingBefore + 1);

    // Bai viet vua tao co id lon nhat, API sort `id DESC` => no o dau danh sach.
    // Tieu do AI co the trung voi du lieu cac lan chay truoc, nen tao mot tieu de
    // UNIQUE qua modal "Chinh sua noi dung bai viet" truoc khi kiem chung.
    // "The tom tat" hien thi tieu do dang text thuan (Social Preview khong dua
    // tieu do vao DOM phuc vu anh chup), nem chon de assertion on dinh.
    await marketerPage.getByRole('button', { name: 'Thẻ tóm tắt' }).click();
    const newestCard = marketerPage.locator('.review-item-card').first();
    await expect(newestCard).toContainText('CHỜ DUYỆT (IN_REVIEW)');

    await newestCard.getByRole('button', { name: 'Sửa' }).click();
    const editModal = marketerPage.locator('[role="dialog"]').filter({
      hasText: 'Chỉnh sửa nội dung bài viết',
    });
    await expect(editModal).toBeVisible();
    await editModal.locator('input[type="text"]').first().fill(CONTENT_TITLE);
    await editModal.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect(editModal).toBeHidden({ timeout: 30_000 });

    const uniqueCard = marketerPage.locator('.review-item-card').filter({ hasText: CONTENT_TITLE });
    await expect(uniqueCard).toHaveCount(1, { timeout: 30_000 });
    await expect(uniqueCard).toContainText('CHỜ DUYỆT (IN_REVIEW)');
  });

  test('4. Manager duyet bai do - trang thai chuyen APPROVED', async () => {
    test.setTimeout(120_000);

    await managerPage.getByRole('button', { name: /Hàng Đợi Phê Duyệt/ }).first().click();
    await expect(
      managerPage.getByRole('heading', { name: 'Hàng đợi Phê Duyệt Nội Dung' })
    ).toBeVisible();
    await managerPage.getByRole('button', { name: 'Thẻ tóm tắt' }).click();

    // Manager la thanh vien Workspace 1 nen thay noi dung cua Marketer trong cung tenant.
    const card = managerPage.locator('.review-item-card').filter({ hasText: CONTENT_TITLE });
    await expect(card).toHaveCount(1, { timeout: 30_000 });

    await card.getByRole('button', { name: 'Phê duyệt (Approve)' }).click();

    // Roi khoi "Cho phe duyet" => POST /contents/{id}/approve da thanh cong.
    await expect(
      managerPage.locator('.review-item-card').filter({ hasText: CONTENT_TITLE })
    ).toHaveCount(0, { timeout: 30_000 });

    // Trang thai APPROVED da duoc ghi xuong CSDL that (tab "Lich su duyet bai").
    await managerPage.getByRole('button', { name: /Lịch sử duyệt bài/ }).click();
    const historyRow = managerPage.locator('tr').filter({ hasText: CONTENT_TITLE });
    await expect(historyRow).toHaveCount(1, { timeout: 30_000 });
    await expect(historyRow).toContainText('✓ ĐÃ PHÊ DUYỆT');
  });

  test('5. Logout - truy cap lai trang bi chan', async () => {
    test.setTimeout(60_000);

    // `exact: true` de khong nham voi nut "Đăng xuất tài khoản" cua Navbar.
    await managerPage.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
    await expect(managerPage.locator('#login-email')).toBeVisible({ timeout: 30_000 });

    // Token va user da bi xoa khoi localStorage.
    expect(await managerPage.evaluate(() => window.localStorage.getItem('access_token'))).toBeNull();
    expect(await managerPage.evaluate(() => window.localStorage.getItem('current_user'))).toBeNull();

    // Vao lai trang: van bi chan o trang dang nhap, khong loi ra app shell da dang nhap.
    await managerPage.goto('/');
    await expect(managerPage.locator('#login-email')).toBeVisible();
    await expect(managerPage.getByTestId('sidebar-tab-campaigns')).toHaveCount(0);
  });
});
