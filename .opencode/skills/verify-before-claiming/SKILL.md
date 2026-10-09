---
name: verify-before-claiming
description: Ngăn opencode báo cáo "đã xong" khi chưa thực sự kiểm chứng. Use when deploying, running multi-step scripts on a server, editing infra config (nginx/systemd/cron/cloudflare), setting up backups or schedules, or before reporting any completed operational task. Triggers on "deploy", "triển khai", "sao lưu", "backup", "cron", "lịch", "nginx", "systemd", "đã xong", "hoàn tất", "chạy thử", "verify", "kiểm tra".
---

# Kiểm chứng trước khi báo cáo

Skill này sinh ra từ ba lỗi thật của chính agent, cùng một mẫu hình:

| Ngày | Đã làm | Sai ở đâu |
|---|---|---|
| 2026-10-09 | Đặt lịch sao lưu 03:00 | `createdb -q` fail giữa script, các lệnh sau không chạy. Đọc dòng in thành công trước đó rồi báo "xong". |
| 2026-10-09 | Kết luận Cloudflare không gửi header | Log rỗng vì `sed` không khớp (file không có `access_log` để thay), debug log chưa bao giờ bật. Đọc "không có dòng" thành "không có header". |
| 2026-10-09 | Báo AI đã sửa xong | Job trả 5 giây — đó là fallback mô phỏng, không phải LLM thật. Đã "thành công" trong khi hệ thống im lặng phục vụ dữ liệu giả. |

Cả ba đều là **một** lỗi: **tin vào dấu hiệu thành công thay vì kiểm tra trạng thái thật.**

## Quy tắc

### 1. Mỗi bước trong script phải tự kiểm tra

Không để trạng thái "đã xong" là điều kiện cuối của script. Mỗi bước phải thoát
non-zero nếu hỏng, và các bước sau phải **không chạy** khi bước trước hỏng.

```bash
# SAI: lỗi ở giữa thì phần còn lại vẫn chạy, in "XONG" giả
set -e
createdb -q ...     # createdb không có cờ -q -> fail
cat > /etc/cron.d/...
echo "== XONG =="

# ĐÚNG: kiểm tra từng bước, không in XONG khi chưa xác minh
set -euo pipefail
createdb -O marketflow vt
psql -q -d vt -f restore.sql
[ "$(so_bang_goc)" = "$(so_bang_khoi_phuc)" ] || { echo "KHOI PHUC SAI"; exit 1; }
grep -q marketflow-backup /etc/cron.d/marketflow-backup || { echo "LICH CHUA TAO"; exit 1; }
echo "== XONG =="
```

Không dùng cờ ngắn gọn bạn không chắc tồn tại (`-q` ở `createdb`). Cứ bỏ cờ, thêm
`2>/dev/null` khi cần.

### 2. Đo trạng thái thật, không đo dấu hiệu thay thế

"Log rỗng" không có nghĩa "header vắng mặt". Nó có thể nghĩa log chưa bật.
"Không có dòng cảnh báo" không có nghĩa không có lỗi. Nó có thể nghĩa grep sai mẫu.

Trước khi kết luận "không có X", hỏi: **cơ chế ghi X đã hoạt động chưa?**

```bash
# SAI: sed không khớp -> log rỗng -> kết luận sai
sed -i 's|access_log /var/log/nginx/access.log;|...|' conf
curl ...; tail log   # rỗng
echo "=> không có header"

# ĐÚNG: kiểm tra log thật sự đã bật, rồi mới kết luận
grep -q 'log_format mfdbg' /etc/nginx/nginx.conf || { echo "LOG CHUA BAT"; exit 1; }
systemctl reload nginx
curl ...; tail /var/log/nginx/mfdbg.log
```

Cách chắc chắn hơn: dựng endpoint tạm trả về chính giá trị cần đo, đọc nó, rồi xoá.

### 3. Phân biệt thành công từ "không lỗi"

Với hệ thống có đường fallback, **trả về 200 không phải bằng chứng đã làm đúng việc**.
Hãy kiểm tra đúng thứ cần có:

- AI trả nội dung thật → `is_fallback=false`, `model` **không** chứa "Fallback",
  và thời gian chạy hợp lý với LLM thật (dưới 5 giây là đáng ngờ).
- Cơ sở dữ liệu → đếm bảng và bản ghi, so giữa bản gốc với bản sao.
- Cấu hình → đọc lại từ nơi thực sự đọc nó, không đọc từ nơi vừa ghi.
- Dịch vụ → `systemctl is-active` **và** một request thật qua đường đi thật.

### 4. Thử phá trước khi tin

Sao lưu chưa từng khôi phục thì không phải sao lưu. Circuit breaker chưa từng thử với
provider chết thì không phải bảo vệ.

Cách kiểm chứng rẻ nhất là phá thử trong môi trường kiểm soát được, có đường quay
về: trỏ cấu hình sang host chết, kích hoạt lỗi, xác nhận hành vi, **rồi khôi phục
và kiểm tra lại lần nữa**.

Nếu thử trực tiếp trên production: backup trước, sửa tối thiểu, có đường thoát.

### 5. Báo cáo trung thực cả phần chưa làm

Câu báo cáo phải tách rõ ba mức: **đã làm và đã kiểm chứng** / **đã làm chưa kiểm
chứng** / **chưa làm**. Không gộp ba mức thành một.

Khi một bước thất bại, nói rõ bước nào và vì sao, thay vì tự sửa bằng cách đoán và
báo như thể đã xong. Sửa lại rồi mới báo là chuỗi hai lần "đã kiểm chứng".

### 6. Với hạ tầng: sửa xong phải khôi phục sạch

Khi thêm cấu hình tạm để đo (location probe, log_format, header thử), **xoá và xác
nhận đã xoá** trong cùng lượt. Đừng để lại cấu hình đo trong production.

### 7. Biết trước cái bẫy của công cụ mình đang dùng

Lỗi này đã xảy ra thật khi thêm endpoint email: `Set-Content -Encoding UTF8` của
PowerShell 5.1 ghi thêm **BOM** (3 byte `EF BB BF`) vào đầu file. Python từ chối
parse với `SyntaxError: invalid non-printable character U+FEFF`. File nhìn bình
thường, chỉ có test đọc bằng `ast.parse` mới lộ ra.

Tương tự, `"$file.FullName"` trong chuỗi nháy kép là **chữ literal**, không truy
cập được property — phải viết `$($file.FullName)` hoặc gán vào biến trước.

Không dùng cách đã từng làm hỏng file. Kiểm tra bằng `py_compile` (và cả test đọc
`ast`) trước khi commit.

## Trước khi commit hoặc deploy

- [ ] Mọi lệnh trong script đã chạy hết, không bị `set -e` cắt im lặng?
- [ ] Đã đọc lại trạng thái thật từ nơi hệ thống thực sự đọc?
- [ ] Nếu có fallback/smoke: đã xác nhận **không** rơi vào đường giả?
- [ ] Cấu hình tạm đã xoá và đã xác nhận xoá?
- [ ] Phần chưa làm có được nói thẳng ra không?

## Khi nào áp dụng

Mọi tác vụ vận hành: deploy, sao lưu, cron, nginx, systemd, DNS, secret, di trú.
Với tác vụ vận hành, **rủi ro lớn nhất không phải làm sai mà là báo sai**. Sửa sai thì
tự phát hiện khi chạy tiếp; báo sai thì mất niềm tin và không ai kiểm tra lại.