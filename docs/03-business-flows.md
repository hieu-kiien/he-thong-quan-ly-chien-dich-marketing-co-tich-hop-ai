---
document_id: AIA331-DOC-03
document_type: business-flows
project_id: AIA331-80300-MARKETING-AI
status: DERIVED
last_reviewed: 2026-08-18
---

# Luồng nghiệp vụ và bất biến

## FLOW-001 — Tạo và theo dõi chiến dịch

1. Người dùng đăng nhập và được kiểm tra quyền.
2. Tạo campaign với mục tiêu, audience, product, thời gian, budget, status.
3. Gắn các channel và content vào campaign.
4. Nhập metric theo ngày và kênh.
5. Hệ thống tính tổng views/clicks/conversions/cost và các tỷ lệ.

## FLOW-002 — Sinh và duyệt nội dung AI

```text
Campaign brief + channel + tone
        -> prompt AI-CAM-001-v1
        -> provider hoặc fallback
        -> draft + warning + needs_human_approval=true
        -> Marketing Manager review
        -> APPROVED -> PUBLISHED
```

Nếu nội dung chưa `APPROVED`, thao tác publish phải bị từ chối. Đây là ranh giới
an toàn tối thiểu, không phải tùy chọn giao diện.

## FLOW-003 — Cập nhật metric

Metric được ghi theo `(campaign, channel, metric_date)`. Input âm, click lớn hơn
view hoặc conversion lớn hơn click bị từ chối. Khi thiếu dữ liệu, báo cáo phải
nêu “chưa đủ dữ liệu”, không suy đoán thành số thật.

## FLOW-004 — Tìm kiếm/lọc

Người dùng nhập tên hoặc trạng thái → view áp filter ORM → trả danh sách campaign
đã lọc. Khi mở rộng, thêm filter theo channel, thời gian và trạng thái content.

## Invariants

| ID | Bất biến | Cách bảo vệ |
|---|---|---|
| FLOW-I01 | Ngày bắt đầu không sau ngày kết thúc | `Campaign.clean()` |
| FLOW-I02 | Click không vượt lượt xem | `Metric.clean()` |
| FLOW-I03 | Conversion không vượt click | `Metric.clean()` |
| FLOW-I04 | Không trùng metric cùng ngày/kênh | DB unique constraint |
| FLOW-I05 | AI không tự đăng | `Content.publish()` |
