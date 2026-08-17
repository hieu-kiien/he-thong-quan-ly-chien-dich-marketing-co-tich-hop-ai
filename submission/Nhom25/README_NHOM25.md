# Nộp bài — Nhóm 25

**Đề tài:** Hệ thống quản lý bán hàng có tích hợp AI  
**Mã dự án:** `BAI03-SALES-AI`  
**Thành viên:** Nguyễn Hải Đăng; Vũ Hiếu Kiên  
**Mã sinh viên:** dtc2451200051; dtc245200244  
**Lớp:** CNTTK23C

## Danh mục file

- `Bao_cao_phan_tich_thiet_ke_BAI03.docx`: báo cáo Word chính.
- `Bao_cao_phan_tich_thiet_ke_BAI03.pdf`: bản PDF để xem/in.
- `Bao_cao_phan_tich_thiet_ke_BAI03.md`: nguồn Markdown có thể tra cứu trên GitHub.
- `Phu_luc_minh_chung_AI.md`: prompt, kiểm chứng RAG/GitNexus, test output và giới hạn bằng chứng.
- `diagrams/`: ba hình PNG được dựng từ thiết kế; source Mermaid nằm trong báo cáo.

## Phạm vi và tính trung thực học thuật

Báo cáo chọn `sales_management/` làm baseline phân tích hiện trạng. Những phần mới chỉ có model/schema/retrieval hoặc thiết kế tương lai đều được ghi qualifier; provider LLM, AI nghiệp vụ end-to-end, RBAC đầy đủ và luồng bán–tồn hoàn chỉnh chưa được tuyên bố đã triển khai.

Thư mục này không chứa secret, `.env`, database local, vector store, cache hay chỉ mục GitNexus. Các artifact trên máy phát triển có thể tái sinh theo hướng dẫn trong repo.
