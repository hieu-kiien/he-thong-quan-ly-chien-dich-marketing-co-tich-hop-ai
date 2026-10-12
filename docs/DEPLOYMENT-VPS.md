# Triển khai native trên CloudCode VPS

## Đánh giá hiện tại

VPS có 2 vCPU, 2 GiB RAM và 30 GB đĩa. Số liệu lần kiểm tra gần nhất là khoảng
393 MiB RAM khi máy gần rảnh. Cơ sở dữ liệu production khoảng 34 MB. Cấu hình này
đủ cho ứng dụng hiện tại ở mức tải thấp đến vừa, miễn là giới hạn tác vụ AI đồng
thời và không chạy mô hình AI tại VPS.

Ứng dụng có frontend React/Vite, API FastAPI, PostgreSQL và hàng đợi AI được lưu
trong PostgreSQL. Worker AI cùng scheduler được khởi động trong vòng đời FastAPI;
không cần Redis hay Celery. Tác vụ AI gọi nhà cung cấp bên ngoài, vì vậy thời
gian chờ mô hình chiếm ưu thế hơn CPU của VPS.

## Bố trí runtime

- PostgreSQL 16.15 chỉ nghe trên loopback; không mở cổng 5432 ra Internet.
- FastAPI chạy dưới tài khoản hệ thống `marketflow`, nghe tại `127.0.0.1:8000`
  (2 Uvicorn worker trên máy thật, xem mục trạng thái bên dưới).
- Nginx phục vụ frontend tĩnh và proxy `/api/` tới FastAPI; Nginx chỉ nghe trên
  `127.0.0.1:8080`.
- Cloudflare Tunnel được quản lý trong Cloudflare Dashboard và trỏ
  `marketing.kienhieu.id.vn` tới Nginx tại `http://127.0.0.1:8080`. Frontend và
  API dùng chung hostname, nên không cần cấu hình CORS cho API hostname riêng.
- Frontend được build thành file tĩnh. Node không cần chạy sau khi build.

File trong `deploy/vps/` là **bản chép nguyên từ máy chủ thật**, không phải bản
mẫu giả định đường dẫn. Nó dùng source `/opt/marketflow`, giao diện đã build ở
`/var/www/marketflow`, env production `/opt/marketflow/backend/.env` (quyền 600,
chỉ user `marketflow` đọc) và nginx nghe `127.0.0.1:8080`. Dựng lại VPS từ repo
sao chép trực tiếp các file này là có đúng cấu hình đang chạy.

## Giới hạn tài nguyên

