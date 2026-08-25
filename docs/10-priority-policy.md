---
document_id: AIA331-DOC-10
document_type: priority-policy
project_id: AIA331-80300-MARKETING-AI
status: CANONICAL_DERIVED
last_reviewed: 2026-08-18
---

# Chính sách ưu tiên và bản đồ phạm vi

## 1. Nguyên tắc cốt lõi

Chỉ hai ảnh nguồn do người dùng cung cấp là `P0 / CRITICAL`. Các tài liệu còn
lại được phân cấp theo vai trò của chúng; không gắn `P0` cho mọi tài liệu chỉ
vì chúng thuộc cùng một dự án.

`P0` là mức ưu tiên nội bộ để quản lý source-of-truth, không phải điểm số hay
một yêu cầu mới của giảng viên.

## 2. Phân cấp hiện tại

| Mức | Ý nghĩa | Phạm vi hiện tại | Cách xử lý |
|---|---|---|---|
| `P0 / CRITICAL` | Nguồn ràng buộc cao nhất | `source-materials/BÀI KIỂM TRA.png`; `source-materials/DỰ ÁN.png` | Đọc trước; không chỉnh nội dung; dùng để phân xử xung đột |
| `P1 / HIGH` | Phải hoàn thành/đối chiếu để làm và nộp bài | `project.md`, `informember.md`, `docs/00`–`docs/05`, `docs/09`, `docs/11`, `docs/99`, code baseline, tests, RAG manifest/tool, `submission/Nhom25/` | Ưu tiên triển khai, kiểm thử và kiểm tra hồ sơ |
| `P2 / MEDIUM` | Tài liệu hỗ trợ thực hiện | `docs/06`–`docs/08`, `docs/reference/`, prompts, `archive/reference/` | Dùng để thiết kế/tra cứu; không được override P0/P1 |
| `P3 / LOW` | Tài liệu tham khảo không ảnh hưởng phạm vi hiện tại | bài tập thử nghiệm, notebook, PDF tham khảo không thuộc đề tài | Chỉ mở khi cần; không đưa vào source-of-truth |
| `LEGACY` | Lịch sử của đề tài khác | `archive/legacy/`, `docs/legacy/` | Giữ nguyên để bảo toàn lịch sử; loại khỏi truy hồi canonical |

`LEGACY` là trạng thái loại khỏi phạm vi, không phải một yêu cầu cần làm.

## 3. Bản đồ thư mục

| Khu vực | Vai trò | Mức ưu tiên |
|---|---|---|
| `source-materials/` | Hai nguồn gốc và chỉ mục nguồn | P0 |
| `project.md`, `informember.md` | Brief và thông tin nhóm | P1 |
| `docs/` | Tài liệu phân tích, thiết kế, checklist và quy tắc tra cứu | P1/P2 tùy file |
| `marketing_management/` | Baseline Django đang được dùng | P1 |
| `prompts/marketing/` | Prompt theo đề tài marketing | P2; prompt chưa triển khai ghi `PROPOSED` |
| `submission/Nhom25/` | Hồ sơ nộp và bản sao nguồn | P1 |
| `tools/` | Script sinh/kiểm tra artifact | P1 nếu dùng cho hồ sơ hiện tại |
| `archive/reference/` | Tài liệu học tập/tham khảo | P2/P3 |
| `archive/legacy/` | Artifact đề tài bán hàng cũ | LEGACY |

## 4. Quy tắc khi có tài liệu mới

1. Không ghi đè hai ảnh P0 hoặc bản gốc của giảng viên.
2. Thêm nguồn mới với ngày nhận, trạng thái và vai trò trong
   `docs/99-source-register.md`.
3. Nếu là hướng dẫn mới nhất của giảng viên, ghi rõ nó thay thế nguồn cũ ở
   `docs/06-open-questions.md` và cập nhật `docs/manifest.yaml`.
4. Tài liệu biên tập phải ghi nguồn; không biến `DERIVED`, `PROPOSED` hoặc
   `OPEN` thành bằng chứng đã hoàn thành.

## 5. Cách tra cứu nhanh

- Xác định tên đề tài và nguồn ràng buộc: đọc hai ảnh trong `source-materials/`.
- Xác định yêu cầu/chức năng: đọc `project.md` và `docs/01-requirements-summary.md`.
- Xác định thiếu gì để nộp: đọc `docs/09-assessment-checklist.md` và
  `docs/05-deliverables-and-validation.md`.
- Xác định code đã chạy được đến đâu: đọc `docs/02-architecture-and-code-status.md`,
  sau đó kiểm tra `marketing_management/` và tests.
- Tra cứu tài liệu có citation: chạy `python tools/rag_index.py validate`, rồi
  `build` và `search`; không dùng database `.rag/` làm file nộp.
- Không dùng thư mục `LEGACY` để suy ra yêu cầu marketing.
