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
    await managerPage.click('button:has-text("Tiếp theo")');
    await expect(managerPage.locator('text=Đạt Tiêu chuẩn Quảng cáo Meta & TikTok')).toBeVisible();

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

    // 3. Intercept AI generation endpoint (POST /api/v1/ai/omnichannel) with 1500ms latency and counter
    let aiCallCount = 0;
    await managerPage.route('**/ai/omnichannel', async (route) => {
      aiCallCount++;
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_type: 'OMNICHANNEL',
          model_used: 'Gemini 2.5 Flash',
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
        }),
      });
    });

    // 4. Locate "1-Click Sinh Toàn Bộ Mẫu Quảng Cáo" button
    const generateBtn = managerPage.locator('button:has-text("1-Click Sinh Toàn Bộ Mẫu Quảng Cáo")');
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toBeEnabled();

    // 5. Adversarial Action: Rapid double-click
    await generateBtn.click({ noWaitAfter: true });

    // Verify immediate disabled state & spinner text ("Gemini đang sáng tạo nội dung...")
    const inFlightBtn = managerPage.locator('button:has-text("Gemini đang sáng tạo nội dung...")');
    await expect(inFlightBtn).toBeVisible({ timeout: 2000 });
    await expect(inFlightBtn).toBeDisabled();

    // Attempt second click during in-flight
    await inFlightBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 6. Verify completion
    await expect(managerPage.locator('text=Google Gemini đã sinh thành công trọn bộ Mẫu Quảng Cáo Đa Kênh!').first()).toBeVisible({ timeout: 7000 });

    // 7. Empirical Invariant Assertion:
    expect(aiCallCount).toBe(1);
  });

  // --- PROBE 5: AI Studio Omnichannel Rapid Double-Click ---
  test('Probe 5: Rapid double-click on Sáng tạo 3 kênh đồng thời in AI Studio disables during in-flight', async ({ managerPage }) => {
    // 1. Navigate to AI Studio via Sidebar "Xưởng Sáng Tạo AI"
    await managerPage.click('aside button:has-text("Xưởng Sáng Tạo AI")');
    await expect(managerPage.locator('text=AI Marketing Copilot & Performance Doctor')).toBeVisible();

    // 2. Intercept AI generation endpoint (POST /api/v1/ai/omnichannel) with 1500ms latency
    let studioAiCount = 0;
    await managerPage.route('**/ai/omnichannel', async (route) => {
      studioAiCount++;
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_type: 'OMNICHANNEL',
          model_used: 'Gemini 2.5 Flash',
          warnings: [],
          compliance_score: 100,
          is_fallback: false,
          facebook: { headline: 'Studio FB', primary_text: 'Body', cta: 'CTA' },
          tiktok: { hook_3s: 'Studio TikTok', scenes: [] },
          email: { subject_line_a: 'Studio Email', body_content: 'Email Body', cta_button: 'CTA' },
        }),
      });
    });

    // 3. Locate the generate button
    const generateBtn = managerPage.locator('button:has-text("Sáng tạo 3 Kênh Đồng Thời")');
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toBeEnabled();

    // 4. Adversarial Action: Rapid double-click
    await generateBtn.click({ noWaitAfter: true });

    // Verify button disabled during in-flight with spinner text ("Gemini đang sáng tạo 3 kênh...")
    const inFlightBtn = managerPage.locator('button:has-text("Gemini đang sáng tạo 3 kênh...")');
    await expect(inFlightBtn).toBeVisible({ timeout: 2000 });
    await expect(inFlightBtn).toBeDisabled();

    // Attempt second click
    await inFlightBtn.click({ force: true, noWaitAfter: true }).catch(() => {});

    // 5. Wait for success toast
    await expect(managerPage.locator('text=Đã tạo thành công nội dung sáng tạo cho cả 3 kênh tiếp thị').first()).toBeVisible({ timeout: 7000 });

    // 6. Empirical Invariant Assertion:
    expect(studioAiCount).toBe(1);
  });

  // --- PROBE 6: AIDrawer Slide-Over AI Generation Rapid Double-Click ---
  test('Probe 6: Rapid double-click on AI generation in AIDrawer slide-over disables button during in-flight', async ({ managerPage }) => {
    // 1. Open AIDrawer via Navbar button
    const openDrawerBtn = managerPage.locator('button:has-text("AI Copilot")');
    await expect(openDrawerBtn).toBeVisible();
    await openDrawerBtn.click();

    // 2. Verify AIDrawer is open
    await expect(managerPage.locator('#ai-drawer-title')).toBeVisible();

    // 3. Intercept Omnichannel generation
    let drawerAiCount = 0;
    await managerPage.route('**/ai/omnichannel', async (route) => {
      drawerAiCount++;
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_type: 'OMNICHANNEL',
          model_used: 'Gemini 2.5 Flash',
          warnings: [],
          compliance_score: 100,
          is_fallback: false,
          facebook: { headline: 'Drawer FB', primary_text: 'Body', cta: 'CTA' },
          tiktok: { hook_3s: 'Drawer TikTok', scenes: [] },
          email: { subject_line_a: 'Drawer Email', body_content: 'Email Body', cta_button: 'CTA' },
        }),
      });
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
    await expect(managerPage.locator('text=Đã sinh thành công nội dung sáng tạo cho cả 3 kênh!').first()).toBeVisible({ timeout: 7000 });

    // 7. Empirical Invariant Assertion:
    expect(drawerAiCount).toBe(1);
  });

});
