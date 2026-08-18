---
document_id: BAI03-DOC-08
document_type: documentation-standard
project_id: BAI03-SALES-AI
status: CANONICAL
authority: project-documentation-policy
language: vi
version: 1.0
last_reviewed: 2026-08-18
source_of_truth: true
---

# Chuẩn tài liệu BAI03-SALES-AI

## 1. Mục đích và phạm vi

Tài liệu này áp dụng cho repository BAI03-SALES-AI, đặc biệt là báo cáo phân
tích và thiết kế nộp cho học phần Ứng dụng AI. Bài 01 về kỹ thuật prompt là
một bài độc lập và không được gộp vào hồ sơ BAI03.

Chuẩn có hai tầng:

| Tầng | Dùng cho | Đầu ra chính |
|---|---|---|
| Submission | Người chấm, in và nộp | DOCX/PDF có bìa, mục lục, hình/bảng, trích dẫn và phụ lục |
| Knowledge | Thành viên, Git, AI và RAG | Markdown/YAML có ID, status, nguồn, liên kết tương đối và khả năng diff |

Mục tiêu không phải kéo dài tài liệu. Mỗi phần phải trả lời một mục của đề,
cung cấp bằng chứng hoặc giúp người đọc tái lập kết luận.

## 2. Thứ tự ưu tiên nguồn

Khi có xung đột, dùng thứ tự sau:

1. Hướng dẫn hiện tại của giảng viên và đề bài của bài đang nộp.
2. Mẫu hiện hành của Khoa Công nghệ thông tin hoặc học phần.
3. Quy định/quy trình hiện hành của ICTU.
4. Chuẩn mặc định trong tài liệu này.
5. Chuẩn kỹ thuật quốc tế dùng làm tham khảo nội dung.

