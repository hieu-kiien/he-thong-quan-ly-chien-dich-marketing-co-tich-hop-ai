Hệ thống quản lý bán hàng có tích hợp AI
> **Metadata:** `document_id=BAI03-PROJECT-BRIEF`; `project_id=BAI03-SALES-AI`; `status=CANONICAL`; đây là nguồn yêu cầu gốc, không phải bằng chứng triển khai.

1. Mô tả bài toán

Các cửa hàng bán lẻ cần quản lý sản phẩm, khách hàng, hóa đơn, doanh thu và tồn kho hằng ngày. Nếu quản lý bằng sổ sách hoặc bảng tính rời rạc, nhân viên dễ nhập sai dữ liệu, khó theo dõi tồn kho và mất nhiều thời gian tổng hợp doanh thu. Đề tài yêu cầu xây dựng hệ thống quản lý bán hàng giúp nhân viên bán hàng thao tác nhanh, chủ cửa hàng theo dõi tình hình kinh doanh và sử dụng AI để hỗ trợ tư vấn sản phẩm, sinh báo cáo hoặc hỏi đáp dữ liệu bán hàng.
2. Mục tiêu

- Xây dựng hệ thống quản lý sản phẩm, khách hàng, hóa đơn, nhập xuất tồn và doanh thu.
- Tích hợp AI tạo sinh để hỗ trợ tư vấn sản phẩm, sinh nhận xét doanh thu và trả lời câu hỏi quản trị bằng ngôn ngữ tự nhiên.
- Sử dụng AI trong SDLC để phân tích nghiệp vụ bán hàng, thiết kế CSDL, sinh giao diện CRUD, viết API, kiểm thử và viết tài liệu.
- Hoàn thiện sản phẩm có dữ liệu mẫu, phân quyền, báo cáo và demo được trong môi trường local hoặc cloud.

3. Yêu cầu chức năng
3.1. Chức năng quản lý
1. Đăng nhập, đăng xuất và phân quyền quản trị viên, nhân viên bán hàng, chủ cửa hàng.
2. Quản lý sản phẩm: mã, tên, nhóm hàng, giá bán, giá nhập, tồn kho, trạng thái.
3. Quản lý khách hàng: thông tin liên hệ, lịch sử mua hàng, nhóm khách hàng.
4. Lập hóa đơn bán hàng, tính tổng tiền, giảm giá, ghi nhận phương thức thanh toán.
5. Quản lý nhập hàng và cập nhật tồn kho.
6. Tìm kiếm, lọc sản phẩm, khách hàng, hóa đơn theo thời gian và trạng thái.
7. Thống kê doanh thu theo ngày, tháng, nhóm hàng, sản phẩm bán chạy.
8. Xuất báo cáo doanh thu hoặc danh sách hóa đơn ra PDF/Excel/CSV.

3.2. Chức năng AI
1. Chatbot tư vấn sản phẩm: nhận nhu cầu khách hàng, tra dữ liệu sản phẩm còn hàng và gợi ý sản phẩm phù hợp.
2. AI sinh báo cáo doanh thu: từ dữ liệu doanh thu, tồn kho, sản phẩm bán chạy, sinh nhận xét ngắn gọn và khuyến nghị nhập hàng.
3. Hỏi đáp dữ liệu bán hàng: chủ cửa hàng đặt câu hỏi như "Tháng này mặt hàng nào bán chậm?" và AI trả lời dựa trên dữ liệu hệ thống.

4. Yêu cầu kỹ thuật

- Backend: Python FastAPI, Flask hoặc Django.
- Frontend: React, Vue, HTML/CSS/JavaScript hoặc template engine.
- CSDL: SQLite cho bản demo; khuyến khích MySQL/PostgreSQL nếu nhóm có năng lực.
- AI Engine: OpenAI API, Gemini API, Claude API, Hugging Face hoặc Ollama.
- Prompt template tách riêng trong thư mục `prompts/`.
- API key đặt trong `.env`, cung cấp `.env.example`.
- Có test case cho hóa đơn, tồn kho, báo cáo và chức năng AI.

5. Dữ liệu đầu vào, đầu ra và dữ liệu hệ thống