Đặt các biến sau trong env production:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql://marketflow:<mat-khau-hex>@127.0.0.1:5432/marketflow
SCHEDULER_ENABLED=true
AI_JOB_WORKER_ENABLED=true
AI_JOB_CONCURRENCY=1
AI_JOB_TIMEOUT_SECONDS=300
AI_JOB_POLL_INTERVAL_SECONDS=2
AI_JOB_RETENTION_DAYS=7
```

Tạo mật khẩu PostgreSQL chỉ gồm ký tự hex để tránh phải URL-encode trong
`DATABASE_URL`. `SECRET_KEY`, `JWT_SECRET_KEY` và `BYOK_ENCRYPTION_KEY` phải là
secret production mạnh. Cần giữ nguyên `BYOK_ENCRYPTION_KEY` hiện dùng để đọc
các API key đã mã hóa trong DB. Không đưa secret vào repo hoặc log.

PostgreSQL nên giữ `shared_buffers` khoảng 128 MB, `work_mem` 4 MB và
`max_connections` khoảng 30. Chỉ tăng `AI_JOB_CONCURRENCY` khi đã theo dõi RAM
thực tế và có nhu cầu xử lý song song. Không chạy nhiều Uvicorn worker vì mỗi
tiến trình sẽ khởi động worker AI và scheduler riêng.

## Kế hoạch chuyển đổi an toàn

1. Cài PostgreSQL, Nginx, Python virtualenv và `cloudflared`; tạo user hệ thống
   không có quyền đăng nhập tương tác. PostgreSQL hướng dẫn cài bản 16 trên
   Ubuntu 24.04 qua PGDG apt repository trong
   [tài liệu chính thức](https://www.postgresql.org/download/linux/ubuntu/).
2. Chuyển source từ repo hiện tại, cài dependency vào virtualenv và build
   frontend với `VITE_API_URL=/api/v1`, `VITE_AI_API_URL` để trống.
3. Tạo PostgreSQL local, restore bản dump thử và đối chiếu bảng, tài khoản cùng
   số bản ghi trước khi đổi traffic.
4. Tạo Tunnel trong Cloudflare Dashboard, cài `cloudflared` service bằng tunnel
   token và đặt hostname route vào Nginx. Tunnel mở kết nối đi ra Cloudflare,
   không cần mở cổng ứng dụng vào Internet; xem
   [tài liệu Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/).
   Khởi động API, scheduler, Nginx và Tunnel; kiểm tra health/API/login qua
   hostname thử nghiệm.
5. Sao lưu lần cuối, tạm dừng ghi trong lúc chuyển dữ liệu cuối, rồi mới chuyển
   route của domain. Giữ Render và Neon sẵn sàng rollback cho tới khi xác nhận
   app và dữ liệu hoạt động ổn định.
6. Thiết lập backup PostgreSQL hằng ngày, kiểm tra khôi phục và theo dõi RAM,
   swap, dung lượng đĩa, log lỗi API và `pg_stat_activity`.

## Kế hoạch chỉnh code

- Giữ queue AI hiện có làm đường gọi chính trên UI; nó trả job ID nhanh và lưu
  trạng thái trong PostgreSQL.
- Dùng một API origin cùng domain. Sau khi rà soát các luồng còn gọi endpoint AI
  đồng bộ, có thể bỏ cơ chế `VITE_AI_API_URL` riêng cho Render và cập nhật các
  chú thích cũ nói request AI phải bypass Worker.
- Giữ endpoint đồng bộ để tương thích trong giai đoạn đầu; không xóa API công khai
  trong cùng lần chuyển hạ tầng.
- Không đổi thuật toán nghiệp vụ hoặc schema chỉ để phục vụ VPS. Mọi thay đổi
  nguồn cần phân tích GitNexus và giữ cấu hình production tách khỏi mặc định dev.

## Rủi ro vận hành

VPS đơn là một điểm lỗi duy nhất. Backup trên cùng đĩa không bảo vệ khi hỏng VPS;
cần có bản sao ngoài VPS và phải thử restore. Chuyển domain chỉ thực hiện sau khi
đã kiểm tra bản chạy mới và có thể quay lại Render/Neon.
Khi chuyển hostname đang gắn với Cloudflare Worker, chỉ đổi route của
`marketing.kienhieu.id.vn`; giữ nguyên các DNS record email.

## Trạng thái đã triển khai (2026-10-09)

Phần trên là kế hoạch. Dưới đây là những gì đã thực sự chạy và đã kiểm chứng.

| Hạng mục | Giá trị thực tế |
| --- | --- |
| Máy chủ | CloudCode NAT, Ubuntu 24.04, 2 vCPU, 2 GiB RAM, 30 GiB đĩa |
| SSH | `vn-hn.cloudcode.io.vn` cổng `30513`, key `marketflow_vps_ed25519` |
| Python | 3.12.3 hệ thống; venv ứng dụng Python 3.11.17 |
| PostgreSQL | 16.15, `shared_buffers` 384 MB, `max_connections` 40 |
| Nginx | 1.24.0, nghe `127.0.0.1:8080` |
| Cloudflared | 2026.10.0, tunnel `marketflow-prod` |
| Source | `/opt/marketflow`, venv `/opt/marketflow/.venv` |
| Cấu hình | `/opt/marketflow/backend/.env` (quyền 600) |
| Giao diện tĩnh | `/var/www/marketflow` |
| Domain | `https://marketing.kienhieu.id.vn` |

Dịch vụ systemd: `marketflow-api` (2 Uvicorn worker, `MemoryMax=1200M`, AI
concurrency 1 mỗi worker) và `cloudflared-tunnel`.

### Ba sai lệch phát hiện khi dựng thật

