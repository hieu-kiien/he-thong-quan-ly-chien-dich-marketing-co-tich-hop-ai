# KỊCH BẢN THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN (7 PHÚT)

* **Học phần:** Ứng dụng trí tuệ nhân tạo (AIA331)
* **Đề tài 80300:** Hệ thống quản lý chiến dịch marketing có tích hợp AI (MarketFlow)
* **Nhóm thực hiện:** Nhóm 25 (Vũ Hiếu Kiên, Nguyễn Hải Đăng)
* **Giảng viên hướng dẫn:** TS. Nguyễn Tuấn Anh
* **Phím điều khiển trên file `slides/index.html`:**
  * `→` hoặc `Space`: Qua slide tiếp theo
  * `←`: Quay lại slide trước
  * `F`: Bật/tắt toàn màn hình
  * `N`: Bật/tắt khung nhắc lời thoại bên dưới

## Bố cục thời gian 12 Slide (07:00)

| Slide | Nội dung chính | Thời lượng | Mốc giờ | Minh họa trên slide |
| :---: | :--- | :---: | :---: | :--- |
| **01** | Giới thiệu đề tài 80300 và nhóm thực hiện | `00:20` | `00:00 - 00:20` | Thông tin đề tài và 4 thông số thực tế của dự án |
| **02** | Bài toán thực tế và mục tiêu hệ thống | `00:30` | `00:20 - 00:50` | 3 vấn đề khi làm thủ công và hướng giải quyết |
| **03** | Phân quyền người dùng và 7 kênh truyền thông | `00:30` | `00:50 - 01:20` | Vai trò `MARKETER` / `MANAGER` và bảng 7 kênh |
| **04** | Kiến trúc 3 dịch vụ và cơ sở dữ liệu 14 bảng | `00:40` | `01:20 - 02:00` | Sơ đồ `React` - `FastAPI (/mcp)` - `AI Runner` |
| **05** | **[VIDEO 1]** Quản lý chiến dịch, KPI và nhập CSV 2 bước | `00:45` | `02:00 - 02:45` | Video `loop-01-dashboard-kpi.mp4` |
| **06** | **[VIDEO 2]** Soạn bài, quét từ cấm và duyệt bài | `00:45` | `02:45 - 03:30` | Video `loop-02-hitl-approval.mp4` |
| **07** | Cách nối Trợ lý AI qua 14 công cụ MCP | `00:35` | `03:30 - 04:05` | 9 hàm chỉ đọc dữ liệu và 5 hàm tạo thẻ đề xuất |
| **08** | **[VIDEO 3]** Trợ lý AI chạy thực tế trên giao diện | `00:50` | `04:05 - 04:55` | Video `loop-03-ai-copilot-mcp.mp4` |
| **09** | Thử nghiệm và sửa System Prompt qua 4 phiên bản | `00:40` | `04:55 - 05:35` | Kết quả chấm tự động trên 8 kịch bản (`TC01`-`TC08`) |
| **10** | **[VIDEO 4]** Kiểm thử 151 bài test và chặn lệnh vượt quyền | `00:35` | `05:35 - 06:10` | Video `loop-04-guardrails-eval.mp4` |
| **11** | Sử dụng AI trong quá trình làm đồ án (SDLC) | `00:30` | `06:10 - 06:40` | 4 lỗi thực tế do code AI sinh ra và cách nhóm tự sửa |
| **12** | Kết quả triển khai trên VPS và các hạn chế hiện tại | `00:20` | `06:40 - 07:00` | Tên miền `marketing.kienhieu.id.vn` và chuyển sang Demo |

## Lời nói trực tiếp cho từng Slide

### Slide 01: Trang bìa (`00:00 - 00:20` | 20 giây)
Em chào thầy và hội đồng ạ. Em đại diện Nhóm 25 xin trình bày đề tài 80300: Hệ thống quản lý chiến dịch marketing có tích hợp AI. Phần trình bày của em gồm 2 nội dung chính: đầu tiên là các chức năng quản lý chiến dịch, duyệt bài, nhập số liệu, và tiếp theo là cách nhóm nối Trợ lý AI vào cơ sở dữ liệu của hệ thống.