- Dữ liệu chính: người dùng, vai trò, sản phẩm, danh mục, khách hàng, hóa đơn, chi tiết hóa đơn, phiếu nhập, tồn kho.
- Đầu vào quản lý: form sản phẩm, khách hàng, hóa đơn, phiếu nhập, bộ lọc thời gian.
- Đầu vào AI: câu hỏi người dùng, danh sách sản phẩm, dữ liệu doanh thu, dữ liệu tồn kho.
- Đầu ra quản lý: bảng dữ liệu, hóa đơn, dashboard, file xuất.
- Đầu ra AI: câu tư vấn, báo cáo doanh thu dạng Markdown, gợi ý hành động.

Ví dụ dữ liệu mẫu: `Sản phẩm: Tai nghe Bluetooth A1, nhóm Phụ kiện, giá 350000, tồn kho 12, mô tả Pin 20 giờ`.

Prompt mẫu:

System: Bạn là trợ lý AI cho hệ thống quản lý bán hàng. Chỉ tư vấn dựa trên dữ liệu sản phẩm và tồn kho được cung cấp. Nếu thiếu dữ liệu, hãy nói rõ.
User: Khách hàng cần tai nghe dưới 500000 đồng, pin lâu, còn hàng. Dữ liệu sản phẩm: {{product_table}}. Hãy gợi ý tối đa 3 sản phẩm và giải thích ngắn gọn.


Khi gọi AI, không gửi thông tin nhạy cảm như số điện thoại đầy đủ hoặc dữ liệu thanh toán của khách hàng nếu không cần thiết.

6. Hướng dẫn sử dụng AI trong từng giai đoạn SDLC

 Giai đoạn 1: Phân tích yêu cầu và thiết kế hệ thống (Bài KT1)

- Dùng AI để phân tích quy trình bán hàng, nhập hàng, lập hóa đơn và quản lý tồn kho.
- Dùng AI gợi ý actor, use case, yêu cầu chức năng, yêu cầu phi chức năng.
- Dùng AI thiết kế ERD cho sản phẩm, hóa đơn, khách hàng, phiếu nhập.
- Dùng AI đề xuất vị trí tích hợp AI: tư vấn sản phẩm, sinh báo cáo, hỏi đáp doanh thu.
- Dùng AI sinh wireframe màn hình bán hàng, quản lý sản phẩm và dashboard.

 Giai đoạn 2: Xây dựng chức năng quản lý (Bài KT2)

- Dùng AI sinh cấu trúc dự án, model, schema, API CRUD và form nhập liệu.
- Dùng AI sinh truy vấn tính doanh thu, tồn kho, sản phẩm bán chạy.
- Dùng AI debug lỗi cập nhật tồn kho khi hủy hoặc sửa hóa đơn.
- Lưu minh chứng prompt và phản hồi AI trong thư mục tài liệu dự án.

 Giai đoạn 3: Tích hợp AI, tối ưu prompt và kiểm thử (Bài KT3)

- Dùng AI thiết kế prompt tư vấn sản phẩm và prompt sinh báo cáo doanh thu.
- Dùng AI sinh code gọi API AI, xử lý timeout, rate limit và response sai định dạng.
- Dùng AI sinh test case cho hóa đơn, tồn kho, chatbot tư vấn và báo cáo AI.
- So sánh ít nhất 3 phiên bản prompt để giảm tư vấn sai sản phẩm hết hàng.

 Giai đoạn 4: Hoàn thiện, triển khai và báo cáo (Bài thi cuối kỳ)

- Dùng AI sinh README, hướng dẫn nhập dữ liệu mẫu và kịch bản demo bán hàng.
- Dùng AI review code, kiểm tra bảo mật API key và phân quyền dữ liệu.
- Dùng AI tạo slide trình bày hai vai trò của AI trong dự án.
- Dùng AI hỗ trợ đóng gói Docker hoặc hướng dẫn triển khai.
7. Mức độ khó

Trung bình: Hệ thống có nhiều thực thể nghiệp vụ phổ biến, yêu cầu xử lý tồn kho và báo cáo. Chức năng AI ở mức hỏi đáp/sinh báo cáo dựa trên dữ liệu hệ thống, chưa bắt buộc RAG phức tạp nhưng cần kiểm soát dữ liệu đầu vào và lỗi phản hồi.



