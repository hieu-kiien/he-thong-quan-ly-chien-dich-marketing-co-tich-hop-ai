---
document_id: AIA331-PROJECT-BRIEF
document_type: official-project-brief
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
course: Ứng dụng trí tuệ nhân tạo - AIA331
assignment_code: "80300"
assignment_type: Dự án
priority: P1
priority_level: HIGH
priority_rationale: Hồ sơ chính thức của đề tài AIA331, cần ưu tiên cao nhất cho phân tích, triển khai và nộp bài.
status: CANONICAL
source: source-materials/DỰ ÁN.png do người dùng cung cấp
language: vi
last_reviewed: 2026-08-18
---

# Hệ thống quản lý chiến dịch marketing có tích hợp AI

Đây là bản yêu cầu gốc của dự án môn **Ứng dụng trí tuệ nhân tạo - AIA331**,
mã số **80300**, hình thức **Dự án**. Tên đề tài chính thức được lấy nguyên
nghĩa từ ảnh `DỰ ÁN.png`; không được thay bằng đề tài quản lý bán hàng.

## 1. Phân tích đúng bài toán quản lý

Doanh nghiệp cần quản lý tập trung các chiến dịch marketing, kênh truyền thông,
nội dung, ngân sách, lịch đăng và chỉ số hiệu quả. Việc lên ý tưởng nội dung và
tổng hợp kết quả còn tốn thời gian. Hệ thống cần giải quyết hai lớp vấn đề:

1. Quản lý dữ liệu và quy trình chiến dịch một cách nhất quán.
2. Tích hợp AI để hỗ trợ sinh nội dung nháp, tóm tắt hiệu quả và gợi ý cải thiện,
   nhưng không thay thế phê duyệt của con người.

### 1.1. Actor chính

| Actor | Trách nhiệm trong phạm vi dự án | Trạng thái |
|---|---|---|
| Quản lý marketing | Tạo/sửa chiến dịch, ngân sách, kênh, duyệt nội dung, xem thống kê | CANONICAL |
| Nhân viên marketing | Nhập nội dung, lịch đăng, chỉ số; yêu cầu AI sinh bản nháp | CANONICAL |
| AI service | Sinh ý tưởng, caption/email nháp, tóm tắt và gợi ý từ dữ liệu được cấp | CANONICAL về vai trò; adapter là IMPLEMENTED_BASELINE |

## 2. Mục tiêu

- Quản lý chiến dịch, kênh, nội dung, ngân sách, lịch đăng và chỉ số.
- Tích hợp AI để sinh ý tưởng nội dung, báo cáo hiệu quả và gợi ý tối ưu.
- Sử dụng AI trong SDLC và trong quy trình vận hành marketing có kiểm soát.
- Lưu được nguồn, phiên bản prompt và trạng thái duyệt để người dùng kiểm tra.

## 3. Yêu cầu chức năng

### 3.1. Chức năng quản lý

| ID | Chức năng | Đầu vào chính | Kết quả cần có |
|---|---|---|---|
| FR-001 | Đăng nhập và phân quyền | Tài khoản, vai trò | Quản lý và nhân viên chỉ dùng được chức năng được cấp |
| FR-002 | Quản lý chiến dịch | Tên, mục tiêu, thời gian, ngân sách, trạng thái | Tạo, xem, sửa và tra cứu chiến dịch |
| FR-003 | Quản lý kênh truyền thông | Tên/loại kênh, trạng thái hoạt động | Danh mục kênh để gắn vào nội dung và chỉ số |
| FR-004 | Quản lý nội dung và lịch đăng | Kênh, loại nội dung, nội dung, thời điểm đăng | Nội dung gắn chiến dịch và có lịch đăng |
| FR-005 | Ghi nhận chỉ số | Lượt xem, click, chuyển đổi, chi phí, ngày, kênh | Chỉ số hợp lệ theo chiến dịch và kênh |
| FR-006 | Duyệt nội dung | Nội dung nháp, người duyệt, kết quả duyệt | Chỉ nội dung đã duyệt mới được phép dùng/đăng |
| FR-007 | Tìm kiếm và lọc | Tên, kênh, thời gian, trạng thái | Danh sách kết quả đúng điều kiện |
| FR-008 | Thống kê hiệu quả | Dữ liệu chỉ số và ngân sách | Tổng lượt xem/click/chuyển đổi, CTR, chi phí/chuyển đổi |

### 3.2. Chức năng AI

| ID | Chức năng | Input bắt buộc | Output | Ràng buộc |
|---|---|---|---|---|
| AI-001 | Sinh ý tưởng nội dung theo mục tiêu | Mục tiêu, đối tượng, sản phẩm, kênh | Danh sách ý tưởng có hook, nội dung, CTA | Chỉ là bản nháp; phải duyệt |
| AI-002 | Sinh caption/email nháp theo kênh | Campaign brief, kênh, giọng văn | Caption/email nháp phù hợp kênh | Không bịa cam kết/số liệu; phải duyệt |
| AI-003 | Tóm tắt hiệu quả và gợi ý cải thiện | Chỉ số chiến dịch, ngân sách, thời gian | Báo cáo ngắn và gợi ý hành động | Grounding từ dữ liệu hệ thống; nêu thiếu dữ liệu |

## 4. Yêu cầu phi chức năng và kỹ thuật

Các mục dưới đây là cách cụ thể hóa yêu cầu trong đề bài để có thể kiểm thử;
chúng không được dùng làm bằng chứng nếu chưa có test hoặc đo lường.

