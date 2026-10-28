# Research Pack — Báo cáo Học thuật AIA331 (Đề tài 80300 — MarketFlow AI)

Đây là bộ hồ sơ truy vết học thuật và bằng chứng thực nghiệm đi kèm báo cáo chính thức `Bao_Cao_AIA331_80300_ICTU.pdf`, đã được đồng bộ 100% với kiến trúc hệ thống đang vận hành thực tế.

## Nội dung hồ sơ

- `project-research-plan.md`: Câu hỏi nghiên cứu, phạm vi kiến trúc hệ thống (14 bảng, `ai-runner` + FastMCP `/mcp`) và kết quả nghiệm thu.
- `source-inventory.csv`: Danh mục nguồn tiêu chuẩn và tài liệu kỹ thuật được sử dụng.
- `evidence-ledger.csv`: Sổ cái truy vết các tuyên bố kỹ thuật (claims), tệp bằng chứng thực tế và trạng thái kiểm chứng (`TESTED` / `MEASURED`).
- `related-work-matrix.csv`: Đối sánh tài liệu tham khảo và các nền tảng quản trị chiến dịch.
- `requirements-traceability.csv`: Ma trận truy xuất nguồn gốc (RTM) ánh xạ 14 yêu cầu chức năng (`FR01`–`FR14`) và 6 yêu cầu phi chức năng (`NFR01`–`NFR06`) tới mã nguồn và 151 ca kiểm thử tự động.
- `quality-attribute-scenarios.csv`: Kịch bản thuộc tính chất lượng theo chuẩn ISO/IEC 25010.
- `evaluation-plan.md`: Phương pháp và kết quả đánh giá định lượng 4 giai đoạn tối ưu hóa System Prompt trên 8 kịch bản (`scripts/evaluate_assistant.py`).
- `visual-coverage-map.csv`: Ánh xạ mục đích và tệp nguồn TikZ của 10 sơ đồ kiến trúc/ERD/luồng dữ liệu.
- `reproducibility-manifest.yaml`: Thông số môi trường, phiên bản mô hình, tập dữ liệu seed và các lệnh chạy kiểm chứng tái lập.

Nguồn tài liệu kỹ thuật đối chiếu trực tiếp: [`docs/REQUIREMENTS_AND_DESIGN.md`](../../docs/REQUIREMENTS_AND_DESIGN.md), [`docs/TESTING.md`](../../docs/TESTING.md), [`docs/AI_ASSISTANT.md`](../../docs/AI_ASSISTANT.md), [`docs/AI_ETHICS_AND_PRIVACY.md`](../../docs/AI_ETHICS_AND_PRIVACY.md), [`docs/AI_IN_SDLC.md`](../../docs/AI_IN_SDLC.md), [`docs/DEPLOYMENT-VPS.md`](../../docs/DEPLOYMENT-VPS.md).