Tài liệu và hướng dẫn ban đầu đều dự đoán, phần này ghi lại điều thực tế:

1. **QUIC bị chặn.** Mạng VPS không mở UDP/443 nên tunnel thử QUIC rồi timeout.
   Buộc dùng `protocol: http2` trong `/etc/cloudflared/config.yml`.
2. **`.env` phải nằm trong `backend/`.** `config.py` tính đường dẫn tương đối
   tới chính nó; đặt ở thư mục gốc khiến app từ chối `SECRET_KEY`.
3. **Lệch phiên bản PostgreSQL.** Kế hoạch ghi bản 18; máy chủ đã có 16.15 từ
   khoá Ubuntu nên dùng bản 16 cho khớp.

### Đã kiểm chứng bằng thực thi, không phải giả định

- Health, trang chủ, đăng nhập ADMIN, các endpoint có phân trang: HTTP 200.
- Dashboard báo `real_rows: 0` — cơ sở dữ liệu sạch, không còn dữ liệu mẫu.
- **AI thật**: job chạy 100 giây, `is_fallback=false`, model `space-bunny-free`,
  không phải fallback mô phỏng.
- **Sao lưu đã thử khôi phục**: phục hồi vào cơ sở dữ liệu tạm được 20 bảng và
  1 user, khớp với bản gốc. Lịch 03:00 hằng ngày, giữ 7 bản mới nhất.

### Hạ tầng cũ đã gỡ

Render (`marketflow-api`, `marketflow-db`), Neon (`marketflow-prod`), Cloudflare
Worker (`marketflow-kienhieu`) và Pages (`marketflow`) đều đã xoá. `render.yaml`
và `cloudflare/wrangler.jsonc` đã xoá khỏi repo để không bị tái tạo ngoài ý muốn.

### Việc còn lại

- Xoá `/opt/marketflow/.env` trùng thừa (app đọc bản trong `backend/`) — **đã xoá**.
- App chạy bằng `User=root` — **đã chuyển** sang user `marketflow`, không đặc quyền.
- Bản sao lưu cùng đĩa — **đã thêm** lớp offsite, xem mục cuối.
- Rate limit gộp mọi người vào một IP — **đã sửa** dùng `CF-Connecting-IP`.

## Sao lưu và cảnh báo (2026-10-09, đã chạy thật)

Phần trên là kế hoạch. Toàn bộ mục việc còn lại đã được xử lý.

### Trên VPS

- Sao lưu PostgreSQL 03:00 hằng ngày qua `/etc/cron.d/marketflow-backup`,
  script `/usr/local/bin/marketflow-backup`, giữ 7 bản mới nhất.
- App chạy bằng user hệ thống `marketflow`; file `settings.env` đặt ở
  `/opt/marketflow/backend/` và chỉ user `marketflow` đọc được.
