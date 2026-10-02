import { test, expect } from './fixtures/auth.fixture';

test.describe('Golden Journey 2: Manager Review Queue, Rejection & Approval Workflow', () => {

  test('Manager rejects draft -> Marketer views rejection feedback & resubmits -> Back to review queue', async ({ managerPage }) => {
    // 1. Manager navigates to Review Queue
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // 2. Verify pending item is present
    await expect(managerPage.locator('text=CHỜ DUYỆT (IN_REVIEW)').first()).toBeVisible();
    await expect(managerPage.locator('text=Đột phá sự nghiệp cùng Kỹ sư AI 2026 tại ICTU!').first()).toBeVisible();

    // 3. Click "Từ chối (Reject)"
    const rejectBtn = managerPage.locator('button:has-text("Từ chối (Reject)")').first();
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();

    // 4. Verify Rejection Modal opens
    await expect(managerPage.locator('text=Từ chối Phê duyệt & Yêu cầu chỉnh sửa')).toBeVisible();

    // 5. Select quick template feedback
    const templateBtn = managerPage.locator('button:has-text("Sai lệch thông điệp thương hiệu")').first();
    await expect(templateBtn).toBeVisible();
    await templateBtn.click();

    // 6. Confirm reject
    const confirmRejectBtn = managerPage.locator('button:has-text("Xác nhận Từ chối")');
    await expect(confirmRejectBtn).toBeEnabled();
    await confirmRejectBtn.click();

    // 7. Verify toast notification
    await expect(managerPage.locator('text=Đã gửi phản hồi từ chối bài viết (REJECTED)').first()).toBeVisible({ timeout: 7000 });

    // 8. Tab "Lịch sử duyệt bài" chỉ chứa APPROVED/PUBLISHED.
    //
    // Bài bị từ chối cố ý KHÔNG nằm ở đây: nó cần marketer sửa và gửi lại nên
    // thuộc tab nháp (xem `historyList`/`draftList` trong ReviewQueue.tsx — trước
    // đây REJECTED nằm ở cả hai tab, bị đếm hai lần và hiện trùng). Vì vậy bước
    // này chỉ xác nhận bài đã từ chối KHÔNG lọt sang lịch sử; nội dung và phản
    // hồi của nó được kiểm ở bước 9.
    await managerPage.click('button:has-text("Lịch sử duyệt bài")');
    await expect(managerPage.locator('text=Lịch sử Phê duyệt').first()).toBeVisible();
    await expect(managerPage.locator('text=ĐÃ TỪ CHỐI')).toHaveCount(0);

    // 9. Switch to "Bản nháp chờ gửi duyệt" tab to see rejected item with feedback
    await managerPage.click('button:has-text("Bản nháp chờ gửi duyệt")');
    await expect(managerPage.locator('text=CẦN CHỈNH SỬA (REJECTED)').first()).toBeVisible();
    await expect(managerPage.locator('text=Sai lệch thông điệp thương hiệu').first()).toBeVisible();

    // 10. Click "Sửa & Gửi lại (Resubmit)" to send item back to review queue
    const resubmitBtn = managerPage.locator('button:has-text("Sửa & Gửi lại (Resubmit)")').first();
    await expect(resubmitBtn).toBeVisible();
    await resubmitBtn.click();

    // 11. Verify resubmit toast notification
    await expect(managerPage.locator('text=Đã chuyển bài viết sang Hàng đợi phê duyệt (IN_REVIEW)!').first()).toBeVisible({ timeout: 7000 });

    // 12. Switch back to "Chờ phê duyệt" tab and verify item is back in review queue
    await managerPage.click('button:has-text("Chờ phê duyệt")');
    await expect(managerPage.locator('text=CHỜ DUYỆT (IN_REVIEW)').first()).toBeVisible();
  });

  test('Manager: Review Queue -> 1-Click Approve -> Status updates to APPROVED and schedules via Calendar', async ({ managerPage }) => {
    // 1. Manager navigates to Review Queue
    await managerPage.click('button:has-text("Hàng Đợi Phê Duyệt")');
    await expect(managerPage.locator('text=Hàng Đợi Phê Duyệt Nội Dung')).toBeVisible();

    // 2. Click Approve on pending item (Genuine assertion without conditional skips)
    const approveBtn = managerPage.locator('button:has-text("Phê duyệt (Approve)")').first();
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // 3. Verify approval success toast
    await expect(managerPage.locator('text=Đã phê duyệt bài viết thành công (APPROVED)!').first()).toBeVisible({ timeout: 7000 });

    // 4. Navigate to "Lịch Xuất Bản"
    await managerPage.click('button:has-text("Lịch Xuất Bản")');
    await expect(managerPage.locator('text=Lịch Xuất Bản').or(managerPage.locator('text=Marketing Calendar')).first()).toBeVisible();

    // 5. Open Schedule Publication Modal
    const openScheduleBtn = managerPage.locator('button:has-text("Lên lịch xuất bản")').first();
    await expect(openScheduleBtn).toBeVisible();
    await openScheduleBtn.click();

    // 6. Verify Schedule Modal is open
    await expect(managerPage.locator('text=Lập Lịch Xuất Bản Đa Kênh')).toBeVisible();

    // 7. Confirm schedule creation
    const confirmScheduleBtn = managerPage.locator('button:has-text("Xác nhận Lên lịch")');
    await expect(confirmScheduleBtn).toBeVisible();
    await confirmScheduleBtn.click();

    // 8. Verify schedule success toast
    await expect(managerPage.locator('text=Đã lập lịch xuất bản bài viết thành công').first()).toBeVisible({ timeout: 7000 });
  });

});