Khoa CNTT công bố riêng mẫu báo cáo thực tập và hướng dẫn đồ án; ICTU/Khoa
cũng công bố quy trình đồ án/khóa luận theo Quyết định 147 năm 2025. Vì vậy
không được suy ra rằng một cấu hình Word duy nhất áp dụng cho mọi loại hồ sơ.
Xem [trang mẫu quyển báo cáo của Khoa CNTT](https://fit.ictu.edu.vn/nhiem-vu-cua-gvql-truong-doan-va-mau-quyen-bao-cao/)
và [trang Quyết định 147](https://fit.ictu.edu.vn/quyet-dinh-so-147-ban-hanh-quy-trinh-thuc-hien-do-an-khoa-luan-tot-nghiep-nam-2025/).

Các thông số Word ở mục 4 là baseline nội bộ cho báo cáo dự án môn học BAI03
khi giảng viên chưa đưa mẫu riêng, không phải tuyên bố về quy định bắt buộc
của ICTU cho mọi bài.

## 3. Phân loại tài liệu và nguồn sự thật

| Status | Ý nghĩa |
|---|---|
| CANONICAL | Nguồn định danh, yêu cầu hoặc chính sách được ưu tiên |
| IMPLEMENTED | Đã thấy trong mã và/hoặc kiểm thử ở đúng phạm vi được dẫn |
| DERIVED | Được tổng hợp từ nguồn khác, có thể truy ngược |
| PROPOSED | Thiết kế mục tiêu, chưa được chứng minh triển khai |
| OPEN | Chưa chốt hoặc chưa đủ bằng chứng |
| REFERENCE | Tài liệu tham khảo ngoài phạm vi triển khai |
| TEMPLATE | Mẫu/prompt để sử dụng, không phải kết quả runtime |
| LEGACY | Bản cũ, chỉ dùng để đối chiếu lịch sử |

CANONICAL không đồng nghĩa với IMPLEMENTED. PROPOSED không được viết như một
kết quả đã đạt.

| Nội dung | Nguồn chuẩn |
|---|---|
| Yêu cầu, rubric và phạm vi bài | project.md |
| Tên nhóm, thành viên, lớp, trường, khoa | informember.md |
| Hiện trạng code | docs/02-architecture-and-code-status.md và mã nguồn được dẫn trong đó |
| Quy trình/nghiệp vụ | docs/03-business-flows.md |
| Đặc tả AI | docs/04-ai-specification.md |
| Quy tắc tài liệu và bản nộp | Tài liệu này |
| Bản Markdown của báo cáo | submission/Nhom25/Bao_cao_phan_tich_thiet_ke_BAI03.md |
| Bản để nộp/in | DOCX/PDF được kiểm tra đồng bộ với cùng phiên bản báo cáo Markdown |

Không tạo chuỗi final, final2, final_ok làm nguồn sự thật. Khi nội dung thay
đổi, cập nhật version/ngày, render lại DOCX/PDF và ghi kiểm chứng.

## 4. Chuẩn hồ sơ nộp BAI03

### 4.1. Loại tài liệu và độ dài

Đây là báo cáo phân tích và thiết kế dự án môn học, không phải báo cáo thực
tập hoặc đồ án tốt nghiệp.

| Thành phần | Mức phù hợp |
|---|---:|
| Bìa | 1 trang |
| Nội dung chính | Khoảng 25–40 trang khi dự án được trình bày đầy đủ |
| Phụ lục bằng chứng/prompt/code dài | Tách khỏi thân báo cáo |
| Mục lục | Bắt buộc khi tài liệu trên 10 trang |
| Danh mục hình/bảng | Chỉ thêm khi số lượng đủ nhiều để tra cứu |
| Lời cảm ơn, cam đoan, abstract | Không thêm nếu đề bài không yêu cầu |

Báo cáo có thể dài hơn vùng mục tiêu nếu tính phụ lục; điều đó chấp nhận được
khi phụ lục là bằng chứng thật và thân báo cáo không bị kéo dài bởi code hoặc
prompt lặp lại.

### 4.2. Bìa

Bìa dùng một trang, tối giản và có: Đại học Thái Nguyên; Trường Đại học Công
nghệ Thông tin và Truyền thông; Khoa Công nghệ thông tin; tên báo cáo; học
phần; bài kiểm tra; giảng viên; nhóm; sinh viên; mã sinh viên; lớp; địa điểm
và năm.

Không đưa GitHub URL, danh sách công nghệ, prompt dài, ảnh nền, slogan hoặc
abstract lên bìa.

### 4.3. Baseline Word khi chưa có mẫu riêng

| Thuộc tính | Giá trị baseline |
|---|---|
| Khổ giấy | A4, dọc |
| Font thân bài | Times New Roman, 13 pt, Unicode |
| Lề | Trái 3,5 cm; phải 2 cm; trên 2,5 cm; dưới 2,5 cm |
| Đoạn văn | Căn đều; Multiple 1,3; Before 6 pt; After 6 pt |
| Heading | Heading 1/2/3 là Word Styles thật; đánh số nhất quán, không gõ mục lục thủ công |
| Mục lục | Field TOC tự động, cập nhật trước khi xuất |
| Hình/bảng | Caption và ID ổn định; tham chiếu thống nhất |
| Số trang | Giữa, cuối trang; không dùng running header trang trí |
| Trích dẫn | Kiểu số [1], [2] hoặc mã nguồn [SRC-001] theo danh mục tài liệu |

Nếu giảng viên đưa file mẫu khác, file mẫu đó thắng toàn bộ baseline này.

### 4.4. Nội dung tối thiểu

Báo cáo phải trả lời đủ 10 mục của đề:

1. Bài toán quản lý: bối cảnh, người dùng, dữ liệu, quy trình và vấn đề.
2. Yêu cầu chức năng: ID, mô tả, ưu tiên và tiêu chí chấp nhận.
3. Yêu cầu phi chức năng: bảo mật, hiệu năng, khả dụng, sao lưu, quyền và UX.
4. Actor/use case: actor chính, use case chính và mô tả/sơ đồ.
5. Cơ sở dữ liệu: ERD, bảng, PK/FK, ràng buộc và quan hệ.
6. Kiến trúc: frontend, backend, database, RAG, AI provider và luồng dữ liệu.
7. Vị trí AI: chức năng, actor, dữ liệu vào/ra, giới hạn và trạng thái.
8. Prompt: system prompt, user prompt, schema, guardrail, fallback.
9. Minh chứng AI: prompt, nguồn, kiểm chứng và chỉnh sửa; không bịa response.
10. Kế hoạch: giai đoạn, deliverable, rủi ro, cổng nghiệm thu và truy xuất.

## 5. Chuẩn kho tri thức cho AI/RAG

DOCX/PDF phục vụ nộp và đọc; Markdown/YAML phục vụ Git, RAG và tra cứu. Mỗi
tài liệu Markdown mới phải có document_id, document_type, project_id, status và
last_reviewed trong frontmatter.

Nội dung kỹ thuật dùng ID ổn định như FR-001, NFR-001, BR-001, UC-001, AI-001,
EV-001 và PLAN-001. Liên kết phải là đường dẫn tương đối trong repository;
không đưa đường dẫn ổ đĩa cá nhân vào tài liệu.

Document RAG phải giữ source_path, source_type, project_id, document_id, status,
content_hash, chunk_index và section. Citation dùng dạng [n]
source_path#section. GitNexus hỗ trợ hiểu quan hệ code nhưng không thay thế
kiểm thử nghiệp vụ. knowledge_store/ và .gitnexus/ là artifact cục bộ, không
đưa vào gói nộp.

Prompt/response dài để trong prompts/, evidence/ hoặc phụ lục. Thân báo cáo
chỉ giữ mục tiêu, prompt quan trọng, kết quả đã kiểm chứng và kết luận. Nếu
chưa có provider response thật, phải ghi rõ PROPOSED/OPEN.

## 6. Checklist trước khi nộp

- [ ] Đề bài và mẫu hiện hành của giảng viên đã được kiểm tra.
- [ ] Bìa có đúng trường, khoa, học phần, nhóm, thành viên, mã sinh viên, lớp và năm.
- [ ] Không trộn Bài 01, BAOHANHAI hoặc QLBH demo vào BAI03.
- [ ] Mã nguồn, tài liệu và bản nộp dùng cùng một baseline/commit.
- [ ] Heading dùng Styles; mục lục/caption/page number đã cập nhật.
- [ ] Bảng/hình không tràn lề, chữ đọc được, caption có ID.
- [ ] Mỗi yêu cầu quan trọng có ID, nguồn, trạng thái và bằng chứng hoặc được ghi OPEN.
- [ ] Không gọi model-only, schema-only, prompt/template hoặc mục tiêu là tính năng đã hoàn thành.
- [ ] Không có API key, mật khẩu, .env, database local, vector store, cache hoặc path cá nhân.
- [ ] DOCX đã xuất PDF và kiểm tra toàn bộ trang; Markdown là bản nguồn cùng version.
- [ ] README gói nộp nói rõ file chính và giới hạn hiện trạng.

## 7. Lịch sử chuẩn

| Version | Ngày | Thay đổi |
|---|---|---|
| 1.0 | 2026-08-18 | Áp dụng nguyên tắc hai tầng ICTU submission + software-engineering knowledge; bổ sung bìa, độ dài, source-of-truth, RAG và checklist. |
