# MarketFlow AI

Ứng dụng mẫu quản lý chiến dịch marketing có tích hợp AI. Phạm vi hiện tại tập trung vào workspace, campaign, tác vụ, ngân sách/KPI mục tiêu, tạo nội dung và quy trình phê duyệt.

> **Trạng thái:** prototype đang được phát triển. Lịch có thể đổi trạng thái nội bộ sang PUBLISHED; hiện chưa gửi bài thật lên mạng xã hội hoặc gửi email qua provider. Xem [lộ trình](docs/ROADMAP.md) và [kiến trúc hiện tại](docs/ARCHITECTURE.md).

## Triển khai ở đâu

| Tầng | Chạy ở đâu | Vai trò |
|---|---|---|
| Tên miền & TLS | Cloudflare — `marketing.kienhieu.id.vn` | DNS, HTTPS, đẩy traffic qua Tunnel |
| Frontend (static) + nginx | VPS `/var/www/marketflow` | Phục vụ file tĩnh, proxy `/api/*` |
| Backend FastAPI | VPS systemd (`marketflow-api`) | Toàn bộ nghiệp vụ, 2 Uvicorn worker |
| Database | PostgreSQL 16 trên cùng VPS | Mọi trạng thái nghiệp vụ, nghe loopback |

Toàn bộ ứng dụng nằm trên **một** máy. Cloudflare không còn chạy mã ứng dụng —
Worker và Pages đã bị gỡ ngày 2026-10-09, cùng Render và Neon. Không còn đường gọi AI
riêng: mọi request đi cùng một origin, nên không còn giới hạn ~100 giây của Cloudflare
lẫn việc lộ URL backend trong JavaScript. Lời gọi AI dài đã chuyển sang hàng đợi
PostgreSQL trả job ID ngay. Chi tiết ở [docs/DEPLOYMENT-VPS.md](docs/DEPLOYMENT-VPS.md).

SQLite chỉ dùng ở local và CI. Production dùng PostgreSQL; sao lưu chạy 03:00 hằng
ngày và đã được thử khôi phục thật.

## Dự án giúp ai làm việc gì?

- Quản lý agency xem chiến dịch cần chú ý, công việc bị chặn, deadline, ngân sách và KPI mục tiêu.
- Marketer nhận brief, giao/hoàn tất tác vụ và gửi nội dung vào quy trình duyệt.
- Người duyệt kiểm tra nội dung trước khi team đánh dấu trạng thái tiếp theo.

AI hỗ trợ tạo nháp và phân tích dữ liệu có sẵn. Người dùng vẫn chịu trách nhiệm duyệt nội dung và quyết định hành động.

## Bắt đầu nhanh

### Chạy backend

Yêu cầu Python 3.12 hoặc phiên bản tương thích với CI. Từ thư mục gốc repo:

    cd backend
    pip install -r requirements.txt
    python seed/seed_data.py
    python -m uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/docs

### Chạy frontend

Mở terminal thứ hai tại thư mục gốc:

    cd frontend
    npm ci
    npm run dev

Giao diện: http://localhost:5173

### Chạy bằng Docker Compose

Tại thư mục gốc:

    docker compose up -d --build

Giao diện local: http://localhost:3000

### Triển khai native trên VPS

VPS production chạy PostgreSQL, FastAPI, Nginx và Cloudflare Tunnel dưới các
dịch vụ hệ thống. Kế hoạch cấu hình, giới hạn tài nguyên và quy trình chuyển dữ
liệu nằm trong [docs/DEPLOYMENT-VPS.md](docs/DEPLOYMENT-VPS.md).

Seed data dành cho local/demo. Không dùng database, mật khẩu mặc định hoặc secret của môi trường thật cho demo công khai hay production. Không ghi credential vào tài liệu hoặc commit.

Trên production, scheduler chạy trong tiến trình API với `SCHEDULER_ENABLED=true`.
Không còn cron của Worker: Worker đã bị gỡ.

## Kiểm tra chất lượng

Workflow canonical nằm tại [.github/workflows/ci.yml](.github/workflows/ci.yml) với 8 gate: lint, typecheck, unit test, E2E, Docker build, dependency audit, secret scan và rubric check. Xem tab Actions trên `main` để lấy run gần nhất — số CI được ghi ở link sẽ lỗi thời sau vài tuần. Gate dependency vẫn ghi advisory thành warning; cần đọc log trước khi kết luận tình trạng bảo mật.

Xem [docs/TESTING.md](docs/TESTING.md) để chạy test và hiểu giới hạn các số liệu. Không xem benchmark trên tập test hữu hạn là bằng chứng về giá trị kinh doanh hoặc cam kết AI không thể sai.

## Cấu trúc chính

- frontend/: React + Vite client.
- backend/: FastAPI, SQLAlchemy và API nghiệp vụ.
- scripts/: công cụ benchmark; một số script sinh báo cáo vào docs/.
- docs/: kiến trúc, roadmap, kiểm thử, đánh giá AI và tài liệu đồ án.
- Bao_Cao_AIA331_80300_ICTU_V8/ và Bao_Cao_AIA331_80300_ICTU_V9/: source/PDF báo cáo học thuật theo phiên bản.
- cloudflare/: Worker static + proxy; xem [cloudflare/README.md](cloudflare/README.md) trước khi dùng dữ liệu thật.