Hướng dẫn chấm theo tiêu chí

Tiêu trí chấm bài kiểm tra số 1 (Tuần 4 phải nộp):

1. Hoàn thiện chức năng hệ thống: Các chức năng quản lý và chức năng AI hoạt động đầy đủ, ổn định, đúng yêu cầu. (1 điểm)
2. Tích hợp được chức năng AI vào hệ thống: Chức năng AI chạy trong hệ thống, phục vụ nghiệp vụ cụ thể, không tách rời sản phẩm. (1 điểm)
3. Phân tích đúng bài toán quản lý: Xác định rõ bối cảnh, người dùng, dữ liệu, quy trình nghiệp vụ và vấn đề cần giải quyết. (1 điểm)
4. Cấu trúc dự án hợp lý: Dự án tổ chức rõ ràng theo frontend/backend/database/config/docs hoặc cấu trúc phù hợp framework. (1 điểm)
5. Chất lượng kiến trúc và mã nguồn: Code rõ ràng, module hóa, dễ bảo trì, tuân thủ quy ước của framework/ngôn ngữ. (1 điểm)
6. Kết nối API/model AI đúng cách: Gọi được OpenAI/Gemini/Claude/Hugging Face/Ollama hoặc mô hình tương đương; bảo vệ API key. (1 điểm)
7. Xác định đầy đủ yêu cầu chức năng: Liệt kê chức năng quản lý cốt lõi phù hợp với đề tài, có mô tả đầu vào, xử lý và đầu ra. (1 điểm)
8. Xây dựng chức năng đăng nhập và phân quyền: Có xác thực người dùng, phân quyền vai trò và bảo vệ các chức năng quan trọng. (1 điểm)
9. Chất lượng cơ sở dữ liệu: CSDL hợp lý, dữ liệu nhất quán, có ràng buộc, dữ liệu mẫu và khả năng sao lưu/khôi phục cơ bản. (1 điểm)
10. Thiết kế prompt có hệ thống: Prompt tách khỏi code, có system/user prompt, ràng buộc output và hướng dẫn xử lý dữ liệu. (1 điểm)

Tiêu trí chấm bài kiểm tra số 2 (Tuần 6 phải nộp):

11. Xác định yêu cầu phi chức năng: Nêu yêu cầu về bảo mật, hiệu năng, khả dụng, sao lưu, phân quyền và trải nghiệm người dùng. (1 điểm)
12. Hoàn thiện CRUD nghiệp vụ chính: Các chức năng thêm, xem, sửa, xóa dữ liệu chính hoạt động đúng. (1 điểm)
13. Chất lượng giao diện và trải nghiệm người dùng: Giao diện dễ dùng, nhất quán, responsive ở mức phù hợp, có phản hồi thao tác và thông báo lỗi. (1 điểm)
14. Tối ưu prompt qua thử nghiệm: Có ít nhất 3 vòng thử nghiệm hoặc so sánh prompt/model, ghi nhận kết quả và cải tiến. (1 điểm)
15. Thiết kế actor và use case: Xác định actor chính, use case chính và có sơ đồ Use Case hoặc mô tả tương đương. (1 điểm)
16. Xây dựng chức năng tìm kiếm và lọc: Cho phép tìm kiếm, lọc, sắp xếp dữ liệu theo tiêu chí phù hợp. (1 điểm)
17. Chất lượng chức năng AI: Kết quả AI hữu ích, đúng ngữ cảnh, có kiểm soát sai lệch, có giới hạn và cảnh báo rõ. (1 điểm)
18. Sử dụng dữ liệu hệ thống trong chức năng AI: AI khai thác dữ liệu phù hợp từ CSDL, file hoặc báo cáo; có kiểm soát quyền truy cập dữ liệu. (1 điểm)
19. Thiết kế cơ sở dữ liệu: Có ERD, bảng dữ liệu, khóa chính/khóa ngoại, ràng buộc và giải thích quan hệ. (1 điểm)
20. Xây dựng thống kê/báo cáo cơ bản: Có báo cáo hoặc dashboard phục vụ nghiệp vụ của hệ thống. (1 điểm)

