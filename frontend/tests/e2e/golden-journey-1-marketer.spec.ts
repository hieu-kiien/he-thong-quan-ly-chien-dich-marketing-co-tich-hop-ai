import { test, expect } from './fixtures/auth.fixture';

test.describe('Golden Journey 1: Marketer End-to-End Workflow', () => {

  test('Marketer: Campaign creation -> AI prompt -> Draft generation -> Compliance fix -> Submit for Review (HITL)', async ({ marketerPage }) => {
    test.setTimeout(60000);
    // 1. Marketer navigates to Campaigns and creates a new Campaign in UI
    await marketerPage.click('button:has-text("Quản Lý Chiến Dịch")');
    await expect(marketerPage.locator('text=Quản Lý Chiến Dịch').or(marketerPage.locator('text=Danh sách Chiến dịch')).first()).toBeVisible();

    const createCampaignBtn = marketerPage.locator('button:has-text("Tạo Chiến Dịch Mới")');
    await expect(createCampaignBtn).toBeVisible();
    await createCampaignBtn.click();

    // Wizard Step 1: Objective & Budget -> Fill Name -> Next
    await expect(marketerPage.locator('text=Quy trình Thiết lập Chiến dịch Quảng cáo')).toBeVisible();
    await marketerPage.fill('input[placeholder*="Nhập tên chiến dịch"]', 'Chiến dịch Tuyển sinh Kỹ sư AI 2026');
    await marketerPage.locator('button:has-text("Tiếp theo")').click();

    // Wizard Step 2: Channels & Audience -> Next
    await marketerPage.locator('button:has-text("Tiếp theo")').click();

    // Wizard Step 3: Creatives -> Next
    await marketerPage.locator('button:has-text("Tiếp theo")').click();

    // Wizard Step 4: Finish & Launch Campaign
    const finishBtn = marketerPage.locator('button:has-text("Hoàn tất & Khởi tạo Chiến dịch")');
    await expect(finishBtn).toBeVisible();
    await finishBtn.click();

    // Verify campaign creation success toast
    await expect(marketerPage.locator('text=đã được tạo thành công!').first()).toBeVisible({ timeout: 7000 });

    // 2. Marketer navigates to AI Studio
    await marketerPage.click('button:has-text("Xưởng Sáng Tạo AI")');
    await expect(marketerPage.locator('text=AI Marketing Copilot').first()).toBeVisible();

    // 3. Switch to Single-Channel Mode ("🎯 Đơn kênh (AIDA/PAS)")
    const singleChannelTab = marketerPage.locator('button:has-text("Đơn kênh")').first();
    await singleChannelTab.click();

    // 4. Click "Khởi tạo 5 Góc Ý Tưởng Tiếp Thị"
    const generateIdeasBtn = marketerPage.locator('button:has-text("Khởi tạo 5 Góc Ý Tưởng Tiếp Thị")').first();
    await expect(generateIdeasBtn).toBeVisible();
    await generateIdeasBtn.click();

    // Verify AI ideas are displayed
    await expect(marketerPage.locator('text=Chinh phục kỷ nguyên AI cùng thực hành GPU đỉnh cao').first()).toBeVisible({ timeout: 10000 });
    await expect(marketerPage.locator('text=Học AI từ chuyên gia doanh nghiệp hàng đầu').first()).toBeVisible();

    // 5. Select the first idea and generate draft ("Viết thành bài hoàn chỉnh")
    const useIdeaBtn = marketerPage.locator('button:has-text("Viết thành bài hoàn chỉnh")').first();
    await useIdeaBtn.click();

    // Verify Draft is generated with Title, Body, CTA
    await expect(marketerPage.locator('text=Khởi đầu sự nghiệp Kỹ sư AI cùng chương trình thực hành chuẩn quốc tế 2026').first()).toBeVisible({ timeout: 10000 });
    await expect(marketerPage.locator('text=Đăng ký nhận tư vấn lộ trình và học bổng ngay').first()).toBeVisible();

    // 6. Check Compliance & Policy -> Trigger violation warning for banned keyword ("cam kết 100%")
    const complianceBtn = marketerPage.locator('button:has-text("Quét Tuân thủ (Compliance Check)")').first();
    await expect(complianceBtn).toBeVisible();
    await complianceBtn.click();

    // Verify Compliance Violation Badge and submission button locked
    await expect(marketerPage.locator('text=VI PHẠM CHÍNH SÁCH (VIOLATION)').first()).toBeVisible({ timeout: 7000 });
    await expect(marketerPage.locator('text=45/100 Điểm').first()).toBeVisible();
    await expect(marketerPage.locator('button:has-text("Bị khóa do Vi phạm Chính sách")').first()).toBeVisible();

    // Fix violation using 1-Click AutoFix ("Sửa ngay")
    const autoFixBtn = marketerPage.locator('button:has-text("Sửa ngay")').first();
    await expect(autoFixBtn).toBeVisible();
    await autoFixBtn.click();

    // Verify updated status: PASSED (100/100 Điểm) and submit button unlocked
    await expect(marketerPage.locator('text=ĐẠT CHUẨN TUÂN THỦ (PASSED)').first()).toBeVisible({ timeout: 7000 });
    await expect(marketerPage.locator('text=100/100 Điểm').first()).toBeVisible();

    // 7. Submit draft for Human-in-the-loop review ("Lưu vào Chiến dịch & Gửi Sếp duyệt ngay (HITL)")
    const submitBtn = marketerPage.locator('button:has-text("Lưu vào Chiến dịch & Gửi Sếp duyệt ngay (HITL)")').first();
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // 8. Verify submission success feedback
    await expect(marketerPage.locator('text=Đã lưu bài viết vào Chiến dịch & Đưa vào Hàng đợi').or(marketerPage.locator('text=IN_REVIEW')).first()).toBeVisible({ timeout: 7000 });
  });

  test('Marketer: Multi-channel 3-in-1 Omnichannel Generation & Facebook/TikTok/Email Preview', async ({ marketerPage }) => {
    test.setTimeout(60000);
    // 1. Navigate to AI Studio
    await marketerPage.click('button:has-text("Xưởng Sáng Tạo AI")');
    await expect(marketerPage.locator('text=AI Marketing Copilot').first()).toBeVisible();

    // 2. Ensure Omnichannel section is active
    const omniTab = marketerPage.locator('button:has-text("Đa kênh 3-in-1")').first();
    await omniTab.click();

    // 3. Click Generate Omnichannel Content
    const generateOmniBtn = marketerPage.locator('button:has-text("Sáng tạo 3 Kênh Đồng Thời")').first();
    await expect(generateOmniBtn).toBeVisible();
    await generateOmniBtn.click();

    // 4. Verify 3 channels headings are generated and displayed
    await expect(marketerPage.locator('text=1. Facebook Feed & Ads').first()).toBeVisible({ timeout: 10000 });
    await expect(marketerPage.locator('text=2. TikTok Video Script').first()).toBeVisible();
    await expect(marketerPage.locator('text=3. Email Marketing Sequence').first()).toBeVisible();

    // 5. Verify Facebook content rendered
    await expect(marketerPage.locator('text=Bứt Phá Thu Nhập Cùng Nghề Kỹ Sư AI Thực Chiến').first()).toBeVisible();

    // 6. Test 1-Click Copy formatted content
    const copyBtn = marketerPage.locator('button:has-text("Copy format chuẩn")').first();
    await expect(copyBtn).toBeVisible();
    await copyBtn.click();
    await expect(marketerPage.locator('text=Đã copy toàn bộ!').first()).toBeVisible({ timeout: 5000 });
  });

});