## Cổng chất lượng (quality gate) của frontend

Chạy trước khi commit — cùng bộ lệnh mà CI chạy:

```bash
cd frontend
npm run typecheck   # tsc --noEmit, strict + noUnusedLocals
npm run lint        # ESLint, chặn cả warning (react-hooks + jsx-a11y)
npm run build
```

`npm run lint` dùng `--max-warnings=0`: mọi cảnh báo đều phải được xử lý,
không bỏ qua. Có một ngoại lệ có chủ đích (`WorkflowCanvas` chỉ nạp brief khi
đổi chiến dịch) được ghi rõ lý do ngay tại dòng `eslint-disable`.

## Biến môi trường đáng chú ý

Ngoài `.env.example`, ba biến sau ảnh hưởng trực tiếp tới an toàn dữ liệu:

| Biến | Mặc định | Vì sao quan trọng |
| --- | --- | --- |
| `SCHEDULER_ENABLED` | `true` | Scheduler trong tiến trình backend ghi thẳng vào database ngoài HTTP path, nên lịch đăng do Cron Trigger của Worker điều phối (mỗi 5 phút). Bật cả hai cùng lúc sẽ chạy trùng job. |
| `SCHEDULER_SECRET` | *(rỗng)* | Dùng Worker gọi `POST /api/v1/schedules/trigger-worker`. Rỗng thì đường gọi bằng secret tắt, endpoint chỉ nhận Bearer token. **Trên Cloudflare đây là secret bắt buộc** (`secrets.required` trong `cloudflare/wrangler.jsonc`): Cron 5 phút/lần sẽ bỏ qua và ghi cảnh báo nếu thiếu. Đặt bằng `wrangler secret put SCHEDULER_SECRET`. |
| `BYOK_PBKDF2_SALT` | *(tự sinh)* | Salt của khoá vault. Để trống thì ứng dụng tự sinh salt ngẫu nhiên và lưu ở `backend/.vault_salt` (không commit). Chỉ đặt khi hạ tầng cấp secret riêng. |

| `AI_PROVIDER` | `opencode` | Phải thuộc danh sách provider trong `backend/app/services/ai/providers.py`: `gemini \| openrouter \| openai \| anthropic \| huggingface \| ollama \| opencode`; backend từ chối khởi động nếu không, vì giá trị sai từng khiến hệ thống rơi im lặng xuống template dự phòng. `opencode` trỏ tới endpoint OpenAI-compatible của opencode zen (`https://opencode.ai/zen/v1`) và dùng đúng model bạn đang cấu hình, **không cần mua credits**. `anthropic` dùng Messages API riêng (`/v1/messages`); `ollama` và `huggingface` không bắt buộc khoá. Danh sách model hợp lệ: `GET {AI_BASE_URL}/models`. |
| `AI_TIMEOUT_SECONDS` | `420` | Timeout gọi provider. Phải lớn hơn thời gian sinh nội dung thật: `/api/v1/ai/omnichannel` đo được 83–214 giây cho 3 kênh. Timeout nhỏ sẽ kích hoạt Smart Fallback dù provider hoàn toàn ổn. Frontend dùng timeout riêng 600s cho nhóm endpoint AI (`AI_LONG_TIMEOUT` trong `frontend/src/services/api.ts`). |

## AI thật hay nội dung dự phòng?

Mỗi phản hồi AI đều mang `is_fallback`. Khi `true`, nội dung do bộ template
sinh ra chứ không phải mô hình ngôn ngữ, và giao diện hiển thị bảng cảnh báo
màu hổ phách kèm lý do (`warnings`). Đó là chủ ý: trước đây UI hiện nhãn
"Gemini 2.5 Flash" và toast báo thành công bất kể backend có gọi được provider
hay không, nên người dùng tưởng xem nội dung AI trong khi thực ra là khuôn mẫu.

Kiểm tra nhanh sau khi cấu hình:

```
curl -s http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" \
  -d '{"email":"manager@gmail.com","password":"Manager@123"}'
# lấy token, rồi:
curl -s http://127.0.0.1:8000/api/v1/ai/omnichannel -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -H "X-Workspace-Id: 1" \
  -d '{"campaign_id":1,"brief":"Ra mắt khóa học AI 2026"}'
```

`"is_fallback": false` nghĩa là AI thật đã viết nội dung.

### Ba tầng khoá AI (BYOK)

`ai_service.resolve_api_key` tra theo thứ tự, tầng đầu thắng:

| Tầng | Nguồn | Phạm vi |
| --- | --- | --- |
| 1 | Khóa lưu trong workspace | Mọi thành viên dùng chung |
| 2 | Khóa cá nhân của user | Chỉ người đó |
| 3 | `AI_API_KEY` trong `.env` | Toàn hệ thống |
| 4 | *(không có)* | Smart Fallback — template, `is_fallback=true` |

