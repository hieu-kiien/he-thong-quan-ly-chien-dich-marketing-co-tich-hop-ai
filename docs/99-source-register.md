---
document_id: AIA331-SOURCE-REGISTER
document_type: source-register
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: CANONICAL_DERIVED
last_reviewed: 2026-08-19
---

# Sổ đăng ký nguồn

| Source ID | Nguồn | Authority | Dùng cho |
|---|---|---|---|
| SRC-000 | `source-materials/BÀI KIỂM TRA.png` / ảnh bài kiểm tra người dùng cung cấp | P0 / CRITICAL | 10 tiêu chí đánh giá, nội dung bắt buộc của báo cáo |
| SRC-001 | `source-materials/DỰ ÁN.png` / ảnh đề bài người dùng cung cấp | P0 / CRITICAL | tên đề tài, AIA331, 80300, requirements |
| SRC-002 | `project.md`, `informember.md` | P1 / HIGH | yêu cầu đã biên tập có truy vết và định danh nhóm |
| SRC-003 | `docs/09-assessment-checklist.md` | P1 / HIGH | checklist biên tập từ SRC-000 |
| SRC-004 | `marketing_management/` và tests | P1 / HIGH | baseline đã triển khai và bằng chứng chạy |
| SRC-005 | `docs/*.md`, `prompts/marketing/` | P2 / MEDIUM | tài liệu thiết kế, hướng dẫn và prompt hỗ trợ |
| SRC-006 | `Slide_PDF/`, PDF/notebook học tập | P2/P3 | tài liệu tham khảo, không override nguồn canonical |
| SRC-007 | Google Classroom screenshots/user notes | REFERENCE_TO_CANONICAL | quy cách thư mục ZIP, mốc nộp |
| SRC-008 | `Code QLBH/`, `sales_management/`, báo cáo bán hàng | LEGACY | lịch sử; không dùng làm yêu cầu marketing |
| SRC-009 | `docs/rag-corpus.json`, `tools/rag_index.py`, `tools/test_rag_index.py` | P1 / HIGH | manifest, truy hồi có citation và kiểm thử chống nhiễm legacy |
| SRC-010 | `evidence/ai/` | P1 / HIGH | phản hồi AI đã khử dữ liệu, kiểm chứng schema và chỉnh sửa của sinh viên |
| SRC-011 | [Template format ICTU công khai](https://repository.ictu.edu.vn/cam-nang-so/huong-dan-format-quyen-khoa-luan-tot-nghiep/) | REFERENCE | tham chiếu logo/bố cục bìa; không khẳng định là mẫu bắt buộc của bài kiểm tra |

## Quy tắc nguồn

Nếu nội dung từ nguồn legacy khác một trong hai đề bài ảnh, chọn `SRC-000` hoặc
`SRC-001` tương ứng và ghi xung đột. Hai nguồn P0 / CRITICAL luôn được ưu tiên
trước tài liệu diễn giải.
Không dùng đường dẫn ổ đĩa cá nhân trong báo cáo phát hành; chỉ dùng path tương
đối trong repo.
