import { test, expect } from './fixtures/auth.fixture';

test.describe('Adversarial Frontend Debounce & Idempotency Probes', () => {

  // --- PROBE 1: ReviewQueue Approve Button Rapid Double-Click ---
  test('Probe 1: Rapid double-click on Approve button in ReviewQueue disables during in-flight, preventing duplicate HTTP requests and preventing duplicate 400 error toasts', async ({ managerPage }) => {
    // 1. Navigate to Review Queue
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng đợi Phê duyệt Nội dung')).toBeVisible();

    // 2. Intercept approve endpoint with 1200ms in-flight latency and duplicate detector
    let approveCallCount = 0;
    let duplicateErrorTriggered = false;

    await managerPage.route('**/api/v1/contents/*/approve', async (route) => {
      approveCallCount++;
      if (approveCallCount > 1) {
        duplicateErrorTriggered = true;
        // Replicate strict backend state-machine check: if content is already approved, return 400 Bad Request
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Chỉ có thể phê duyệt nội dung đang ở trạng thái chờ duyệt (IN_REVIEW)' }),
        });
      }
      // Simulate network latency so button remains in in-flight state
      await new Promise((resolve) => setTimeout(resolve, 1200));
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          campaign_id: 1,
          channel_id: 1,
          title: 'Đột phá sự nghiệp cùng Kỹ sư AI 2026 tại ICTU!',
          status: 'APPROVED',
          updated_at: new Date().toISOString(),
        }),
      });
    });

    // 3. Locate the Approve button
    const approveBtn = managerPage.locator('button:has-text("Phê duyệt (Approve)")').first();
    await expect(approveBtn).toBeVisible();
    await expect(approveBtn).toBeEnabled();

    // 4. Adversarial Action: Rapid double-click on Approve button
    await approveBtn.click({ noWaitAfter: true });
    
    // Verify immediate in-flight visual state & button disabling (text changes to "Đang duyệt...")
    const inFlightBtn = managerPage.locator('button:has-text("Đang duyệt...")').first();
    await expect(inFlightBtn).toBeVisible({ timeout: 2000 });
    await expect(inFlightBtn).toBeDisabled();

    // Second click attempted during in-flight window (with force: true to attempt bypassing DOM disabled)
    await inFlightBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 5. Wait for request to settle
    await expect(managerPage.locator('text=Đã phê duyệt bài viết thành công (APPROVED)!').first()).toBeVisible({ timeout: 7000 });

    // 6. Empirical Invariant Assertions:
    // Exactly ONE HTTP request must be sent
    expect(approveCallCount).toBe(1);
    expect(duplicateErrorTriggered).toBe(false);

    // Verify NO duplicate 400 error toast appears
    const errorToast = managerPage.locator('text=Lỗi khi duyệt bài');
    await expect(errorToast).not.toBeVisible();

    const stateMachineToast = managerPage.locator('text=Chỉ có thể phê duyệt nội dung đang ở trạng thái chờ duyệt');
    await expect(stateMachineToast).not.toBeVisible();
  });

  // --- PROBE 2: ReviewQueue Reject Button Rapid Double-Click ---
  test('Probe 2: Rapid double-click on Confirm Reject button in ReviewQueue disables during in-flight, preventing duplicate HTTP requests and preventing duplicate 400 error toasts', async ({ managerPage }) => {
    // 1. Navigate to Review Queue
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng đợi Phê duyệt Nội dung')).toBeVisible();

    // 2. Open Reject Modal
    const rejectBtn = managerPage.locator('button:has-text("Từ chối (Reject)")').first();
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();

    // 3. Verify modal opened and pick a reason
    await expect(managerPage.locator('text=Từ chối Phê duyệt & Yêu cầu chỉnh sửa')).toBeVisible();
    const templateBtn = managerPage.locator('button:has-text("Sai lệch thông điệp thương hiệu")').first();
    await templateBtn.click();

    const confirmRejectBtn = managerPage.locator('button:has-text("Xác nhận Từ chối")');
    await expect(confirmRejectBtn).toBeEnabled();

    // 4. Intercept reject endpoint with 1200ms latency and duplicate detector
    let rejectCallCount = 0;
    let duplicateRejectError = false;

    await managerPage.route('**/api/v1/contents/*/reject', async (route) => {
      rejectCallCount++;
      if (rejectCallCount > 1) {
        duplicateRejectError = true;
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Chỉ có thể từ chối nội dung đang ở trạng thái chờ duyệt (IN_REVIEW)' }),
        });
      }
      await new Promise((resolve) => setTimeout(resolve, 1200));
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          status: 'REJECTED',
          rejection_reason: 'Sai lệch thông điệp thương hiệu & định vị sản phẩm',
          updated_at: new Date().toISOString(),
        }),
      });
    });

    // 5. Adversarial Action: Rapid double-click on Confirm Reject button
    await confirmRejectBtn.click({ noWaitAfter: true });

    // Verify immediate in-flight visual state & button disabling
    await expect(confirmRejectBtn).toBeDisabled();

    // Attempt second click during in-flight window
    await confirmRejectBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 6. Wait for request to settle
    await expect(managerPage.locator('text=Đã gửi phản hồi từ chối bài viết (REJECTED)').first()).toBeVisible({ timeout: 7000 });

    // 7. Empirical Invariant Assertions:
    expect(rejectCallCount).toBe(1);
    expect(duplicateRejectError).toBe(false);

    // Verify NO duplicate 400 error toast appears
    const errorToast = managerPage.locator('text=Lỗi khi từ chối bài');
    await expect(errorToast).not.toBeVisible();

    const stateToast = managerPage.locator('text=Chỉ có thể từ chối nội dung đang ở trạng thái chờ duyệt');
    await expect(stateToast).not.toBeVisible();
  });

  // --- PROBE 3: Campaign Creation Rapid Double-Click on Submit ---
  test('Probe 3: Rapid double-click on Campaign Creation Submit button disables during in-flight, preventing duplicate campaign creation', async ({ managerPage }) => {
    // 1. Navigate to Campaigns page via Sidebar "Quản Lý Chiến Dịch"
    await managerPage.click('aside button:has-text("Quản Lý Chiến Dịch")');
    await expect(managerPage.locator('text=Quản trị Chiến dịch Tiếp thị')).toBeVisible();

    // 2. Open Campaign Creation Wizard
    const createBtn = managerPage.locator('button:has-text("Tạo Chiến Dịch Mới")').first();
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // 3. Step 1: Verify Wizard opened
    await expect(managerPage.locator('#campaign-wizard-title')).toBeVisible();

    // Advance to Step 2
    await managerPage.click('button:has-text("Tiếp theo")');
    await expect(managerPage.locator('text=2. Kênh Phân phối & Phân bổ Ngân sách')).toBeVisible();

    // Advance to Step 3
    await managerPage.click('button:has-text("Tiếp theo")');
    await expect(managerPage.locator('text=Sinh trọn bộ Mẫu Quảng Cáo Đa Kênh')).toBeVisible();

    // Advance to Step 4
    //
    // Bước 4 giờ hiển thị kết quả kiểm tra tuân thủ THẬT thay vì chữ
    // "Đạt Tiêu chuẩn" viết cứng trước đây. Ở luồng này chưa bấm sinh Mẫu QC ở
    // bước 3 nên chưa có nội dung để quét — trạng thái đúng là
    // "Chưa có nội dung để kiểm tra", không phải "Đạt". Assert vào trạng thái
    // thật để test không lại đòi một kết luận tuân thủ bịa đặt.
    await managerPage.click('button:has-text("Tiếp theo")');
    await expect(managerPage.locator('text=Chưa có nội dung để kiểm tra')).toBeVisible();

    // 4. Intercept campaign creation endpoint with 1200ms latency and counter
    let campaignCreateCount = 0;
    await managerPage.route('**/campaigns', async (route) => {
      if (route.request().method() === 'POST') {
        campaignCreateCount++;
        await new Promise((resolve) => setTimeout(resolve, 1200));
        return route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 999,
            name: 'Adversarial Idempotency Test Campaign',
            product_id: 1,
            objective: 'Doanh số & Chuyển đổi',
            audience: 'Chủ shop thời trang & kinh doanh online',
            budget: 15000000,
            status: 'ACTIVE',
            created_at: new Date().toISOString(),
          }),
        });
      }
      return route.fallback();
    });

    // 5. Locate Final Submit button
    const finishBtn = managerPage.locator('button:has-text("Hoàn tất & Khởi tạo Chiến dịch")');
    await expect(finishBtn).toBeVisible();
    await expect(finishBtn).toBeEnabled();

    // 6. Adversarial Action: Rapid double-click on Submit
    await finishBtn.click({ noWaitAfter: true });

    // Verify immediate disabled state and loader text ("Đang xuất bản chiến dịch...")
    const inFlightBtn = managerPage.locator('button:has-text("Đang xuất bản chiến dịch...")');
    await expect(inFlightBtn).toBeVisible({ timeout: 2000 });
    await expect(inFlightBtn).toBeDisabled();

    // Attempt second click during in-flight window
    await inFlightBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 7. Verify success toast and modal closed
    await expect(managerPage.locator('text=đã được tạo thành công!').first()).toBeVisible({ timeout: 7000 });

    // 8. Empirical Assertions:
    expect(campaignCreateCount).toBe(1);
  });

  /**
   * Bộ đếm lượt gọi AI cho hàng đợi bất đồng bộ.
   *
   * Từ khi frontend chuyển sang `POST /ai/jobs` + poll `GET /ai/jobs/{id}`, "một
   * lượt gọi AI" được đo bằng SỐ LẦN ENQUEUE chứ không phải số request HTTP tới
   * `/ai/omnichannel`. Bộ đếm này đếm `POST /ai/jobs` và trả lời poll, nên một
   * double-click tạo ra hai lần gọi AI thật vẫn bị bắt đúng như trước.
   *
   * `minPollsBeforeSuccess` = 1 nghĩa là phải poll ít nhất một vòng trước khi
   * trả kết quả: nếu UI bỏ qua bước thăm dò mà lấy thẳng kết quả, probe vẫn
   * phải thất bại.
   */
  const queueCounter = () => ({
    enqueues: 0,
    polls: 0,
    idempotencyKeys: [] as string[],
  });

  type QueueCounter = ReturnType<typeof queueCounter>;

  /**
   * Cài hàng đợi AI giả lập trên trang: `POST /ai/jobs` trả 202, `GET
   * /ai/jobs/{id}` đi qua `running` rồi mới `succeeded`.
   *
   * Trả lời poll chỉ thành công sau `minPollsBeforeSuccess` vòng để probe bắt
   * được hành vi thăm dò thật, và độ trễ 1500ms ở lúc enqueue để nút kịp ở
   * trạng thái in-flight khi double-click.
   */
  const installAiJobQueue = async (
    page: import('@playwright/test').Page,
    state: QueueCounter,
    result: Record<string, unknown>,
    opts: { minPollsBeforeSuccess?: number; enqueueLatencyMs?: number } = {},
  ) => {
    const minPolls = opts.minPollsBeforeSuccess ?? 1;
    const latency = opts.enqueueLatencyMs ?? 1500;
    const pollsByJob: Record<number, number> = {};

    await page.route('**/ai/jobs', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      state.enqueues += 1;
      const body = route.request().postDataJSON() || {};
      if (body.idempotency_key) state.idempotencyKeys.push(body.idempotency_key);
      const jobId = 9000 + state.enqueues;
      pollsByJob[jobId] = 0;
      await new Promise((resolve) => setTimeout(resolve, latency));
      return route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: jobId,
          status: 'queued',
          kind: body.kind,
          deduplicated: false,
          poll_url: `/api/v1/ai/jobs/${jobId}`,
        }),
      });
    });

    await page.route(/\/ai\/jobs\/\d+$/, async (route) => {
      state.polls += 1;
      const jobId = Number(new URL(route.request().url()).pathname.split('/').pop());
      pollsByJob[jobId] = (pollsByJob[jobId] || 0) + 1;
      const done = pollsByJob[jobId] > minPolls;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: jobId,
          kind: 'omnichannel',
          status: done ? 'succeeded' : 'running',
          attempts: 1,
          max_attempts: 3,
          error: null,
          result: done ? result : null,
        }),
      });
    });
  };

  // --- PROBE 4: AI Generation Rapid Double-Click in Campaign Wizard ---
  test('Probe 4: Rapid double-click on AI Omnichannel generation button disables during in-flight, preventing duplicate LLM requests', async ({ managerPage }) => {
    // 1. Navigate to Campaigns page via Sidebar "Quản Lý Chiến Dịch"
    await managerPage.click('aside button:has-text("Quản Lý Chiến Dịch")');
    await expect(managerPage.locator('text=Quản trị Chiến dịch Tiếp thị')).toBeVisible();

    // 2. Open Campaign Creation Wizard and navigate to Step 3
    const createBtn = managerPage.locator('button:has-text("Tạo Chiến Dịch Mới")').first();
    await createBtn.click();
    await expect(managerPage.locator('#campaign-wizard-title')).toBeVisible();

    await managerPage.click('button:has-text("Tiếp theo")'); // to Step 2
    await expect(managerPage.locator('text=2. Kênh Phân phối & Phân bổ Ngân sách')).toBeVisible();

    await managerPage.click('button:has-text("Tiếp theo")'); // to Step 3
    await expect(managerPage.locator('text=Sinh trọn bộ Mẫu Quảng Cáo Đa Kênh')).toBeVisible();

    // 3. Chặn hàng đợi AI: `POST /ai/jobs` (202) + poll `GET /ai/jobs/{id}`.
    // Bộ đếm đo SỐ LẦN ENQUEUE — đó mới là "một lượt gọi AI" sau khi frontend
    // chuyển sang hàng đợi bất đồng bộ.
    const state = queueCounter();
    await installAiJobQueue(managerPage, state, {
      task_type: 'OMNICHANNEL',
      model_used: 'probe-model',
      model_provider: 'probe-provider',
      warnings: [],
      compliance_score: 100,
      is_fallback: false,
      facebook: {
        title: 'Adversarial Test Headline',
        headline: 'Adversarial Test Headline',
        body: 'Adversarial Test Body Text',
        primary_text: 'Adversarial Test Body Text',
        cta: 'Click Now',
        hashtags: ['#Test', '#AI'],
      },
      tiktok: {
        hook_3s: 'Adversarial TikTok Hook',
        scenes: [
          { scene_number: 1, visual_action: 'Scene 1', voiceover_script: 'Voiceover 1', duration_seconds: 5 },
        ],
      },
      email: {
        subject: 'Adversarial Email Subject',
        body: 'Adversarial Email Body',
        cta: 'Learn More',
      },
    });

    // 4. Locate "1-Click Sinh Toàn Bộ Mẫu Quảng Cáo" button
    const generateBtn = managerPage.locator('button:has-text("1-Click Sinh Toàn Bộ Mẫu Quảng Cáo")');
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toBeEnabled();

    // 5. Adversarial Action: Rapid double-click
    await generateBtn.click({ noWaitAfter: true });

    // Nhãn in-flight không còn ghi cứng "Gemini": provider thật có thể là
    // opencode/openrouter. Assert vào nhãn trung lập đã dùng ở probe 5.
    const inFlightBtn = managerPage.locator('button:has-text("AI đang sáng tạo nội dung...")');
    await expect(inFlightBtn).toBeVisible({ timeout: 2000 });
    await expect(inFlightBtn).toBeDisabled();

    // Attempt second click during in-flight
    await inFlightBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 6. Verify completion. Toast nêu provider/model lấy từ kết quả thật, nên
    // assert vào phần ổn định rồi kiểm tra có tên provider kèm theo.
    const successToast = managerPage
      .locator('text=Đã sinh thành công trọn bộ Mẫu Quảng Cáo Đa Kênh bằng')
      .first();
    await expect(successToast).toBeVisible({ timeout: 10_000 });
    await expect(successToast).toContainText('probe-provider/probe-model');

    // 7. Empirical Invariant Assertions:
    //   - đúng MỘT lần enqueue => đúng một lượt gọi AI, không trừ hạn mứng hai lần;
    //   - có thăm dò thật (không lấy kết quả bằng cách bỏ qua poll);
    //   - khoá idempotency phải được gửi đi để backend có lớp chống trùng thứ hai.
    expect(state.enqueues).toBe(1);
    expect(state.polls).toBeGreaterThanOrEqual(2);
    expect(state.idempotencyKeys).toHaveLength(1);
    expect(state.idempotencyKeys[0]).toBeTruthy();
  });

  // --- PROBE 5: AI Studio Omnichannel Rapid Double-Click ---
  test('Probe 5: Rapid double-click on Sáng tạo 3 kênh đồng thời in AI Studio disables during in-flight', async ({ managerPage }) => {
    // 1. Navigate to AI Studio via Sidebar "Xưởng Sáng Tạo AI"
    await managerPage.click('aside button:has-text("Xưởng Sáng Tạo AI")');
    await expect(managerPage.locator('text=AI Marketing Copilot & Performance Doctor')).toBeVisible();

    // 2. Chặn hàng đợi AI (POST /ai/jobs + poll) với 1500ms độ trễ lúc enqueue.
    const state = queueCounter();
    await installAiJobQueue(managerPage, state, {
      task_type: 'OMNICHANNEL',
      model_used: 'probe-model',
      model_provider: 'probe-provider',
      warnings: [],
      compliance_score: 100,
      is_fallback: false,
      facebook: { headline: 'Studio FB', primary_text: 'Body', cta: 'CTA' },
      tiktok: { hook_3s: 'Studio TikTok', scenes: [] },
      email: { subject_line_a: 'Studio Email', body_content: 'Email Body', cta_button: 'CTA' },
    });

    // 3. Locate the generate button
    const generateBtn = managerPage.locator('button:has-text("Sáng tạo 3 Kênh Đồng Thời")');
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toBeEnabled();

    // 4. Adversarial Action: Rapid double-click
    await generateBtn.click({ noWaitAfter: true });

    // Verify button disabled during in-flight with spinner text.
    //
    // Nhãn in-flight không còn hardcode "Gemini": provider thật có thể là OpenCode
    // hoặc provider khác, nên UI hiện "AI đang sáng tạo 3 kênh (có thể mất vài
    // phút)...". Assert vào nhãn trung lập này, không assert vào tên provider.
    const inFlightBtn = managerPage.locator('button:has-text("AI đang sáng tạo 3 kênh")');
    await expect(inFlightBtn).toBeVisible({ timeout: 2000 });
    await expect(inFlightBtn).toBeDisabled();

    // Attempt second click
    await inFlightBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 5. Wait for success toast
    //
    // Toast giờ kèm provider/model thật của backend nên không còn chuỗi cố định
    // "...cho cả 3 kênh tiếp thị". Assert vào phần ổn định và kiểm tra provider
    // đi kèm để vẫn bắt được việc toast phải nói đúng nguồn sinh nội dung.
    const successToast = managerPage.locator('text=Đã tạo thành công nội dung cho cả 3 kênh').first();
    await expect(successToast).toBeVisible({ timeout: 10_000 });
    await expect(successToast).toContainText('probe-provider/probe-model');

    // 6. Empirical Invariant Assertions: đúng một lần enqueue, có thăm dò thật.
    expect(state.enqueues).toBe(1);
    expect(state.polls).toBeGreaterThanOrEqual(2);
  });

  // --- PROBE 6: AIDrawer Slide-Over AI Generation Rapid Double-Click ---
  test('Probe 6: Rapid double-click on AI generation in AIDrawer slide-over disables button during in-flight', async ({ managerPage }) => {
    // 1. Open AIDrawer via Navbar button
    const openDrawerBtn = managerPage.locator('button:has-text("AI Copilot")');
    await expect(openDrawerBtn).toBeVisible();
    await openDrawerBtn.click();

    // 2. Verify AIDrawer is open
    await expect(managerPage.locator('#ai-drawer-title')).toBeVisible();

    // 3. Chặn hàng đợi AI (POST /ai/jobs + poll) với 1500ms độ trễ lúc enqueue.
    const state = queueCounter();
    await installAiJobQueue(managerPage, state, {
      task_type: 'OMNICHANNEL',
      model_used: 'probe-model',
      model_provider: 'probe-provider',
      warnings: [],
      compliance_score: 100,
      is_fallback: false,
      facebook: { headline: 'Drawer FB', primary_text: 'Body', cta: 'CTA' },
      tiktok: { hook_3s: 'Drawer TikTok', scenes: [] },
      email: { subject_line_a: 'Drawer Email', body_content: 'Email Body', cta_button: 'CTA' },
    });

    // 4. Locate drawer omnichannel button
    const drawerOmniBtn = managerPage.locator('button:has-text("Sáng tạo 3 kênh đồng thời")');
    await expect(drawerOmniBtn).toBeVisible();
    await expect(drawerOmniBtn).toBeEnabled();

    // Fill brief if empty
    const briefInput = managerPage.locator('#omni-brief-input');
    await briefInput.fill('Chiến dịch tuyển sinh CNTT 2026');

    // 5. Adversarial Action: Rapid double-click
    await drawerOmniBtn.click({ noWaitAfter: true });

    // Verify button disabled during in-flight
    await expect(drawerOmniBtn).toBeDisabled();

    // Attempt second click during in-flight
    await drawerOmniBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 6. Wait for success toast
    const successToast = managerPage
      .locator('text=Đã sinh thành công nội dung sáng tạo cho cả 3 kênh!')
      .first();
    await expect(successToast).toBeVisible({ timeout: 10_000 });
    await expect(successToast).toContainText('probe-provider/probe-model');

    // 7. Empirical Invariant Assertions: đúng một lần enqueue, có thăm dò thật.
    expect(state.enqueues).toBe(1);
    expect(state.polls).toBeGreaterThanOrEqual(2);
  });

});