### Slide 02: Bài toán thực tế và mục tiêu (`00:20 - 00:50` | 30 giây)
Khi tìm hiểu việc chạy chiến dịch marketing ở các nhóm nhỏ, bọn em thấy có 3 bất cập chính khi làm thủ công. Một là kế hoạch, bài viết và file số liệu CSV nằm ở nhiều nơi nên khi tổng hợp rất dễ nhầm số. Hai là lúc viết bài nhân viên dễ dùng các từ quảng cáo quá đà bị cấm, hoặc tự đăng bài khi chưa có người duyệt. Ba là nếu dùng các trang chat AI bên ngoài thì phải tự copy thông tin chiến dịch sang, và khi chiến dịch chưa có số liệu thì AI rất hay tự bịa ra con số. Vì vậy nhóm xây dựng MarketFlow để gom toàn bộ dữ liệu về một web chung và cho AI đọc trực tiếp dữ liệu thật từ hệ thống.

### Slide 03: Phân quyền và 7 kênh truyền thông (`00:50 - 01:20` | 30 giây)
Hệ thống quản lý nội dung và chi phí trên 7 kênh gồm Facebook, Instagram, TikTok, Zalo OA, Email, Google Ads và Website. Về phân quyền, hệ thống chia làm 2 vai trò: Nhân viên (`MARKETER`) chỉ được sửa bài viết, lịch đăng và nhập số liệu trên đúng chiến dịch mà mình phụ trách. Còn Quản lý (`MANAGER`) nắm ngân sách, cài đặt danh sách từ cấm và duyệt bài cho nhân viên.

### Slide 04: Kiến trúc hệ thống và CSDL 14 bảng (`01:20 - 02:00` | 40 giây)
Về kiến trúc, hệ thống gồm 3 phần: Giao diện viết bằng React 18 và TypeScript, máy chủ chính dùng FastAPI kết nối cơ sở dữ liệu PostgreSQL 14 bảng, và một dịch vụ `ai-runner` tách riêng để gọi AI. Lý do bọn em tách riêng `ai-runner` là vì mỗi tiến trình gọi AI ngốn khoảng 490 MB RAM và mất vài chục giây chờ phản hồi. Việc tách riêng và xếp hàng chạy từng lượt giúp máy chủ chính luôn phản hồi nhanh các thao tác quản lý.

### Slide 05: [VIDEO 1] Quản lý chiến dịch, KPI và nhập CSV 2 bước (`02:00 - 02:45` | 45 giây)
Trên màn hình là video chức năng quản lý chỉ số quảng cáo của chiến dịch Cold Brew. Người dùng chỉ cần nhập 4 số gốc là lượt xem, lượt nhấp, chuyển đổi và chi phí. Máy chủ sẽ tự tính các chỉ số CTR, CVR, CPC, CPA để tránh sai công thức. Khi tải file báo cáo CSV lên, hệ thống chạy qua 2 bước: bước Xem trước sẽ kiểm tra điều kiện số lượt chuyển đổi không được lớn hơn lượt nhấp và lượt nhấp không được lớn hơn lượt xem, báo rõ các dòng lỗi để người dùng kiểm tra rồi mới bấm lưu vào cơ sở dữ liệu.

### Slide 06: [VIDEO 2] Soạn bài, quét từ cấm và duyệt bài (`02:45 - 03:30` | 45 giây)
Video thứ hai minh họa luồng gửi duyệt và phê duyệt bài viết. Ngay khi nhân viên bấm Gửi duyệt, hệ thống tự quét nội dung bài viết với bảng từ cấm của thương hiệu. Ví dụ bài viết có cụm 'cam kết 100%' sẽ bị gắn cảnh báo ngay cho người duyệt thấy. Ở màn hình duyệt bài, hệ thống kiểm tra người tạo bài phải khác người duyệt bài: kể cả tài khoản Quản lý nếu tự viết bài thì cũng không thể tự bấm duyệt bài của chính mình. Các bài đã duyệt xong sẽ bị khóa không cho xóa để giữ lại lịch sử.

### Slide 07: Cách nối Trợ lý AI qua 14 công cụ MCP (`03:30 - 04:05` | 35 giây)
Sang phần tích hợp AI: để AI lấy được dữ liệu thật mà không làm hỏng cơ sở dữ liệu, nhóm tạo 14 hàm công cụ theo giao thức MCP gắn tại đường dẫn nội bộ `/mcp`. Trong đó có 9 hàm chỉ đọc giúp AI tra cứu chiến dịch, bài viết, chỉ số KPI và kiểm tra từ cấm. Còn 5 hàm tạo đề xuất bắt đầu bằng chữ `propose_` chỉ được tạo bản ghi ở trạng thái `PROPOSED` trong bảng tạm. Hệ thống không cấp cho AI bất kỳ hàm nào để xóa dữ liệu hay tự duyệt bài.

