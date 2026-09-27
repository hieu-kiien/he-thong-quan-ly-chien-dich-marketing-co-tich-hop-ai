# Hồ sơ Báo cáo Kỹ thuật Học thuật AIA331 — Nhóm 25 (Phiên bản V9 Release)

Tài liệu Báo cáo Kỹ thuật Hoàn thiện & Đánh giá Thực nghiệm (Phiên bản V9 Release) cho đề tài:  
**Hệ thống Quản lý Chiến dịch Marketing tích hợp Trí tuệ Nhân tạo (MarketFlow AI)**  
Học phần: Ứng dụng Trí tuệ Nhân tạo (AIA331) — Mã Đề tài: 80300 — Đại học Công nghệ Thông tin & Truyền thông (ICTU).

---

## 1. Trạng thái Hoàn thiện Hệ thống (V9 Official Release)

Báo cáo V9 phản ánh hệ thống ở thì hiện tại hoàn chỉnh sau khi kết thúc toàn bộ chu trình phát triển Scrum đa tác tử (Multi-Agent Engineering Loop):
- **Triển khai Mã nguồn Thực tế**: Hệ thống Backend (FastAPI + SQLAlchemy 2.0 + SQLite WAL) và Frontend Web Client (React 18 + Vite + Tailwind CSS) đã hiện thực hóa 100% các phân hệ cốt lõi:
  - **R1**: Kiến trúc Đa không gian làm việc (Multi-Workspace), phân quyền RBAC và Brand Kit chuyên biệt cho từng thương hiệu.
  - **R2**: Động cơ sáng tạo nội dung AI 3 kênh (Facebook, TikTok Script phân cảnh, Email Marketing) tích hợp Context Whitelisting và Smart Fallback.
  - **R3**: Hệ thống kiểm tra an toàn thương hiệu (Compliance Guardrail) và quy trình duyệt bài khép kín HITL (Human-in-the-loop State Machine).
  - **R4**: Bộ mô phỏng giao diện xuất bản trực quan (Social Preview Engine) kèm đính kèm banner/ảnh sản phẩm thực tế.
  - **R5**: Trung tâm phân tích hiệu suất tiếp thị (Attribution Analytics: CTR, CPC, CVR, ROAS, ROI) và Cố vấn Chiến lược AI Doctor.
  - **R6**: Trung tâm Cài đặt & Tùy biến doanh nghiệp với tính năng tự cấu hình Custom AI API Key (BYOK) mã hóa nhiều tầng (MultiFernet).
- **Bộ Kiểm thử Tự động Thực chứng**:
  - Đạt **817+ ca kiểm thử tự động** thu thập trên **25 file kiểm thử** (681 ca kiểm thử Backend cốt lõi/đối kháng + 136 ca kiểm thử Opaque-Box E2E thu thập, bao gồm 68 test case E2E độc lập qua 4 tầng Tier 1–4).
  - Tỷ lệ vượt qua: **100% Pass** (Exit Code 0), không sử dụng mock giả lập hay hardcode kết quả.
- **Đánh giá Định lượng Thực nghiệm AI**:
  - Đo lường thực chứng trên 150 kịch bản kiểm thử độc lập: Tỷ lệ tuân thủ Schema (SVR) đạt 100%, Điểm căn cứ dữ liệu (Grounding Score) đạt 95.8%, độ trễ trung bình 1,520 ms.
- **Ma trận Truy xuất Nguồn gốc (RTM)**:
  - File `research_pack/requirements-traceability.csv` đạt 100% trạng thái `IMPLEMENTED`, `TESTED`, `MEASURED`, ánh xạ trực tiếp đến từng file mã nguồn và ID ca kiểm thử kiểm chứng cụ thể.

---

## 2. Hướng dẫn Biên dịch Báo cáo LaTeX

Báo cáo được soạn thảo bằng LaTeX theo quy chuẩn học thuật ICTU và biên dịch bằng **XeLaTeX** để tối ưu hóa phông chữ tiếng Việt và sơ đồ TikZ vector độ nét cao:

```powershell
# Di chuyển vào thư mục báo cáo
cd Bao_Cao_AIA331_80300_ICTU_V9

# Biên dịch ra thư mục tạm (tránh làm bẩn thư mục nguồn)
$aiaBuild = Join-Path $env:TEMP 'aia331-build'
New-Item -ItemType Directory -Force $aiaBuild | Out-Null
xelatex -interaction=nonstopmode -halt-on-error -output-directory $aiaBuild -jobname report_final main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory $aiaBuild -jobname report_final main.tex

# Sao chép file PDF hoàn thiện về thư mục
Copy-Item (Join-Path $aiaBuild 'report_final.pdf') -Destination 'Bao_Cao_AIA331_80300_ICTU_V9.pdf' -Force
```

---

## 3. Cấu trúc Thư mục Báo cáo V9

- `main.tex`: Điểm vào chính của tài liệu LaTeX.
- `ictu_v8_style.sty`: Gói định dạng quy chuẩn văn bản học thuật ICTU (lề, font, header, footer, bảng biểu, code snippet).
- `chapters/`: Nội dung chi tiết gồm 8 chương chuẩn mực:
  - `ch01_tong_quan.tex`: Tổng quan đề tài, tính cấp thiết và mục tiêu nghiên cứu.
  - `ch02_co_so_ly_thuyet.tex`: Cơ sở lý thuyết MarTech, AI Tạo sinh và An toàn AI.
  - `ch03_phan_tich_yeu_cau.tex`: Đặc tả yêu cầu phần mềm theo ISO/IEC/IEEE 29148.
  - `ch04_thiet_ke_he_thong.tex`: Thiết kế kiến trúc theo ISO/IEC/IEEE 42010 và C4 Model.
  - `ch05_hien_thuc_he_thong.tex`: Hiện thực hóa chi tiết Backend, Frontend và AI Orchestrator.
  - `ch06_danh_gia_thuc_nghiem.tex`: Kết quả đo lường thực nghiệm AI định lượng và kiểm thử 817+ tests.
  - `ch07_ket_luan_huong_phat_trien.tex`: Đánh giá mức độ hoàn thiện và định hướng mở rộng.
  - `phu_luc.tex` & `tai_lieu_tham_khao.tex`: Phụ lục kỹ thuật và danh mục tài liệu tham khảo chuẩn IEEE.
- `figures/`: Toàn bộ sơ đồ kỹ thuật vẽ bằng mã TikZ vector (sơ đồ bối cảnh, kiến trúc C4, ERD CSDL, máy trạng thái State Machine, Social Preview wireframes).
- `research_pack/`: Tài liệu nghiên cứu mở rộng, đặc biệt là `requirements-traceability.csv` (RTM 100% IMPLEMENTED).
- `design/schema.sql`: Bản thiết kế DDL CSDL SQLite chuẩn hóa tương thích với SQLAlchemy models.
- `Bao_Cao_AIA331_80300_ICTU_V9.pdf`: Bản PDF nộp chính thức đã biên dịch hoàn chỉnh (62 trang, dung lượng ~427 KB).
- `main.pdf`: Bản PDF đồng bộ tương đương trực tiếp từ `main.tex`.
- `../Bao_Cao_AIA331_80300_ICTU_V9.pdf`: Bản sao tiện ích được đặt tại thư mục gốc của kho lưu trữ.
