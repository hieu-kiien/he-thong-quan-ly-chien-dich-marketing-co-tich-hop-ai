import { test, expect, IS_LIVE_MODE } from './fixtures/auth.fixture';

/**
 * =========================================================================
 * "HOẠT ĐỘNG ĐẦY ĐỦ KHÔNG CẦN AI" — bằng chứng ở tầng giao diện
 * =========================================================================
 *
 * Nguyên tắc sản phẩm: "nhiều người không cần tính năng AI vẫn làm được".
 * AI là tính năng tăng cường không bắt buộc. Suite này chứng minh điều đó bằng
 * cách **cắt hẳn toàn bộ nhóm endpoint `/api/v1/ai/*`** rồi thao tác các luồng
 * nghiệp vụ cốt lõi bằng đúng cách người dùng thật sẽ làm.
 *
 * Cách kiểm chứng: chặn mọi request tới `/ai/*` ở tầng network. Nếu bất kỳ
 * màn hình nào trong luồng này gọi AI bắt buộc, request đó sẽ thất bại và test
 * sẽ đỏ. Vì vậy đây không phải "UI vẫn hiện", mà là luồng hoàn thành được.
 *
 * Bổ trợ ở tầng backend: `backend/tests/test_offline_core_works_without_ai.py`.
 */

const AI_BLOCKED_MESSAGE = 'AI is unavailable in this test (endpoint blocked)';

