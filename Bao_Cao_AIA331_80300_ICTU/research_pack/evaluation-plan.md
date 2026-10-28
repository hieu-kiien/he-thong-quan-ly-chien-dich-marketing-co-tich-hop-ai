# Kế hoạch và Kết quả Đánh giá Thực nghiệm (MarketFlow AI)

## 1. Mục tiêu đánh giá

Đánh giá độc lập và có thể tái lập bằng dòng lệnh trên ba phương diện:
1. **Độ tin cậy nghiệp vụ và phân quyền**: Thông qua 151 ca kiểm thử tự động (104 Backend Pytest + 18 AI-Runner Pytest + 29 Playwright E2E).
2. **Chất lượng điều phối công cụ MCP và tuân thủ *Proposal-Only* của AI**: Thông qua bộ đánh giá định lượng `scripts/evaluate_assistant.py` trên 8 kịch bản nghiệp vụ (`scripts/eval_cases.json`: `TC01 content_ideas`..`TC08 proposal_claim_trap`) đối với 4 giai đoạn tối ưu hóa System Prompt (`deploy/opencode/prompts/`).
3. **Định cỡ tài nguyên và khả năng chịu lỗi**: Thông qua khảo sát thực nghiệm P0 Spike trên máy chủ mục tiêu và kiểm thử tiêm lỗi đa mô hình.

## 2. Kết quả đánh giá 4 giai đoạn tối ưu hóa System Prompt

Lệnh tái lập:
```bash
python scripts/evaluate_assistant.py --all-versions --transcripts docs/eval/transcripts.json
```

| Giai đoạn Prompt | Đặc điểm chỉ dẫn | Số kịch bản Đạt | Tỷ lệ Pass | Ghi chú phân tích thực nghiệm |
|---|---|---|---|---|
| **Bản 1 (Cơ sở)** | Baseline cơ bản | 6 / 8 | **75.0%** | Trượt `TC03` (TikTok dài 3650 ký tự > 1500) và `TC05` (tự bịa thêm số liệu giả định ngoài ngữ cảnh). |
| **Bản 2 (Rào chắn)** | Bổ sung Guardrails & Grounding | 5 / 8 | **62.5%** | Hiện tượng *Disclaimer Bloat* làm cả `TC02` (2082 ký tự) và `TC03` (3306 ký tự) vượt giới hạn độ dài; trượt `TC05`. |
| **Bản 3 (Chuẩn KPI)** | Chuẩn hóa KPI & quy chuẩn kênh | 6 / 8 | **75.0%** | Vượt qua `TC05` (Grounding 1.0); còn vượt độ dài ở `TC02` (2467 ký tự) và `TC03` (2789 ký tự). |
| **Bản 4 (Production)** | Khóa độ dài kênh & bỏ disclaimer thừa | **7 / 8** | **87.5%** | Đạt `TC01, TC02, TC03, TC04, TC06, TC07, TC08`; chỉ trượt nhẹ `TC05` do đưa thêm 1 số ví dụ giả định (`1.212`). |

## 3. Kết quả kiểm thử tự động toàn hệ thống (151 ca kiểm thử)

| Tầng kiểm thử | Công cụ | Số tệp test | Số ca kiểm thử | Kết quả |
|---|---|---|---|---|
| Backend API & FastMCP | `pytest` | 16 tệp (`backend/tests/`) | 104 ca | **104 / 104 Pass (100%)** |
| AI Runner Service | `pytest` | 2 tệp (`ai-runner/tests/`) | 18 ca | **18 / 18 Pass (100%)** |
| Frontend E2E Browser | `Playwright` | 9 tệp (`frontend/tests/e2e/`) | 29 ca | **29 / 29 Pass (100%)** |
| **Tổng cộng** | | **27 tệp** | **151 ca** | **151 / 151 Pass (100%)** |