| ID | Yêu cầu | Tiêu chí kiểm tra baseline |
|---|---|---|
| NFR-001 | Bảo mật và phân quyền | Có authentication; API key chỉ ở `.env`; kiểm tra quyền trước màn hình quản lý |
| NFR-002 | Kiểm soát AI | AI output có version/provider/warning; nội dung phải qua trạng thái duyệt |
| NFR-003 | Tính toàn vẹn dữ liệu | Ngày hợp lệ; click không vượt view; conversion không vượt click; metric không trùng ngày/kênh |
| NFR-004 | Khả dụng | Có SQLite demo, migration, seed và hướng dẫn chạy sạch |
| NFR-005 | Trải nghiệm | Có lọc/tìm kiếm, thông báo thao tác và hiển thị trạng thái rõ ràng |
| NFR-006 | Khả năng kiểm thử | Có test cho chiến dịch, thống kê, duyệt nội dung và fallback AI |

### 4.1. Công nghệ được đề bài cho phép

- Backend: FastAPI, Flask hoặc Django.
- Frontend: React, Vue hoặc HTML.
- CSDL: SQLite, MySQL hoặc PostgreSQL.
- AI: OpenAI, Gemini, Claude, Hugging Face hoặc Ollama.
- Baseline của repo này chọn **Django + SQLite + HTML template + provider adapter
  OpenAI-compatible/fallback offline** để chạy được trong môi trường học tập.

## 5. Dữ liệu vào/ra và mô hình nghiệp vụ

### 5.1. Dữ liệu chính

`Campaign`, `Channel`, `Content`, `Schedule`, `Budget`, `Metric`, `User` và
`Role`. Baseline gộp lịch vào `Content.scheduled_at` và ngân sách vào
`Campaign.budget`; nếu mở rộng có thể tách thành bảng riêng.

### 5.2. Dữ liệu vào/ra AI

| Nhóm | Dữ liệu |
|---|---|
| Input | Mục tiêu, đối tượng, kênh, sản phẩm, campaign brief, giọng văn, metric đã được cấp quyền |
| Output | Ý tưởng, caption/email nháp, tóm tắt hiệu quả, gợi ý cải thiện |
| Không gửi mặc định | API key, mật khẩu, dữ liệu cá nhân không cần thiết, dữ liệu ngoài quyền người dùng |

## 6. Prompt mẫu chính thức

```text
System: Bạn là trợ lý marketing. Tạo nội dung nháp để con người duyệt, không
đưa ra cam kết sai sự thật. Chỉ sử dụng thông tin trong campaign brief và dữ
liệu được cung cấp. Nêu rõ khi thiếu dữ liệu.

User: Chiến dịch: {{campaign_brief}}. Hãy đề xuất 5 ý tưởng nội dung cho kênh
Facebook, giọng văn thân thiện. Mỗi ý tưởng gồm hook, nội dung ngắn và CTA.
```

Prompt runtime của baseline có ID/phiên bản `AI-CAM-001-v1` tại
`marketing_management/campaigns/ai_service.py`.

## 7. Sử dụng AI trong SDLC

| Giai đoạn | Việc dùng AI theo đề bài | Bằng chứng cần lưu |
|---|---|---|
| KT1 | Phân tích chiến dịch, nội dung, chỉ số; thiết kế ERD và chức năng AI | Prompt, phản hồi, bản đã kiểm chứng |
| KT2 | Sinh CRUD chiến dịch, lịch đăng, chỉ số; debug báo cáo | Commit, test, log sửa lỗi |
| KT3 | Thiết kế prompt sinh nội dung; test chất lượng/sai hoặc quá đà | Các phiên bản prompt và bảng đánh giá |
| Cuối kỳ | Sinh tài liệu, báo cáo, slide; đánh giá chất lượng AI | Báo cáo, checklist, tiêu chí đánh giá |

## 8. Trạng thái triển khai hiện tại

| Phạm vi | Trạng thái | Bằng chứng |
|---|---|---|
| Model chiến dịch/kênh/nội dung/chỉ số | IMPLEMENTED_BASELINE | `marketing_management/campaigns/models.py`, migration |
| CRUD/tra cứu chiến dịch | IMPLEMENTED_BASELINE | `campaigns/views.py`, templates, tests |
| Tổng hợp CTR/chi phí/chuyển đổi | IMPLEMENTED_BASELINE | `Campaign.performance_summary()`, tests |
| Approval gate cho nội dung AI | IMPLEMENTED_BASELINE | `Content.approve/publish()`, tests |
| Gọi provider ngoài | PROPOSED/OPTIONAL | Adapter có hợp đồng; cần API key và kiểm thử tích hợp |
| Báo cáo AI từ metric trong UI | PROPOSED | Cần bổ sung màn hình/endpoint sau baseline |

## 9. Mức độ khó

**Trung bình.** Dữ liệu nghiệp vụ không quá phức tạp nhưng cần quy trình duyệt
nội dung AI và cách đánh giá kết quả chiến dịch.

## 10. Cấp ưu tiên của dự án

`P1 / HIGH` là metadata quản lý hồ sơ do nhóm đặt theo yêu cầu người dùng: đây
là đề tài chính thức cần dùng làm nguồn duy nhất cho tài liệu, mã nguồn, RAG và
hồ sơ nộp. Cấp ưu tiên không phải là điểm số hay yêu cầu mới của giảng viên.