Tiêu trí chấm bài kiểm tra số 3 (Tuần 8 phải nộp):

21. Bảo mật, quyền riêng tư và đạo đức AI: Bảo vệ tài khoản, phân quyền dữ liệu, không lộ API key, cân nhắc dữ liệu nhạy cảm khi gọi AI. (1 điểm)
22. Hiển thị kết quả AI rõ ràng: Kết quả AI được trình bày dễ hiểu, có định dạng phù hợp và có cảnh báo khi cần. (1 điểm)
23. Thiết kế kiến trúc hệ thống: Mô tả kiến trúc frontend, backend, database, AI service và luồng dữ liệu chính. (1 điểm)
24. Thiết kế giao diện rõ ràng, dễ sử dụng: Giao diện nhất quán, dễ thao tác, có thông báo lỗi và phản hồi người dùng. (1 điểm)
25. Hiệu năng và độ ổn định: Ứng dụng phản hồi hợp lý, xử lý được dữ liệu demo, có cơ chế tránh lỗi lặp lại hoặc lỗi do AI. (1 điểm)
26. Xử lý lỗi và giới hạn AI: Xử lý timeout, rate limit, response rỗng/sai định dạng, dữ liệu quá dài, lỗi model. (1 điểm)
27. Xác định vị trí ứng dụng AI: Chọn chức năng AI hợp lý, gắn với dữ liệu và nhu cầu thực tế của hệ thống. (1 điểm)
28. Kết nối và thao tác CSDL ổn định: Lưu, đọc, cập nhật, xóa dữ liệu chính xác; có dữ liệu mẫu để demo. (1 điểm)
29. Triển khai và đóng gói: Có hướng dẫn triển khai, cấu hình môi trường, dữ liệu mẫu; khuyến khích Docker hoặc cloud demo. (1 điểm)
30. Kiểm thử chức năng quản lý và chức năng AI: Có test case, manual test hoặc script test; bao gồm trường hợp đúng, sai và biên. (1 điểm)

Tiêu trí chấm Thi hết môn (kết thúc 9 tuần phải nộp):

31. Thiết kế prompt và luồng gọi AI sơ bộ: Có system prompt, user prompt mẫu, input/output format, ràng buộc và giới hạn. (1 điểm)
32. Xử lý lỗi cơ bản: Xử lý input sai, dữ liệu thiếu, lỗi truy vấn, lỗi phân quyền; không để ứng dụng crash. (1 điểm)
33. Báo cáo kỹ thuật đầy đủ: Báo cáo mô tả phân tích, thiết kế, triển khai, kiểm thử, chức năng AI và vai trò của AI trong SDLC. (1 điểm)
34. Review code và cải thiện chất lượng bằng AI: Có minh chứng dùng AI để review code, phát hiện lỗi, refactor hoặc cải thiện bảo mật. (1 điểm)
35. Minh chứng sử dụng AI trong phân tích và thiết kế: Lưu prompt, phản hồi AI và nhận xét cách sinh viên kiểm chứng/chỉnh sửa kết quả AI. (1 điểm)
36. Minh chứng sử dụng AI khi lập trình: Có nhật ký prompt, phản hồi AI, phần code được hỗ trợ và phần sinh viên đã kiểm tra/chỉnh sửa. (1 điểm)
37. Thuyết trình và demo: Demo mạch lạc, trình bày rõ chức năng quản lý, chức năng AI, minh chứng sử dụng AI và trả lời câu hỏi tốt. (1 điểm)
38. Tích hợp chức năng AI với trải nghiệm người dùng: Luồng sử dụng AI tự nhiên, hữu ích, không gây nhầm lẫn với chức năng quản lý chính. (1 điểm)
39. Tài liệu phân tích thiết kế: Tài liệu rõ ràng, có cấu trúc, có kế hoạch triển khai các giai đoạn tiếp theo. (1 điểm)
40. Quản lý mã nguồn và tài liệu chạy thử: Có README, hướng dẫn cài đặt/chạy, .env.example, commit rõ ràng. (1 điểm)