### Slide 08: [VIDEO 3] Trợ lý AI chạy thực tế trên giao diện (`04:05 - 04:55` | 50 giây)
Video trên slide là một lượt dùng Trợ lý AI thực tế. Người dùng mở ngăn kéo AI bên phải, chọn mô hình trong danh sách 13 mô hình miễn phí và yêu cầu phân tích chiến dịch kèm viết bài nháp. Giao diện hiển thị trực tiếp các hàm mà AI đang gọi gồm đọc thông tin thương hiệu, lấy thống kê KPI, kiểm tra từ cấm và tạo bản nháp. Kết quả hiện ra thành một Thẻ đề xuất ở cột phải. Chỉ khi người dùng kiểm tra và bấm nút Áp dụng thì bài nháp mới được lưu vào bảng nội dung.

### Slide 09: Thử nghiệm và sửa System Prompt qua 4 phiên bản (`04:55 - 05:35` | 40 giây)
Để đánh giá chất lượng câu trả lời của AI, nhóm viết script chấm tự động trên 8 kịch bản kiểm tra qua 4 lần sửa System Prompt. Ở Bản 1 cơ sở, AI đạt 6 trên 8 kịch bản do viết kịch bản TikTok quá dài hơn 3.600 ký tự và tự bịa thêm số liệu. Sang Bản 2, khi nhóm thêm các câu dặn dò an toàn quá dài, AI lại bắt chước viết kèm một đoạn cảnh báo dài ở cuối mỗi bài làm bài đăng Facebook và TikTok bị lố số ký tự, tụt xuống 5 trên 8. Đến Bản 4 hiện tại, nhóm cắt bỏ các câu rào đón thừa và đặt giới hạn ký tự cứng cho từng kênh thì đạt 7 trên 8 kịch bản, chỉ còn trượt nhẹ 1 câu do AI tự lấy một con số ví dụ khi gợi ý.

### Slide 10: [VIDEO 4] Kiểm thử 151 bài test và chặn lệnh vượt quyền (`05:35 - 06:10` | 35 giây)
Về kiểm thử, dự án có 151 bài test tự động gồm 104 bài test Backend Pytest, 18 bài test dịch vụ `ai-runner` và 29 bài test giao diện Playwright. Như trong video bên phải, khi thử nhập câu lệnh yêu cầu AI bỏ qua quy tắc để đọc file mật khẩu hệ thống `/etc/passwd` và tự duyệt hết bài viết, AI từ chối ngay vì tiến trình chạy AI đã bị tắt quyền chạy lệnh hệ điều hành và không có công cụ duyệt bài.

### Slide 11: Sử dụng AI trong quá trình làm đồ án (SDLC) (`06:10 - 06:40` | 30 giây)
Trong quá trình làm đồ án, nhóm có dùng công cụ AI để hỗ trợ viết khung code và test, nhưng qua kiểm tra thực tế nhóm đã phát hiện và tự sửa 4 lỗi lớn do code AI sinh ra. Đầu tiên là code AI không giới hạn số tiến trình chạy song song làm tràn RAM VPS, nhóm phải đo lại và đặt hàng đợi chạy tuần tự từng lượt. Tiếp theo là thay khóa tĩnh dùng chung ở cổng `/mcp` bằng token tạm 10 phút theo đúng người đang đăng nhập. Ngoài ra nhóm cũng đổi từ `EventSource` sang `fetch` stream để truyền được token đăng nhập, đồng thời chặn cổng `/mcp` trên Nginx không cho bên ngoài gọi vào.

### Slide 12: Tổng kết, hạn chế hiện tại và chuyển sang Demo (`06:40 - 07:00` | 20 giây)
Hiện hệ thống đang chạy trực tuyến trên VPS tại địa chỉ `marketing.kienhieu.id.vn`. Điểm hạn chế hiện tại là do VPS chỉ có 2,5 GB RAM và dùng các mô hình miễn phí nên các câu hỏi AI phải xếp hàng xử lý tuần tự, mất khoảng 20 đến 60 giây mỗi lượt. Em xin cảm ơn thầy và hội đồng đã lắng nghe, sau đây em xin phép mở hệ thống để demo trực tiếp ạ.