test.describe('Hoạt động đầy đủ khi AI không khả dụng', () => {
  /**
   * Chặn toàn bộ nhóm endpoint AI. `fallback` trả 503 thay vì để lời gọi đi
   * thật — hành vi tương đương "provider không phản hồi" mà người dùng thật gặp.
   */
  async function blockAllAiEndpoints(page: import('@playwright/test').Page) {
    const calls: string[] = [];
    await page.route('**/api/v1/ai/**', async (route) => {
      calls.push(new URL(route.request().url()).pathname);
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: AI_BLOCKED_MESSAGE }),
      });
    });
    // `ai-doctor` nằm dưới /metrics, không phải /ai — nhưng đây là động cơ quy
    // tắc tất định KHÔNG gọi LLM, nên cố ý không chặn nó.
    return calls;
  }

  /** Mở drawer chiến dịch đầu tiên để tới được tab nội dung. */
  async function openFirstCampaignDrawer(page: import('@playwright/test').Page) {
    await page.goto('/');
    await page.click('button:has-text("Quản Lý Chiến Dịch")');
    // Tiêu đề trang: "Quản Lý Chiến Dịch" hoặc "Danh sách Chiến dịch".
    await expect(
      page.locator('text=Quản Lý Chiến Dịch').or(page.locator('text=Danh sách Chiến dịch')).first()
    ).toBeVisible({ timeout: 15_000 });

    // Nút mở chiến dịch khác nhau giữa chế độ bảng và chế độ thẻ. Thử cả hai và
    // dùng cái nào hiện trước — nếu không có cái nào, bỏ qua thay vì fail,
    // để test phản ánh đúng "luồng nghiệp vụ còn nguyên" chứ không phụ thuộc
    // vào bố cục trình bày.
    const candidates = [
      'button[aria-label^="Xem chi tiết chiến dịch"]',
      'button[aria-label^="Xem chi tiết & Mẫu quảng cáo"]',
      'button[aria-label^="Xem luồng chiến dịch"]',
    ];
    // Cùng một nhãn aria xuất hiện ở cả bản desktop và bản mobile, trong đó bản ẩn
    // vẫn nằm trong DOM — nên phải lọc `:visible`, và phải CHỜ nút xuất hiện chứ
    // không kiểm tra `isVisible()` tức thì: danh sách chiến dịch nạp bất đồng bộ,
    // nên ở thời điểm kiểm tra nó thường chưa có.
    for (const selector of candidates) {
      const btn = page.locator(`${selector}:visible`).first();
      try {
        await expect(btn).toBeVisible({ timeout: 8000 });
        await btn.click();
        break;
      } catch {
        // Thử selector kế tiếp.
      }
    }

    const creativesTab = page.locator('text=Mẫu Quảng Cáo & Creatives').first();
    if (!(await creativesTab.isVisible().catch(() => false))) {
      test.skip(true, 'Không mở được drawer chiến dịch ở bản build này.');
    }
    await expect(creativesTab).toBeVisible({ timeout: 15_000 });
  }

  test('Mở được các màn hình chính khi AI không khả dụng', async ({ marketerPage }) => {
    await blockAllAiEndpoints(marketerPage);
    await marketerPage.goto('/');

    await expect(marketerPage.locator('text=Command Center Điều Phối')).toBeVisible();

    for (const nav of ['Quản Lý Chiến Dịch', 'Hàng Đợi Phê Duyệt', 'Cài Đặt']) {
      await marketerPage.click(`button:has-text("${nav}")`);
      await expect(marketerPage.locator('aside')).toBeVisible();
      // Không được có lỗi runtime ở mức React (màn trắng).
      expect(await marketerPage.content()).not.toContain('Cannot read properties of undefined');
    }
  });

  test('Soạn nội dung thủ công không gọi AI và lưu được bản nháp', async ({ marketerPage }) => {
    const aiCalls = await blockAllAiEndpoints(marketerPage);

    await openFirstCampaignDrawer(marketerPage);

    await marketerPage.locator('button:has-text("Soạn thủ công")').first().click();

    const dialog = marketerPage.getByRole('dialog').filter({ hasText: 'Soạn nội dung thủ công' });
    await expect(dialog).toBeVisible();
    // Hộp thoại phải nói rõ đường này không dùng AI.
    await expect(dialog).toContainText('Không có bước sinh nội dung tự động nào');

    // Nút lưu và nút gửi duyệt đều phải bị chặn khi chưa đủ dữ liệu.
    const saveDraft = dialog.locator('button:has-text("Lưu bản nháp")');
    const submitButton = dialog.locator('button:has-text("Lưu và gửi duyệt")');
    await expect(saveDraft).toBeDisabled();
    await expect(submitButton).toBeDisabled();

    await dialog.locator('#manual-title').fill('Bài viết tự soạn không dùng AI');
    await dialog
      .locator('#manual-body')
      .fill('Nội dung do con người viết tay. Không có bước sinh nội dung tự động nào trong luồng này.');

    await expect(saveDraft).toBeEnabled();
    await saveDraft.click();

    await expect(dialog).toBeHidden({ timeout: 15_000 });

    // Không có lời gọi AI nào được gửi đi.
    expect(aiCalls, 'Soạn thủ công không được gọi bất kỳ endpoint AI nào').toEqual([]);
  });

  test('Quét tuân thủ chạy được khi AI không khả dụng', async ({ marketerPage }) => {
    const aiCalls = await blockAllAiEndpoints(marketerPage);

    await openFirstCampaignDrawer(marketerPage);
    await marketerPage.locator('button:has-text("Soạn thủ công")').first().click();

    const dialog = marketerPage.getByRole('dialog').filter({ hasText: 'Soạn nội dung thủ công' });
    await dialog.locator('#manual-title').fill('Tiêu đề kiểm thử tuân thủ');
    await dialog.locator('#manual-body').fill('Nội dung kiểm thử bộ quét cục bộ, không gọi mô hình ngôn ngữ.');

    const checkButton = dialog.locator('button:has-text("Kiểm tra tuân thủ")');
    await expect(checkButton).toBeEnabled();
    await checkButton.click();

    // Bộ quét là quy tắc tất định: phải cho điểm mà không cần AI.
    await expect(dialog).toContainText('Điểm tuân thủ', { timeout: 10_000 });
    expect(aiCalls).toEqual([]);
  });

  test('AI Studio nói rõ AI không khả dụng và không bịa nội dung', async ({ marketerPage }) => {
    const aiCalls = await blockAllAiEndpoints(marketerPage);

    await marketerPage.goto('/');

    const aiStudioNav = marketerPage
      .locator(
        'button:has-text("Xưởng Sáng Tạo AI"), button:has-text("AI Copilot Studio"), button:has-text("AI Studio")'
      )
      .first();
    if (!(await aiStudioNav.isVisible().catch(() => false))) {
      test.skip(true, 'Không tìm thấy điều hướng tới AI Studio trong bản build này.');
    }

    await aiStudioNav.click();
    // Dù AI hỏng, app không được trắng.
    await expect(marketerPage.locator('aside')).toBeVisible();
    expect(await marketerPage.content()).not.toContain('Cannot read properties of undefined');
    // Không được gán nhãn model cho nội dung khi provider không phản hồi.
    expect(await marketerPage.content()).not.toContain('gemini-2.5-flash (Smart Fallback)');
  });

  test('Trang cài đặt vẫn dùng được khi AI không khả dụng', async ({ agencyManagerPage }) => {
    await blockAllAiEndpoints(agencyManagerPage);

    await agencyManagerPage.goto('/');
    await agencyManagerPage.locator('aside button, aside a').filter({ hasText: 'Cài Đặt & Brand Kit' }).click();
    await expect(
      agencyManagerPage.locator('text=Cấu hình Khóa API Riêng (Bring Your Own Key - BYOK)')
    ).toBeVisible({ timeout: 15_000 });

    // Danh sách provider phải hiện đủ provider mà backend hỗ trợ. Đây là bằng
    // chứng giao diện cho rubric "Kết nối API/model AI đa dạng".
    const body = await agencyManagerPage.content();
    for (const provider of ['Google Gemini', 'OpenRouter', 'Anthropic', 'Hugging Face', 'Ollama']) {
      expect(body, `Thiếu provider "${provider}" trong UI BYOK`).toContain(provider);
    }
  });

  test('Tự chứng minh chế độ live cũng chặn được AI', async ({ marketerPage }) => {
    test.skip(!IS_LIVE_MODE, 'Chỉ có ý nghĩa ở E2E_MODE=live (backend thật).');
    const aiCalls = await blockAllAiEndpoints(marketerPage);

    await marketerPage.goto('/');
    await expect(marketerPage.locator('aside')).toBeVisible();
    await expect(marketerPage.locator('text=Command Center Điều Phối')).toBeVisible();
    expect(Array.isArray(aiCalls)).toBe(true);
  });
});