Xem/sửa khóa ở **Cài Đặt & Brand Kit → BYOK Vault**. Gán `provider` và `model`
riêng cho từng tầng; danh sách model hợp lệ lấy từ `GET {AI_BASE_URL}/models`.
Phản hồi sau mỗi lần sinh nội dung báo `model_provider` dạng
`opencode-workspace` / `opencode-user` / `opencode` để biết đang dùng tầng nào.

Lưu khóa cho workspace chỉ `MANAGER`, `AGENCY_MANAGER` hoặc `ADMIN` được —
`MARKETER` nhận 403. `CLIENT_APPROVER` không được quản lý khoá.

### Hai file `.env` phải khớp nhau

Có hai file: `.env` ở thư mục gốc (đọc bởi `docker-compose.yml`) và
`backend/.env` (đọc bởi `app/core/config.py`). Trước đây chúng lệch nhau nên
`docker compose up` chạy một backend im lặng rơi về template trong khi chạy trực
tiếp thì dùng provider khác. Khi đổi cấu hình AI, sửa **cả hai**.

## Tài khoản kiểm thử

| Email | Mật khẩu | Vai trò / giới hạn |
| --- | --- | --- |
| `manager@gmail.com` | `Manager@123` | Xem/toàn quyền chiến dịch, duyệt & xuất bản |
| `marketer@gmail.com` | `Marketer@123` | Soạn nội dung AI, lập lịch, KHÔNG tự duyệt |
| `approver@gmail.com` | `Approver@123` | Chỉ duyệt/từ chối, không được publish |
| `admin@gmail.com` | `Admin@123` | Quyền rộng nhất, quản lý khoá mọi workspace |

Các mật khẩu này chỉ phục vụ seed dữ liệu local/demo. Backend từ chối đăng ký
tự do với vai trò đặc quyền (`MANAGER`, `AGENCY_MANAGER`, `CLIENT_APPROVER`,
`ADMIN`) — xem `POST /api/v1/auth/register`.

## Giới hạn cần biết

1. PUBLISHED hiện là trạng thái của hệ thống. Chưa có bằng chứng rằng content đã được gửi và xác nhận từ một nền tảng bên ngoài.
2. Chỉ số AI/backend trong CI là kết quả của môi trường và workload đã ghi; chúng không chứng minh campaign tạo thêm doanh thu hoặc người dùng tiết kiệm thời gian.
3. Toàn bộ dữ liệu nằm trong PostgreSQL trên một VPS. Sao lưu chạy 03:00 hằng ngày và đã được thử khôi phục vào database tạm (20 bảng, 1 user, khớp bản gốc) — nhưng **bản sao vẫn nằm trên cùng đĩa với ứng dụng**, nên cứu được lỗi phần mềm chứ không cứu được hỏng phần cứng. Ứng dụng dùng `create_all()` chứ không có migration — thêm cột mới ở production cần `ALTER TABLE` thủ công. VPS là một điểm lỗi duy nhất.
4. Mọi chỉ số trên giao diện đều đọc từ `CampaignMetric` trong database. Nếu chưa nhập chỉ số thì giao diện hiển thị "chưa có dữ liệu" chứ không tự sinh số ước tính — đây là chủ ý, không phải thiếu sót. Chạy `python backend/seed/seed_data.py` để nạp dữ liệu mẫu. Dữ liệu mẫu được đánh dấu bằng `CampaignMetric.source = 'seed'` và giao diện hiện cảnh báo.
5. Điểm `compliance_score` của nội dung đa kênh đến từ bộ quét quy tắc từ khoá, không phải chấm điểm của AI; không có Brand Kit thì hiển thị "chưa chấm". Xem [đạo đức AI & giám sát](docs/AI_ETHICS_AND_HUMAN_OVERSIGHT.md).
6. Bảng so sánh prompt v1/v2/v3 chạy trên stub tất định — đo mức đáp ứng đặc tả, không đo chất lượng văn phong của mô hình thật. Xem [so sánh prompt](docs/PROMPT_VARIANT_COMPARISON.md).

## Tài liệu

- [Mục lục tài liệu](docs/README.md)
- [Phân tích yêu cầu & thiết kế](docs/REQUIREMENTS_AND_DESIGN.md)
- [Phân tích khoảng cách](docs/REQUIREMENTS_GAP_ANALYSIS.md)
- [Lộ trình dài hạn](docs/ROADMAP.md)
- [Kiến trúc](docs/ARCHITECTURE.md)
- [Kiểm thử và CI](docs/TESTING.md)
- [AI evaluation](docs/AI_EVALUATION_REPORT.md)
- [So sánh phiên bản prompt](docs/PROMPT_VARIANT_COMPARISON.md)
- [Đạo đức AI & giám sát của con người](docs/AI_ETHICS_AND_HUMAN_OVERSIGHT.md)
- [Cloudflare deployment](cloudflare/README.md)
- [Đối chiếu rubric 40 tiêu chí](docs/UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md)

V8/V9 và các biên bản/test readiness trước đây được giữ như hồ sơ snapshot. Mục lục tài liệu phân biệt rõ tài liệu hiện hành với hồ sơ lịch sử.