- Mỗi lần kéo bản mới, người dùng kiểm tra `pull.log` ở
  `%USERPROFILE%\marketflow-backups\`; monitor ghi ra `monitor.log` cùng chỗ.
- Bộ giới hạn đăng nhập dùng `CF-Connecting-IP` (IP thật) do nginx chuyển tiếp,
  thay vì phần đầu `X-Forwarded-For` chứa IP điểm vào của Cloudflare.

### Ngoài VPS — bản sao lưu thật sự an toàn

Trước đây bản sao lưu chỉ nằm trên cùng đĩa VPS nên **không cứu được lỗi phần
cứng**. Nay có thêm lớp thứ hai: **máy tính của người vận hành kéo bản về** qua
`marketflow-pull-backup.ps1` (lịch Windows `MarketFlow-Offsite-Backup`, 04:00 và
09:00 hằng ngày, giữ 7 phiên bản). Vì VPS không biết địa chỉ máy cá nhân (NAT,
Windows không có sshd), nên chiều khả thi là **máy cá nhân chủ động kéo**.

Các script (đặt ở `%USERPROFILE%`):

| Script | Vai trò |
|---|---|
| `marketflow-pull-backup.ps1` | Yêu cầu VPS tạo bản mới, kéo về, giữ 7 bản |
| `marketflow-monitor.ps1` | Kiểm tra domain + nội bộ VPS, ghi log, báo hỏng |
| `marketflow-verify-offsite.ps1` | Phục hồi bản local vào DB tạm trên VPS, so sánh |
| `marketflow-offsite-verify.sh` | Script tập trung chạy trên VPS |
| `marketflow-register-backup.ps1` | Đăng ký Task Scheduler |

### Đã kiểm chứng bằng thực thi, không phải giả định

- **Sao lưu trong VPS**: phục hồi vào DB tạm, 20 bảng và 1 user khớp bản gốc.
- **Sao lưu offsite**: kéo từ VPS về máy cá nhân, giải nén (2332 dòng, 20
  `CREATE TABLE`), đẩy lên VPS và phục hồi vào DB tạm — kết quả
  `goc=20 · khoi-phuc=20 · users goc=1 · khoi-phuc=1`. Đã chạy lại hai lần cho
  chắc, không chỉ một lần may mắn.
- **Cảnh báo**: `health OK: healthy`, trang chủ 200, VPS nội bộ 200 — kiểm tra
  cả tầng Cloudflare lẫn tầng VPS để biết lỗi nằm ở đâu.

### Rủi ro còn lại

- Máy cá nhân phải **bật** vào lúc 04:00 hoặc 09:00 mới kéo được; Task có
  `StartWhenAvailable` nên nếu tắt máy sẽ tự bù trong vòng 2 ngày.
- Bản local lưu dạng `.sql.gz` trên ổ `C:`. Hỏng ổ `C:` thì mất cả hai lớp.
  Nếu muốn an toàn tuyệt đối, cần đẩy lên Cloudflare R2 hoặc ổ di động.

## Đồng bộ nginx và nén (2026-10-10)

### Lỗi 404 ở `/assets/` — nguyên nhân thật

Mọi file dưới `/assets/` trả 404 khiến trang mở không ra giao diện. Nghi vấn đầu
tiên là `try_files`, nhưng nginx không phải thủ phạm: thư mục assets đang chế độ
không cho user `www-data` đọc. Sửa bằng `chmod 755` cho cả `/var/www/marketflow`
và `/var/www/marketflow/assets`.

Bài học được ghi vào repo: file nginx trong git trước đó chỉ là bản mẫu chưa
từng chạy — giả định `/srv/marketflow/frontend`, timeout 120s, thiếu cả
`CF-Connecting-IP`. Dựng lại VPS từ bản đó sẽ tái xuất hiện lỗi vừa sửa. File
trong `deploy/vps/` nay là bản chép nguyên từ máy chủ, các điểm khác biệt so với
bản mẫu cũ đều có lý do:

| Khác biệt | Vì sao |
| --- | --- |
| `upstream` + `keepalive 8` | Tái dùng kết nối tới FastAPI, đỡ TCP handshake mỗi request |
| `proxy_read_timeout 600s` | Tác vụ AI chạy 80–240 giây; bản mẫu 120s sẽ cắt ngang job |
| `CF-Connecting-IP` / `CF-IPCountry` | App và giới hạn đăng nhập cần IP thật, không phải IP Cloudflare |
| `expires 30d` + `try_files` trong `/assets/` | Cache file có hash trong tên; 404 đúng khi file thật sự không có |
| `gzip` cho `text/*`, JSON, SVG | JS ~138 KB + CSS ~95 KB nén còn ~70 KB tổng |
| `location /health` | Health độc lập, không lẫn với route `/api/` |

Thêm `deploy/vps/nginx-mf-probe.conf` — vhost `127.0.0.1:8099` in ra header
Cloudflare gửi tới, dùng để kiểm chứng IP thật khi nghi ngờ rate limit.

### Việc còn dở

- **TLS 1.3 đã có sẵn**, không phải việc còn dở. TLS kết thúc tại Cloudflare
  edge chứ không tại VPS (nginx chỉ nghe loopback). Kiểm chứng bằng
  `openssl s_client -tls1_3`: bắt tay ra `TLSv1.3, TLS_AES_256_GCM_SHA384`.
  Dashboard đặt mức tối thiểu là 1.2 — nên giữ nguyên, nâng lên 1.3 chỉ chặn
  client cũ mà không được lợi ích gì thêm vì bản 1.3 đã được chọn thật.
- **`marketflow-api.service` trong repo vẫn là bản mẫu đã lệch**: thực tế chạy
  `--workers 2 --timeout-keep-alive 75`, env ở `/opt/marketflow/backend/.env`,
  không dùng `--proxy-headers`. Chưa đồng bộ vì chưa cần dựng lại máy chủ; nếu
  giữ repo làm nguồn dựng lại thì phải sửa cùng đợt.
- **Resend**: code xong (`EMAIL_PROVIDER=resend`, `RESEND_API_KEY`,
  `EMAIL_FROM_ADDRESS`), đang đặt `none`. Cần người vận hành tạo key ở
  resend.com và xác thực domain gửi, rồi dán biến vào `/opt/marketflow/backend/.env`
  trên VPS và khởi động lại `marketflow-api`.

## Đo Lighthouse / Core Web Vitals (2026-10-10)

Đo bằng Chrome DevTools MCP trên trang chủ, desktop, không bóp CPU/mạng. Hệ
thống chưa có dữ liệu CrUX thật nên con số dưới đây là **lab**, đo từ máy vận
hành ở Việt Nam.

### Điểm

| Chỉ số | Giá trị | Ngưỡng | Kết luận |
| --- | --- | --- | --- |
| LCP | 1.769 ms | < 2.5 s | Tốt |
| CLS | 0,00 | < 0,1 | Tốt |
| TTFB | 210 ms | < 800 ms | Tốt |
| Lighthouse a11y | 96 | — | Tốt |
| Lighthouse best-practices | 77 | — | Cần xem |
| Lighthouse SEO | 82 | — | Cần xem |

LCP gồm TTFB 210 ms + độ trễ render 1.559 ms. Độ trễ render chiếm 88 % và là
chi phí tất yếu của SPA: phải tải và chạy xong React mới vẽ được chữ đầu tiên.
Cách giảm là bớt JS phải chạy trước khi vẽ, không phải sửa nginx.

### Phát hiện, xếp theo mức đáng sửa

1. **`/robots.txt`, `/sitemap.xml`, `/favicon.ico` trả về trang HTML.** Nginx
   `location /` đẩy mọi đường dẫn thiếu về `index.html`, nên bot xin
   `robots.txt` nhận nguyên trang HTML (trạng thái 200,
   `content-type: text/html`) — Lighthouse báo *robots.txt is not valid, 21
   errors*. Mọi URL vô nghĩa cũng trả 200 HTML thay vì 404, làm bẩn dữ liệu
   crawl. Cách sửa: đặt `robots.txt` thật vào `frontend/public/` và cho nginx
   trả 404 cho `.txt`/`.xml`/`.ico` thay vì fallback về SPA.
2. **Không có `meta description`.** Trang chủ chỉ có `<title>`. Thêm một thẻ
   mô tả khoảng 150 ký tự là xong việc này.
3. **Nhiều API bị gọi trùng trên một lần tải trang**: `/campaigns` 4 lần,
   `/analytics/dashboard` 5 lần, `/contents` 5 lần. Các component tự fetch
   không dùng cache chung nên cứ vào trang là dội lại hết. Trên VPS 2 vCPU việc
   này cộng thêm tải thật; phía UI cũng phải hiện skeleton lâu hơn. Cách sửa:
   một query cache dùng chung (React Query với `staleTime`, hoặc context giữ
   kết quả) để các component đọc lại thay vì tự gọi.
4. **Google Fonts chặn render và là bên thứ ba.** `<link>` tới
   `fonts.googleapis.com` nằm trong `<head>` nên chặn vẽ đầu tiên; sau đó còn
   3 file woff2 từ `fonts.gstatic.com`. Trang chỉ cần tiếng Việt và latin — tự
   host hai subset đó rồi `preload` sẽ bỏ được cả lối tắt DNS/TLS sang bên thứ
   ba, và cache 30 ngày qua `assets/` luôn. Tách subset xong còn bỏ được
   cyrillic-ext chưa ai dùng.
5. **Cloudflare đang trả gzip chứ không phải brotli.** Request từ Chrome có
   `accept-encoding: br` nhưng phản hồi vẫn `content-encoding: gzip` vì nginx
   đã nén từ đầu và Cloudflare chỉ chuyển tiếp bản đã nén. Nếu bỏ gzip ở nginx,
   Cloudflare sẽ nén lại bằng brotli (nhỏ hơn gzip khoảng 15–20 %) và VPS đỡ
   tốn CPU nén. Cần đo trước khi đổi để chắc Cloudflare thật sự nén lại response
   đi qua tunnel — **chưa làm**, chỉ ghi lại lựa chọn này. Gzip ở nginx vẫn giữ
   nguyên trong repo cho tới khi có quyết định.
6. **Dữ liệu mẫu nằm trong bundle production.** Các hằng `MOCK_CAMPAIGNS`,
   `MOCK_CHANNEL_ATTRIBUTION` trong `frontend/src/services/mockData.ts` nằm
   trong `index-*.js` phục vụ mọi lượt vào trang. Nếu chỉ là dự phòng khi API
   lỗi/offline, nên tách sang import động để first-load khỏi tải.
7. Nặng nhỏ còn lại: `LegacyJavaScript` 10,6 kB code hỗ trợ trình duyệt cũ;
   favicon vẫn là `/vite.svg` mặc định của Vite.

Lỗi `errors-in-console` mà Lighthouse bắt được là `chrome-extension://invalid/`
— lỗi của extension trong máy vận hành, không phải của trang.

## Phiên 2026-10-10 (buổi chiều)

### Sự cố cần biết: VPS ngỏng lúc ~12:35

Domain trả Cloudflare **error 1033** (mất kết nối tới cloudflared), SSH cổng
30513 timeout dù ping còn trả lời. Monitor cuối cùng thấy healthy lúc
12:02:49. **Chưa xử lý được vì không vào được máy chủ từ xa** — cần người
vận hành kiểm tra trực tiếp: VPS còn sống không, `systemctl status
cloudflared-tunnel`, mạng ra ngoài của VPS có bị chặn/rớt không. Các sửa đổi
trong ba commit dưới chưa được đẩy lên server.

### Đã sửa trong các commit này

1. **Trang đăng nhập mới** (bản Halloween của người vận hành, port sang React):
   cảnh ngày/đêm, dây leo SVG, đèn pin chiếu từng ký tự mật khẩu, sói 60 khung,
   nhện canvas. Ảnh sói PNG 1,42 MB → WebP 0,47 MB. Toàn bộ hiệu ứng tách thành
   module `frontend/src/features/halloween-login/` có cleanup: rời trang là gỡ
   sạch listener và class trên `<body>`.
2. **Sửa lỗi login mất chữ đã gõ** (lỗi có sẵn, không do port): `login()` và
   `register()` trong AuthContext bật cùng cờ `isLoading` mà App.tsx dùng để
   tháo LoginPage khỏi cây React. Giữa lúc đăng nhập trang bị unmount: chữ đã
   gõ biến mất, lỗi không kịp hiện, cảnh phải dựng lại. Cờ chung đã bỏ, trang
   đăng nhập tự theo dõi trạng thái chờ.
3. **Nhà cung cấp AI lỗi thời — đã nâng cấp theo mô hình của 9Router** (khảo
   sát `github.com/decolua/9router`): bài học cốt lõi là *không hardcode tên
   model*. Ta làm theo bằng endpoint `GET /api/v1/settings/ai-models` gọi
   `{base_url}/models` của nhà cung cấp; nếu không liệt kê được (Anthropic,
   lỗi mạng, thiếu khoá) thì dùng danh sách dự phòng đã kiểm chứng trong
   `providers.py`. Thử thật: OpenCode Zen trả `source=live` với model
   `space-bunny-free, big-pickle, mimo-v2.6-flash-free…`. Model mặc định cập
   nhật theo trang chính thức: `gemini-3.8-flash`, `gpt-6.1-sol`,
   `claude-sonnet-4-6`, `anthropic/claude-sonnet-4-6` cho OpenRouter. Registry
   có thêm `free_tier`/`free_note` để UI gợi ý tầng miễn phí.
4. **SEO (Lighthouse phàn nàn từ phiên trước)**: thêm meta description + og
   tags, favicon thật thay `/vite.svg`, `robots.txt` và `sitemap.xml` thật.
   nginx đổi `.txt/.xml/.ico` thiếu sang **404** thay vì rơi vào fallback SPA
   (trước đó bot xin `robots.txt` nhận trang HTML — Lighthouse báo 21 lỗi).
   `/api/` và `/assets/` chuyển sang `^~` để location regex không ăn nhầm.

### Còn dở

- **Resend trên VPS đã hoàn tất** (2026-10-11, xem mục cuối tài liệu).
- **Gộp chuỗi fallback (combos kiểu 9Router)**: hiện mới có Smart Fallback
  trong app, chưa có chuỗi do người dùng đặt tên. Việc tiếp theo hợp lý.
- Ba việc "đáng làm" trong mục dự án (API gọi trùng, Google Fonts tự host,
  dữ liệu mẫu trong bundle) vẫn chưa ai làm.
- File lạ `D:\Temp\hieuk\opencode\inspect.py` (đọc `/root/.cloudflared/cert.pem`)
  được phát hiện khi chạy test; **không phải do phiên này tạo**, đã không chạy
  nó. Người vận hành nên xoá hoặc kiểm tra nguồn gốc.

## Email Resend — đã chạy thật (2026-10-10, tối)

Làm bằng browser skill (bsk) trên phiên đăng nhập sẵn của người vận hành:

- **API key đã tạo**: `re_5VDLniyM…` ("MarketFlow production mail", quyền
  Sending access), lưu vào `backend/.env` máy này (file .env có gitignore).
- **Domain riêng**: `marketing.kienhieu.id.vn` đã thêm và **Verified** trong
  Resend. Bản ghi DNS do tôi tự thêm trong Cloudflare Dashboard: TXT DKIM,
  CNAME `rsend.marketing` + `send.marketing` → `*.forge.rmta.net`.
- **Gửi thử đã thành công ba lần**, kèm id trả về từ Resend:
  1. về `qtu1053@gmail.com` (chế độ thử `onboarding@resend.dev`);
  2. về người nhận **ngoài** chủ tài khoản (`dtc245200244@ictu.edu.vn`) từ địa
     chỉ đã xác thực `no-reply@auth.kienhieu.id.vn`;
  3. về `dtc245200244@ictu.edu.vn` từ địa chỉ mới
     `no-reply@marketing.kienhieu.id.vn`.
- `GET /api/v1/settings/email-status` trả
  `{enabled: true, provider: resend, from_address: no-reply@marketing.kienhieu.id.vn}`.
- Lưu ý đúng thiết kế: `send()` không ném lỗi ra ngoài; gửi sai địa chỉ ở chế độ
  thử trả `{sent: false, reason: …}` chứ không làm hỏng request nghiệp vụ.

### Hai cái bẫy đã mắc, ghi lại để lần sau khỏi lặp

1. **Bản ghi DNS trong Cloudflare phải để "DNS only", tuyệt đối không Proxied.**
   Lần đầu tôi thêm 2 CNAME `rsend/send` bị mặc định **Proxied** (mây cam) →
   DNS không phân giải được kiểu CNAME → Resend báo Failed mãi. Mở panel Edit →
   tắt công tắc "Proxy status" → Save. Cách nhận biết đúng: `Resolve-DnsName`
   phải trả về NameHost, và cả 1.1.1.1 lẫn 8.8.8.8 đều phải thấy.
2. **Sau khi Resend đã đánh dấu Failed, bấm Verify lại có thể không chạy thật.**
   Cách chắc ăn: xoá domain, thêm lại, rồi Verify — lần làm lại này qua luôn.
3. Tiện thể: `D:\Temp\hieuk\opencode`đã có sẵn 2 domain `auth.*` của cùng chủ —
   thêm domain mới trên gói free bị chặn ở mốc 3 domain; phải xoá domain hỏng
   (`gtoil.vn`, Failed) mới có chỗ trống.
4. Key Resend quyền **Sending access không đọc được** bản ghi DNS qua API. Muốn
   lấy đầy đủ giá trị CNAME phải tạo key **Full access** tạm, đọc xong **xoá
   ngay** (đã làm đúng vậy).

### Còn lại trên VPS — đã hoàn tất (2026-10-11)

Bốn dòng env đã ghi vào `/opt/marketflow/backend/.env` (lưu ý: bản cũ trên VPS
đang có `EMAIL_PROVIDER="none"` — giá trị placeholder, không phải thiếu key) rồi
`systemctl restart marketflow-api`. Từ chối `none` sang `resend` + thêm
`RESEND_API_KEY` và `EMAIL_FROM_NAME`.

## Sự cố VPS chết và khôi phục (2026-10-11)

### Diễn biến

1. ~12:02 UTC VPS tắt đột ngột (panel CloudCode ghi `STOPPED`). Domain timeout,
   SSH reset, tunnel báo error 1033.
2. Panel `my.cloudcode.io.vn` lỗi HTTP 500; panel mới **`vps.cloud.codes`**
   (`cloudcode.io.vn/my` cũng trỏ tới hệ thống này) vẫn chạy. Người vận hành
   bấm **Start** trên trang `vps.cloud.codes/servers/639a6009`.
3. VPS lên (uptime 4 phút) nhưng **domain vẫn chết**.

### Hai nguyên nhân và cách sửa

1. **Bản ghi DNS tunnel phải Proxied (mây cam).** Sau khi VPS chạy lại,
   `marketing.kienhieu.id.vn` (CNAME → `<tunnel-uuid>.cfargotunnel.com`) đang ở
   chế độ **DNS only**. Resolver đuổi theo CNAME và chỉ nhận được
   `fd10:aec2:5dae::` — IPv6 unique-local, không giao thông được → timeout cả
   từ trong VPS lẫn ngoài. Bật **Proxy status** trong DNS dashboard là xong
   ngay (trả IP edge `104.21.x/172.67.x`, front 200).
   - **Khác với record Resend** ở trên: record mail (TXT/CNAME rsend, send)
     phải **DNS only**; record **tunnel hostname** phải **Proxied**. Hai kiểu
     record, hai quy tắc ngược nhau — đừng lẫn.
2. **Quyền thư mục `/var/www/marketflow`.** scp từ Windows tạo thư mục con
   `drwx------` (umask 077) → nginx (www-data) không đọc được → asset trả
   fallback SPA (HTML 2023 byte) hoặc 404 dù file có trên đĩa. Fix:
   `find /var/www/marketflow -type d -exec chmod 755 {} +` và
   `find /var/www/marketflow -type f -exec chmod 644 {} +`.
   Cloudflare còn cache briefly cái 404 cũ — request có query `?v=2` xác nhận
   file phục vụ đúng, cache tự hết sau vài phút.

### Việc deploy dở dang trong lúc VPS chết đã hoàn tất

- Kéo 7 commit mới nhất (`ca713fd`) vào `/opt/marketflow`.
- nginx đổi sang `deploy/vps/nginx-marketflow.conf` (gzip, CF-Connecting-IP,
  timeout 600s, `/api/`+`/assets/` `^~`, `.txt/.xml/.ico` thiếu → 404).
- Frontend build lại local với `VITE_AI_API_URL=` **trống** (bỏ URL Render đã
  chết trong `frontend/.env`) và `VITE_API_URL=/api/v1`; upload `dist/` lên
  `/var/www/marketflow`.
- Host key SSH của `vn-hn.cloudcode.io.vn:30513` thay đổi sau khi máy được
  Start lại (có thể provider chuyển VM sang node khác) — đã ghi nhận key mới.

### Panel VPS

| Link | Ghi chú |
| --- | --- |
| `https://cloudcode.io.vn/my` | Danh sách server |
| `https://vps.cloud.codes/servers/639a6009` | Server NAT-GO-300PAG (Start/Restart/Kill) |

Lưu ý: browser bsk (automation) gặp `ERR_SSL_UNRECOGNIZED_NAME_ALERT` khi mở
`vps.cloud.codes` — thao tác Start phải làm tay trên browser người vận hành.
