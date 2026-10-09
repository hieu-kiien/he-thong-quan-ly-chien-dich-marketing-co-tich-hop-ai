# Lộ trình dài hạn MarketFlow AI

**Loại tài liệu:** Đề xuất định hướng; chưa phải cam kết lịch phát hành.
**Trạng thái mã nguồn:** mô tả theo trạng thái hiện tại trên `main` (FastAPI + PostgreSQL
+ nginx trên một VPS; Cloudflare chỉ giữ DNS/CDN/Tunnel). Xem `git log -1` trên commit
sửa tài liệu này để biết baseline chính xác.
**Nguồn định hướng:** [Nghiên cứu đối thủ](https://chatgpt.com/share/6abb25a6-2328-83ec-8402-0038059a95a2), [đánh giá dự án và vấn đề người dùng](https://chatgpt.com/share/6aba47a2-feb0-83ec-a47f-16757fd55d17), cùng mã nguồn và CI hiện tại.

> **Ghi chú lịch sử.** Các mục cũ trong bản trước nói "Worker tuần tự hoá write và
> sao lưu toàn bộ file SQLite lên R2" và "lưu trữ triển khai Cloudflare đã hiện
> thực". Cả hai **không còn đúng**: tài khoản không có Workers Paid plan nên
> containers không deploy được (Cloudflare trả 401), và kiến trúc hiện tại là
> Postgres trên Render. Các mục đó đã được sửa ở bên dưới.
>
> **Cập nhật 2026-10-09:** hạ tầng đã gộp về một VPS; Render, Neon và Cloudflare
> Worker đã bị gỡ. Bảng hạ tầng ở bên dưới được cập nhật theo hiện trạng; phần còn
> lại của ROADMAP là kế hoạch sản phẩm và không phụ thuộc hạ tầng cũ.

## 1. Tóm tắt quyết định

Định hướng đề xuất là xây MarketFlow thành **không gian điều phối chiến dịch cho nhóm marketing agency nhỏ và vừa**. Mỗi chiến dịch cần nối được brief, người phụ trách, việc cần làm, duyệt nội dung, kế hoạch ngân sách/KPI, phân phối nội dung và kết quả đo lường.

Lát cắt sản phẩm kế tiếp nên hoàn tất một chiến dịch qua **một kênh gửi email thật**: brief → giao việc → tạo nội dung → duyệt → gửi/lên lịch → nhận sự kiện từ nhà cung cấp → xem kết quả. AI hỗ trợ các bước viết và giải thích dữ liệu; quyền duyệt, chi tiêu và kết luận vận hành vẫn do người dùng và logic xác định kiểm soát.

Ưu tiên theo thứ tự:

1. Làm rõ người dùng chính và giá trị mà họ nhận được.
2. Chỉnh các thông tin giao diện và tài liệu để phản ánh đúng hành vi hiện tại.
3. Đảm bảo độ bền dữ liệu và tính đúng đắn của trạng thái trước khi dùng dữ liệu khách hàng thật.
4. Xây, đo và thử nghiệm một luồng gửi email thật.
5. Chỉ mở rộng kênh và phạm vi sản phẩm khi thử nghiệm thực tế chứng minh nhu cầu.

## 2. Trạng thái xuất phát

Các trạng thái được dùng trong tài liệu này:

- **Đã hiện thực:** có trong mã hiện tại.
- **Đã kiểm thử:** có kết quả test/CI cho phạm vi được nêu.
- **Đề xuất:** việc tương lai, chưa được tính là tính năng.
- **Chưa xác nhận:** repo chưa có bằng chứng đủ để kết luận.

| Năng lực | Trạng thái hiện tại | Bằng chứng hoặc giới hạn |
|---|---|---|
| Workspace, vai trò và ranh giới truy cập | Đã hiện thực; có kiểm thử | Backend, test bảo mật và các gate CI. |
| Chiến dịch, brief, tác vụ, ngân sách và KPI mục tiêu | Đã hiện thực; có kiểm thử | API chiến dịch/tác vụ và màn hình Campaign Hub. |
| Soạn nội dung bằng AI và quy trình người duyệt | Đã hiện thực; có kiểm thử | AI API, Review Queue và state machine nội dung. |
| Lên lịch và trạng thái PUBLISHED | Đã hiện thực ở mức trạng thái nội bộ | Scheduler đổi lịch sang EXECUTED và nội dung sang PUBLISHED; chưa có kết nối gửi mạng xã hội/email trong luồng này. |
| Gửi email thật và nhận sự kiện gửi | Đề xuất; chưa hiện thực | Chưa tìm thấy tích hợp SendGrid/provider trong backend hoặc frontend. |
| Dashboard vận hành và chẩn đoán AI | Đã hiện thực; có kiểm thử trong phạm vi CI | Các chỉ số hiện có chưa chứng minh cải thiện hiệu quả marketing của khách hàng. |
| Soạn nội dung **không** dùng AI | Đã hiện thực; có kiểm thử | `ManualContentComposer.tsx` + `test_offline_core_works_without_ai.py` + `works-without-ai.spec.ts`. |
| Nhiều nhà cung cấp AI | Đã hiện thực; có kiểm thử (mock, không gọi mạng) | Registry tại `providers.py`; adapter Anthropic; Ollama/HuggingFace không bắt buộc khoá. |
| So sánh 3 phiên bản prompt | Đã hiện thực; chỉ đo đặc tả trên stub | [PROMPT_VARIANT_COMPARISON.md](PROMPT_VARIANT_COMPARISON.md). |
| Cơ chế đạo đức & giám sát | Đã hiện thực; có tài liệu và test ràng buộc tài liệu | [AI_ETHICS_AND_HUMAN_OVERSIGHT.md](AI_ETHICS_AND_HUMAN_OVERSIGHT.md). |
| Lưu trữ triển khai | PostgreSQL trên VPS, Cloudflare chỉ DNS/Tunnel | Mọi ứng dụng trên một máy; không còn mã Worker. Xem [DEPLOYMENT-VPS.md](DEPLOYMENT-VPS.md). |
| Circuit breaker AI | Đã hiện thực; có kiểm thử | `backend/app/services/ai/circuit_breaker.py`; 3 lỗi liên tiếp thì ngắt, 60s sau thử lại. |
| IP thật cho rate limit | Đã hiện thực; đã đo qua tunnel | `CF-Connecting-IP` được nginx forward và app ưu tiên trước `X-Forwarded-For`. |

CI xanh chứng minh các gate đã chạy đạt ở commit tương ứng; điều đó không thay thế thử nghiệm usability, pilot, hay xác nhận độ bền lưu trữ dưới tải thật. Báo cáo AI hiện là benchmark có tập mẫu hữu hạn, không phải cam kết tổng quát về chất lượng mọi đầu ra.

## 3. Người dùng và lời hứa sản phẩm

### Nhóm người dùng ưu tiên

1. **Quản lý agency:** điều phối nhiều khách hàng/chiến dịch; cần thấy rủi ro, chỗ tắc, ngân sách và quyết định cần đưa ra.
2. **Marketer/nhân viên thực thi:** cần biết việc kế tiếp, deadline, brief và người đang chờ phản hồi.
3. **Người duyệt phía khách hàng:** cần xem đúng nội dung, phản hồi/duyệt và biết điều gì sẽ được phát hành.

### Lời hứa cần kiểm chứng

> Một nhóm agency có thể điều phối chiến dịch từ brief đến kết quả trong một workspace, biết rõ ai đang làm gì, nội dung nào đang chờ duyệt và chiến dịch nào cần can thiệp.

Đây là giả thuyết sản phẩm. Chỉ được mô tả là giá trị đã được xác nhận sau khi người dùng mục tiêu hoàn thành các tác vụ và dữ liệu pilot hỗ trợ kết luận đó.

### Câu hỏi phải trả lời trong giao diện

- Quản lý: chiến dịch nào đang lệch tiến độ/ngân sách/KPI; nguyên nhân; ai cần làm gì tiếp theo?
- Marketer: việc ưu tiên tiếp theo là gì; brief, hạn và trạng thái duyệt ở đâu?
- Người duyệt: nội dung nào đang chờ; nội dung sau khi duyệt sẽ được gửi ở đâu và khi nào?

## 4. Phạm vi theo thời hạn

Thời lượng dưới đây là khung tương đối để lập kế hoạch. Chốt lại sau khi biết quy mô nhóm, lịch học/bảo vệ và kết quả phỏng vấn. Các giai đoạn có thể gối nhau, nhưng không bỏ cổng nghiệm thu.

### Giai đoạn 0 — Làm sạch nguồn sự thật và chốt phạm vi

**Khung tham khảo:** 1–2 tuần.
**Mục tiêu:** mọi người nhìn vào cùng một trạng thái sản phẩm và cùng một bộ tài liệu.

**Việc làm**

- Dùng `docs/README.md` làm mục lục; dùng tài liệu này làm roadmap; dùng `docs/TESTING.md` làm nguồn hướng dẫn test.
- Sửa README và tài liệu kiến trúc để phân biệt rõ đã hiện thực, đã kiểm thử, đề xuất và chưa xác nhận.
- Gắn trạng thái lịch sử cho TEST_READY, TEST_INFRA, biên bản nghiệm thu và bộ báo cáo V8/V9; giữ nguyên PDF đã nộp.
- Ghi lại baseline repo/CI, rủi ro Cloudflare và khoảng trống phát hành thật.
- Xác định một chủ sở hữu cho từng tài liệu sống và quy tắc cập nhật theo nguồn sự thật.

**Nghiệm thu**

- Người đọc mới tìm được cách chạy, test, xem kiến trúc và roadmap trong dưới 3 phút.
- Không còn hai nguồn hiện hành đưa ra hai con số test khác nhau.
- Mọi nội dung “đã phát hành” chỉ ra được bằng chứng provider hoặc được ghi rõ là trạng thái nội bộ.

### Giai đoạn 1 — Khám phá workflow agency và giảm tải trải nghiệm

**Khung tham khảo:** 2–3 tuần.
**Mục tiêu:** xác nhận đúng vấn đề và làm người dùng nhận ra việc cần làm mà không cần người hướng dẫn.

**Việc làm**

- Phỏng vấn 5–8 người thuộc các vai trò quản lý agency, marketer và người duyệt khách hàng; tập trung vào cách họ quản lý chiến dịch hiện tại, bảng tính/công cụ đang dùng và nơi hay trễ.
- Quan sát ít nhất 5 lượt hoàn thành tác vụ: tạo/đọc brief, tìm task trễ, duyệt nội dung và xem ngân sách/KPI.
- Vẽ một hành trình duy nhất và ghi mọi chỗ người dùng phải đổi công cụ hoặc nhập lại thông tin.
- Thử hai luồng điều hướng: quản lý cần điều phối và marketer cần làm việc hôm nay.
- Thu gọn màn hình đầu thành danh sách hành động/rủi ro rõ ràng; chuyển chỉ số chuyên sâu vào chi tiết chiến dịch/báo cáo.
- Ghi lại thuật ngữ người dùng hiểu; bỏ nhãn nội bộ như “AI Doctor” khỏi vị trí quyết định chính nếu người dùng không hiểu lợi ích.

**Nghiệm thu đề xuất**

- Ít nhất 4/5 người thử có thể tự tìm chiến dịch có rủi ro, task kế tiếp và mục đang chờ duyệt.
- Ghi baseline thời gian hoàn thành, lỗi thao tác, câu hỏi cần trợ giúp và mức tin tưởng vào trạng thái xuất bản.
- Mỗi thay đổi UI liên kết với một quan sát hoặc usability issue cụ thể.

### Giai đoạn 2 — Tin cậy nghiệp vụ, trạng thái và dữ liệu

**Khung tham khảo:** 2–4 tuần.
**Mục tiêu:** không để UI hoặc hạ tầng báo kết quả mạnh hơn bằng chứng thật.

**Việc làm**

- Đổi nhãn PUBLISHED, lịch và thông báo đến khi có connector gửi thật; thể hiện riêng trạng thái “đã duyệt”, “đã lên lịch”, “đã gửi provider xác nhận” và “đã nhận sự kiện delivered”.
- Kiểm tra đường tenant/RBAC của các thao tác tác vụ, chiến dịch, nội dung và metrics theo từng vai trò.
- Kiểm chứng backup/restore của Postgres trên Render và Neon: sao lưu tự động có thật không, thời gian khôi phục, và hành vi khi mất kết nối giữa chừng.
- Chốt `DATABASE_URL` production (Render Postgres hay Neon `marketflow-prod`) và ghi lại lựa chọn cùng lý do. Bước này cần làm tay trong Render Dashboard — xem [ARCHITECTURE.md](ARCHITECTURE.md) mục 2.
- Có đường dẫn `ALTER TABLE` tài liệu hoá cho cột mới, vì ứng dụng dùng `create_all()` chứ không dùng migration.
- Rà soát các advisory npm/pip; ghi từng advisory, mức ảnh hưởng, quyết định nâng cấp/waiver và ngày xem lại. Nâng các GitHub Actions còn bị ép chạy Node 24 theo kế hoạch nâng runtime.
- Kiểm tra seed account, secret và cấu hình demo để không dùng mật khẩu mặc định trong môi trường thật.

**Nghiệm thu**

- Có kiểm thử khôi phục backup và test lỗi ghi/restore trước khi chạy pilot có dữ liệu khách hàng.
- Không còn trạng thái giao diện đánh đồng duyệt nội dung với gửi thành công.
- Tenant boundary có test âm cho từng vai trò và tài nguyên trọng yếu.
- Mọi advisory bảo mật còn mở có owner, mức độ và quyết định được ghi.

### Giai đoạn 3 — Một luồng email thật

**Khung tham khảo:** 4–8 tuần sau khi giai đoạn 1–2 được chấp nhận.
**Mục tiêu:** chứng minh một campaign có thể đi đến một kết quả bên ngoài và quay về dashboard.

**Phạm vi**

1. Tạo chiến dịch với đối tượng, mục tiêu, thông điệp chính, CTA, ngân sách và KPI.
2. Tạo và giao task cho các vai trò liên quan.
3. Dùng AI tạo email draft; người phụ trách sửa và gửi duyệt.
4. Người duyệt xác nhận nội dung/đối tượng; có preview và xác nhận cuối trước khi gửi.
5. Gửi vào địa chỉ thử nghiệm hoặc danh sách đã được phép gửi; ghi provider message ID.
6. Nhận webhook đã xác thực cho accepted/delivered/bounced và các engagement event provider hỗ trợ.
7. Hiển thị trạng thái/số liệu có nguồn và thời điểm; AI giải thích dữ liệu, không tự tạo số liệu.

**Yêu cầu thiết kế**

- Idempotency key cho lệnh gửi và webhook; retry không gửi trùng.
- Xác minh chữ ký webhook, lưu raw event tối thiểu cần thiết, loại sự kiện lặp và log theo workspace/campaign.
- Tách trạng thái gửi nội dung khỏi trạng thái phê duyệt; ghi audit trail cho ai duyệt, ai gửi và thời điểm.
- Có suppression/opt-out và quy tắc gửi an toàn; không gửi mặc định đến audience không rõ nguồn gốc.
- Quản lý API key bằng secret/config bảo vệ; không trả key ra UI/log.
- Bắt đầu với worker hiện có hoặc xử lý bền giản dị; chỉ thêm Celery/Redis/Temporal khi số liệu tải, retry hoặc throughput chứng minh cần thiết.

**Nghiệm thu**

- Một chiến dịch demo hoàn thành từ brief đến email được provider xác nhận.
- Lỗi provider, timeout, webhook sai chữ ký, event trùng và retry không tạo gửi trùng hoặc trạng thái sai.
- Dashboard chỉ hiển thị event thực nhận, có mẫu số/thời điểm và không gọi event “mở/nhấp” là chuyển đổi.
- Luồng được kiểm thử trong staging riêng, không dùng database khách hàng.

### Giai đoạn 4 — Pilot có kiểm soát

**Khung tham khảo:** 4–6 tuần.
**Mục tiêu:** kiểm chứng việc điều phối chiến dịch tiết kiệm công sức và tăng độ rõ ràng.

**Việc làm**

- Tuyển 3–5 nhóm agency; bắt đầu với một workspace và 2–3 campaign mỗi nhóm.
- Thu baseline công việc hiện tại trước khi dùng phần mềm; ghi nơi vẫn phải dùng spreadsheet hoặc chat ngoài hệ thống.
- Onboard theo cùng một kịch bản, theo dõi drop-off và mức trợ giúp.
- Thu phản hồi sau mỗi chiến dịch, không chỉ khảo sát cuối kỳ.
- Không mở rộng thêm kênh trong pilot trừ khi một nhu cầu lặp lại chặn việc hoàn tất campaign.

**Chỉ số cần đo**

- Tỷ lệ người dùng hoàn tất brief → task → duyệt → gửi mà không cần trợ giúp.
- Thời gian từ brief đến nội dung đầu tiên được duyệt; thời gian chờ khách duyệt.
- Tỷ lệ task đúng hạn; số campaign bị chặn; số lần quản lý phải nhắc tay.
- Giờ điều phối trên mỗi campaign so với baseline.
- Số lần cảnh báo ngân sách/KPI dẫn đến một hành động quản lý hữu ích và tỷ lệ cảnh báo sai.
- Send acceptance, delivery, bounce và webhook processing error riêng biệt.

**Cổng quyết định**

- Tiếp tục nếu người dùng quay lại, campaign thật được điều phối trong hệ thống và họ chỉ ra được thời gian/công việc giảm cụ thể.
- Chỉnh sản phẩm nếu họ chỉ dùng AI draft nhưng bỏ qua task, approval hoặc dashboard.
- Dừng mở rộng nếu workflow chính vẫn phải hoàn tất ngoài hệ thống hoặc số liệu không được tin.

Chỉ chốt mục tiêu số tuyệt đối sau khi có baseline pilot; trước đó mọi con số là giả thuyết.

### Giai đoạn 5 — Mở rộng sau pilot

**Khung tham khảo:** tháng 3–6 sau khi pilot đạt cổng quyết định.
**Mục tiêu:** mở rộng đúng điểm đau lặp lại, không quay lại mô hình “mỗi tuần thêm một phân hệ”.

**Thứ tự xem xét**

1. Cổng duyệt cho khách hàng: link duyệt, nhận xét theo phiên bản, deadline và nhắc việc.
2. Báo cáo tự động theo khách hàng/campaign với dữ liệu provider và metrics import có nguồn.
3. Connector social đầu tiên nếu nhiều pilot agency yêu cầu cùng một kênh; làm rõ token expiry, permissions, giới hạn API và retry trước khi cam kết “đăng bài thật”.
4. Tích hợp dữ liệu analytics/ad platform khi có use case đo attribution rõ ràng.
5. Chỉ xem xét CRM/journey khi pilot chứng minh nhóm hiện mất công vì quản lý audience và lifecycle, không chỉ vì cần điều phối công việc.

**Nguyên tắc mở rộng**

- Mỗi connector là một năng lực rõ ràng: preview, schedule, publish, status sync, metrics import; không quảng bá phần chưa hoàn tất.
- Có release gate cho API provider và test sandbox trước dữ liệu thật.
- Giữ một canonical event model để tránh mỗi kênh tạo một hệ status không đồng bộ.

### Giai đoạn 6 — Sẵn sàng vận hành và tăng quy mô

**Khung tham khảo:** tháng 6–12, tùy kết quả pilot và quy mô sử dụng.
**Mục tiêu:** chứng minh khả năng vận hành có trách nhiệm trước khi bán rộng.

- Hoàn thiện lưu trữ production, migration, backup/restore, kế hoạch rollback và kiểm tra phục hồi định kỳ.
- Đo concurrency, kích thước DB, latency và chi phí; đặt ngưỡng cần nâng hạ tầng bằng số liệu.
- Thêm observability cho request, job, provider event, lỗi tenant và tỷ lệ retry; không ghi secret hoặc nội dung nhạy cảm không cần thiết.
- Xây quy trình quản trị workspace, hỗ trợ người dùng, xử lý export/delete và giới hạn retention theo yêu cầu thực tế.
- Nếu thu phí được xác nhận: thử mô hình gói theo workspace/campaign/user; không xây billing trước nhu cầu.
- Kiểm tra tên thương hiệu/domain và phạm vi pháp lý trước public launch; coi đây là việc cần xác minh hiện hành.

## 5. Hướng kỹ thuật và ranh giới phạm vi

### Giữ ổn định trong giai đoạn MVP

- Giữ React/Vite, FastAPI và các domain model campaign/task/content hiện có.
- Dùng SQLite cho local/demo nếu dữ liệu có thể tạo lại; chưa gọi cấu hình đó là production-ready.
- Chọn một database production sau kiểm thử concurrency, migration và restore; không mặc định PostgreSQL đã được kiểm chứng chỉ vì URL có thể cấu hình.
- Dùng API provider trực tiếp với retry/idempotency phù hợp; chỉ thêm hàng đợi phân tán khi có bằng chứng tải hoặc yêu cầu durability.
- AI là trợ lý: mọi nội dung cần human approval; số liệu KPI lấy từ nguồn đã xác nhận.

### Để sau khi có bằng chứng nhu cầu

- CRM/CDP, journey builder, attribution đa chạm và audience segmentation.
- Nhiều connector mạng xã hội cùng lúc.
- Celery/Redis/Temporal, semantic cache hoặc microservices.
- Gói trả phí, billing và enterprise multi-region.

Các hạng mục này có thể được xem xét lại khi dữ liệu pilot hoặc tải thực tế chứng minh lợi ích vượt chi phí.

## 6. Quản lý quyết định, rủi ro và trạng thái

### Rủi ro cần theo dõi

| Rủi ro | Ảnh hưởng | Cách xử lý |
|---|---|---|
| Phạm vi nhiều phân hệ làm mất luồng chính | Người dùng không hiểu lợi ích, khó hoàn tất campaign | Giữ một persona/luồng ưu tiên; yêu cầu evidence trước khi thêm feature. |
| PUBLISHED bị hiểu là đã đăng/gửi thật | Báo cáo sai, mất niềm tin | Đổi semantics và chỉ xác nhận khi có provider event phù hợp. |
| Danh sách không phân trang | `GET /campaigns`, `/contents`, `/tasks` trả toàn bộ kết quả; chậm và nặng khi dữ liệu lớn | Thêm `limit`/`offset` + tổng số; đo trước khi chọn cursor hay offset. |
| Postgres trên Render chưa có quy trình migration | `create_all()` không sửa bảng đã có; thêm cột mới dễ bị bỏ sót ở production | Ghi checklist `ALTER TABLE` cho mỗi thay đổi schema; cân nhắc Alembic. |
| AI không tự trợ được qua Worker | Mọi lời gọi AI thật trả `524` sau ~100 giây | Đã sửa bằng cách gọi thẳng Render (đo được 237 giây, HTTP 200); cần theo dõi để không vô tình gom nhóm AI về Worker. |
| `compliance_score` bị đọc là điểm tự chấm của AI | Người dùng tin điểm tuyệt đối rồi bỏ qua duyệt | Đo bằng `ComplianceScanner.scan`; trả `None` khi không chấm được. Xem [AI_ETHICS_AND_HUMAN_OVERSIGHT.md](AI_ETHICS_AND_HUMAN_OVERSIGHT.md) mục 3. |
| Dependency audit chỉ cảnh báo | Dependency có advisory vẫn qua CI | Phân loại advisory, đặt ngưỡng chặn phù hợp, ghi waiver có thời hạn. |
| Benchmark AI bị diễn giải thành đảm bảo chung | Tuyên bố vượt phạm vi dữ liệu thử | Ghi sample, môi trường, commit, mẫu số và giới hạn ở mọi báo cáo. |
| Hai màn hình hiển thị điểm sức khỏe theo quy tắc/ngưỡng và nhãn khác nhau | Người dùng có thể hiểu điểm Command Center và AI Doctor là cùng một phép đo | Thống nhất semantics hoặc đặt tên/phạm vi rõ; xác nhận bằng usability test trước khi quảng bá chỉ số chung. |
| Provider gửi lặp hoặc webhook đến sai thứ tự | Email trùng/sai trạng thái campaign | Idempotency, deduplication, event timestamp và state transition có kiểm soát. |
| Pilot không đại diện nhóm mục tiêu | Tối ưu sai quy trình | Chọn nhiều vai trò/agency; ghi đặc tính mẫu và giới hạn ngoại suy. |

### Quy tắc cập nhật roadmap

- Rà lại sau discovery, sau mỗi pilot wave và ít nhất mỗi tháng khi còn phát triển.
- Mỗi epic ghi: vấn đề người dùng, evidence, owner, trạng thái, acceptance criteria, rủi ro và quyết định tiếp tục/dừng.
- Mọi thay đổi phạm vi lớn ghi vào ADR hoặc phần quyết định của roadmap.
- Không chuyển hạng mục từ “đề xuất” sang “đã hiện thực” nếu chưa có bằng chứng từ source/test/deployment.
- Kết quả pilot và benchmark luôn có ngày, commit, môi trường và mẫu số.

## 7. Việc cần bắt đầu ngay

1. Hoàn thiện đợt chuẩn hóa tài liệu đang thực hiện; không chỉnh sửa PDF V8/V9 đã nộp.
2. Chốt kịch bản usability 5 người và chuẩn bị prototype dashboard/campaign flow.
3. Tạo backlog P0 cho trạng thái xuất bản, độ bền lưu trữ Cloudflare và dependency advisories.
4. Sau khi giai đoạn 1–2 qua cổng nghiệm thu, đặc tả hợp đồng email provider/webhook và bắt đầu một vertical slice.
5. Chốt pilot cohort và baseline outcome trước khi bật tính năng gửi cho khách hàng thật.

## 8. Liên kết nguồn

- [Mục lục tài liệu](README.md)
- [Hướng dẫn kiểm thử và bằng chứng CI](TESTING.md)
- [Kiến trúc hiện tại](ARCHITECTURE.md)
- [Báo cáo benchmark AI có giới hạn phạm vi](AI_EVALUATION_REPORT.md)
- [Hướng dẫn lưu trữ Cloudflare](../cloudflare/README.md)
- [CI hiện tại](https://github.com/hieu-kiien/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/actions)
