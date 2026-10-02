# Báo cáo benchmark AI (được sinh tự động)

> Báo cáo này được sinh bởi [scripts/evaluate_ai_grounding.py](../scripts/evaluate_ai_grounding.py) trong Gate 5 của [workflow CI](../.github/workflows/ci.yml). Khi thay đổi nội dung, cập nhật generator và artifact cùng nhau.

**Hệ thống:** MarketFlow AI
**Thời điểm chạy:** 2026-09-29 12:37:52
**Môi trường:** GitHub Actions, SQLite cô lập
**Phạm vi kết luận:** benchmark kỹ thuật tự động trên các case được ghi dưới đây. Không đo giá trị kinh doanh, usability, conversion thực tế hoặc chất lượng mọi lần gọi model.

## 1. Tóm tắt kết quả

| Chỉ số | Tập đo | Kết quả | Cách diễn giải |
|---|---:|---:|---|
| Tuân thủ schema | 60 mẫu cố định trên 4 tác vụ | 100.00% | Các mẫu trong suite đạt schema. |
| Vi phạm grounding | 40 case cố định | 0.00% (0/40) | Không quan sát vi phạm trong các case này; không phải tỷ lệ tổng quát ngoài suite. |
| Failover | Các tình huống được định nghĩa trong script | 100.00% | Kết quả có phạm vi của các nhánh failover đã kiểm tra. |
| Latency AI Doctor xác định | 50 lượt trên SQLite cô lập | p95 = 3.36 ms | Không phải latency LLM/provider qua mạng hoặc tải production. |

## 2. Phương pháp và giới hạn

### 2.1 Schema

Script kiểm tra mẫu cho các hợp đồng dữ liệu idea, draft, summary và nội dung đa kênh. Tỷ lệ 100% là tỷ lệ mẫu trong bộ kiểm tra hợp lệ với schema. Nó không chứng minh nội dung hữu ích, đúng sự thật, phù hợp thương hiệu hoặc không có lỗi ở mọi đầu vào khác.

### 2.2 Grounding và dữ liệu thưa

Các case được mã hóa kiểm tra hành vi chẩn đoán khi có metrics và khi thiếu metrics. Trong suite hiện tại, 0/40 case bị đánh dấu vi phạm. Suite không chứng minh mọi nhận định ở mọi đầu vào/provider luôn được grounding chính xác; đầu ra ngoài các case, model/provider mới và dữ liệu vận hành vẫn cần người kiểm tra.

### 2.3 Failover

Tỷ lệ failover được tính từ các trường hợp provider/fallback do script mô phỏng. Mẫu số nhỏ và không đại diện mọi timeout, quota, lỗi mạng hoặc lỗi dịch vụ có thể xảy ra.

### 2.4 Latency

Độ trễ 3.36 ms là p95 của đường chẩn đoán xác định chạy trong process trên database SQLite cô lập trong 50 lượt. Đây không phải end-to-end response time, thời gian gọi Gemini/OpenAI, throughput nhiều tenant hoặc SLA production.

## 3. Kết luận

Benchmark này hỗ trợ nhận định rằng các trường hợp đã mã hóa hoạt động như kỳ vọng trong môi trường thử nghiệm nêu trên. Nó không chứng minh rằng MarketFlow đã sẵn sàng production, AI luôn đúng, hoặc agency tiết kiệm thời gian/tăng doanh thu.

Để chứng minh các kết luận rộng hơn, cần:
- mở rộng test case và kiểm tra chất lượng bằng rubric có người đánh giá;
- đo các lỗi provider, retry và webhook trong staging;
- chạy pilot với người dùng agency, có baseline và chỉ số hoàn thành công việc;
- ghi commit SHA, môi trường và mẫu số cho từng lần đo mới.
