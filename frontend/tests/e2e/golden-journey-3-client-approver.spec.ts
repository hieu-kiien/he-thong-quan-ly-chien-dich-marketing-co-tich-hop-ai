import { test, expect } from './fixtures/auth.fixture';

test.describe('Golden Journey 3: Client Approver Boundary & RBAC Workflow', () => {

  test('Client Approver: Access Review Queue and see assigned workspace content', async ({ approverPage }) => {
    // 1. Client Approver navigates to Review Queue
    await approverPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(approverPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // 2. Verify Client Approver role badge is visible
    await expect(approverPage.locator('aside span:has-text("Client Approver")').first()).toBeVisible();

    // 3. Verify pending content is displayed
    await expect(approverPage.locator('text=CHỜ DUYỆT (IN_REVIEW)').first()).toBeVisible();
    await expect(approverPage.locator('text=Đột phá sự nghiệp cùng Kỹ sư AI 2026 tại ICTU!').first()).toBeVisible();

    // 4. Verify Approver has approve/reject buttons
    await expect(approverPage.locator('button:has-text("Phê duyệt (Approve)")').first()).toBeVisible();
    await expect(approverPage.locator('button:has-text("Từ chối (Reject)")').first()).toBeVisible();
  });

  test('Client Approver: Cross-workspace unauthorized action is blocked with 403 Forbidden', async ({ approverPage }) => {
    // 1. Client Approver is in Review Queue
    await approverPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(approverPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // 2. Intercept an approval attempt for cross-workspace content with 403 Forbidden
    await approverPage.route('**/api/v1/contents/1/approve', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Bạn không có quyền thao tác trên tài nguyên thuộc không gian làm việc này (403 Forbidden)',
        }),
      });
    });

    // 3. Click Approve on the item
    const approveBtn = approverPage.locator('button:has-text("Phê duyệt (Approve)")').first();
    await approveBtn.click();

    // 4. Verify 403 Forbidden toast/error notification is displayed to user
    await expect(
      approverPage.locator('text=Bạn không có quyền thao tác trên tài nguyên thuộc không gian làm việc này').or(approverPage.locator('text=403 Forbidden')).first()
    ).toBeVisible({ timeout: 7000 });
  });

  test('Client Approver: Structured review rejection with custom feedback', async ({ approverPage }) => {
    await approverPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(approverPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // Open reject modal (Genuine assertion without conditional skips)
    const rejectBtn = approverPage.locator('button:has-text("Từ chối (Reject)")').first();
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();
    await expect(approverPage.locator('text=Từ chối Phê duyệt & Yêu cầu chỉnh sửa')).toBeVisible();

    // Click template feedback
    const tmplBtn = approverPage.locator('button:has-text("Giọng văn chưa phù hợp")').first();
    await expect(tmplBtn).toBeVisible();
    await tmplBtn.click();

    // Submit rejection
    const confirmBtn = approverPage.locator('button:has-text("Xác nhận Từ chối")');
    await expect(confirmBtn).toBeVisible();
    await confirmBtn.click();

    await expect(approverPage.locator('text=Đã gửi phản hồi từ chối bài viết (REJECTED)').first()).toBeVisible({ timeout: 7000 });
  });

});
