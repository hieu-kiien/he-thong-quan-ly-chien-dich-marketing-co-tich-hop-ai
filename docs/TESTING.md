# Kiểm thử, CI và cách đọc kết quả

Đây là hướng dẫn kiểm thử hiện hành. Workflow trong [.github/workflows/ci.yml](../.github/workflows/ci.yml) là nguồn chuẩn cho lệnh, môi trường và điều kiện pass/fail; các báo cáo test cũ ở root được giữ làm lịch sử.

## Trạng thái baseline

- Repo baseline: `b99ac876a06993edfb5a88d866c22080434e7372`.
- [GitHub Actions run tại baseline](https://github.com/hieu-kiien/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/actions/runs/36537065686) hoàn tất thành công với 6 gate CI và bước Docker verification.
- Bộ số liệu trong commit `6627de4`, được tài liệu hóa tại `b99ac87`: 1.262 backend tests pass, 1 test skip do CI không có live DB bị gitignore; coverage 86.20%; E2E 38/38 mock và 7/7 live; WCAG 25/25. Đây là kết quả của lần chạy đó, không phải số đếm bất biến cho các commit sau.
- Gate 6 hiện báo advisory của npm/pip dưới dạng warning; workflow chưa chặn merge chỉ vì các advisory này. Xem phần Security/dependency bên dưới.

## Các gate trong CI

| Gate | Phạm vi | Lệnh/điều kiện chính |
|---|---|---|
| 1 — Backend | Pytest, timeout, coverage | `pytest backend/tests/ -v --timeout=180 --timeout-method=thread --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=80` |
| 2 — Frontend | TypeScript và production build | `npm ci`, sau đó `npm run build` trong `frontend/`. |
| 3 — Playwright | E2E mock/live và tương tác | Mock business journeys; backend thật + SQLite; interaction probes. |
| 4 — WCAG | Accessibility với backend chạy | Playwright WCAG 2.2 AA; CI yêu cầu test không có vi phạm mức được cấu hình. |
| 5 — Performance/AI | API latency và benchmark AI | `scripts/measure_api_latency.py` và `scripts/evaluate_ai_grounding.py`. |
| 6 — Secrets/dependencies | Gitleaks, pip-audit, npm audit | Gitleaks chặn theo kết quả scan; pip/npm audit hiện chỉ ghi warning khi có advisory. |
| Docker | Build và compose verification | Chạy sau khi sáu gate phía trên thành công. |

Tên gate có chữ “security” hoặc “100%” trong workflow không thay cho việc đọc log thực tế. Luôn kiểm tra warning, skip, artifact và commit của run.

## Chạy cục bộ

### Backend

Tại thư mục gốc repo, cài dependencies backend và công cụ coverage/timeout như workflow, rồi chạy lệnh Gate 1 ở bảng trên. Khi kết quả local khác CI, đối chiếu biến môi trường, phiên bản Python và database setup tại workflow trước khi so sánh.

### Frontend build

```powershell
cd frontend
npm ci
npm run build
```

### Playwright

Chạy từ `frontend/` với dependencies và Chromium đã cài. CI là cách tái lập đầy đủ cả chế độ mock và live; chế độ live cần backend/SQLite test fixture thực sự chạy và không được trỏ vào database cá nhân.

```powershell
cd frontend
npx playwright install chromium
npx playwright test tests/e2e --reporter=list
```

Để chạy a11y, probes, benchmark và Docker đúng môi trường, lấy lệnh cùng working directory từ workflow. Không chạy live test trên database production.

## Cách hiểu benchmark AI

- Báo cáo [AI_EVALUATION_REPORT.md](AI_EVALUATION_REPORT.md) được sinh bởi `scripts/evaluate_ai_grounding.py` trong Gate 5. Khi thay nội dung báo cáo, cập nhật generator và artifact cùng nhau.
- Schema adherence được tính trên bộ mẫu cố định; grounding dùng các tình huống được mã hóa trong script; failover có số tình huống giới hạn.
- Độ trễ AI Doctor đo đường chẩn đoán xác định trên SQLite cô lập, không phải latency mạng/LLM Gemini và không đại diện tải production.
- 0 vi phạm trong benchmark nghĩa là 0 vi phạm trong đúng các case đã chạy. Không suy ra rằng mọi nội dung sinh từ mọi model/provider đều không thể ảo giác.
- Benchmark không đo thời gian tiết kiệm, độ hữu ích với agency, conversion marketing hay sự hài lòng của người duyệt. Các giả thuyết đó cần pilot riêng.

## Cách báo cáo kết quả mới

Mỗi kết quả mới cần ghi:

1. Commit SHA và URL CI run.
2. Môi trường/runtime, database và cấu hình liên quan; tuyệt đối không ghi secret.
3. Số lượng test chạy, pass, fail, skip và lý do skip.
4. Coverage/latency kèm workload, số lượt đo, percentile và giới hạn áp dụng.
5. Advisory, warning, retry và artifact cần người đọc xem.
6. Kết luận đúng phạm vi đã đo; tách riêng kết quả kỹ thuật và kết quả người dùng.

Không sao chép số liệu volatile sang README, kiến trúc và release notes cùng lúc. Ghi link run ở đây hoặc trong báo cáo benchmark có timestamp.

## Dependency advisory đang mở

Gate 6 dùng `|| echo` sau `pip-audit` và `npm audit`, nên run có thể xanh dù công cụ tìm thấy advisory. Đây là hạng mục cần phân loại theo package, mức độ và đường sử dụng; đặt owner/ngày xử lý hoặc waiver có hạn. Không ghi “không có lỗ hổng” chỉ dựa trên trạng thái xanh của run hiện tại.

## Hồ sơ lịch sử

- [TEST_READY.md](../TEST_READY.md) là snapshot readiness ngày 2026-09-27; số liệu không đồng bộ baseline hiện hành.
- [TEST_INFRA.md](../TEST_INFRA.md) là thiết kế hạ tầng test cũ; workflow hiện tại đã thay đổi.
- Run/commit mới hơn thay thế các con số trong snapshot lịch sử; không xóa các file này để giữ dấu vết quyết định.
