# IT Thesis Research & Documentation Engineer V3.0

Đây là bản mở rộng của skill Visual Designer V2.0. Media/LaTeX vẫn được giữ nguyên, nhưng trọng tâm mới là **nghiên cứu, thiết kế và chứng minh toàn bộ dự án CNTT**.

## Skill làm gì?

Khi đưa repository/project/report vào, skill được hướng dẫn để:
1. đọc yêu cầu môn học và template trường;
2. kiểm kê source of truth và xác định starting point;
3. nghiên cứu domain, related work và các hệ tương tự;
4. xây requirements + quality attributes;
5. lập traceability requirement -> design -> code -> test -> evidence;
6. xây architecture documentation nhiều view + ADR;
7. tài liệu hóa database, AI, security, operations;
8. thiết kế kế hoạch test/evaluation/reproducibility;
9. thiết kế cấu trúc chương và lập luận của báo cáo;
10. cuối cùng mới tạo figure/table/media research-grade và compile LaTeX.

## Cài đặt

Upload file ZIP chứa thư mục skill vào môi trường Agent Skills/ChatGPT Skills hỗ trợ custom skills.

## Dùng hiệu quả

Ví dụ prompt:

> Hãy dùng skill này nghiên cứu toàn bộ repo của tôi. Trước tiên lập Project Evidence Map, starting-point declaration, research questions, related-work matrix, requirement traceability và kế hoạch evaluation. Sau đó mới đề xuất cấu trúc báo cáo LaTeX và bộ hình cần có. Không được coi nội dung trong báo cáo là implemented nếu repo không chứng minh được.

Hoặc:

> Rà soát Chương 1-5 của báo cáo theo research-grade mode. Chỉ ra claim nào thiếu evidence, requirements nào không trace được tới test, design decision nào chưa có rationale, và evaluation nào mới chỉ là kế hoạch.

## Nguyên tắc quan trọng

Skill phân biệt rõ EXISTING / IMPLEMENTED / DESIGNED / PROPOSED / DEMONSTRATED / TESTED / MEASURED / VALIDATED / INFERRED / UNKNOWN.

Nó không được biến kế hoạch thành kết quả, mock thành implementation, hoặc screenshot thành bằng chứng mạnh hơn test/log/measurement.

## Công cụ đi kèm

- inventory project;
- validate requirement traceability;
- validate research pack;
- LaTeX audit;
- PDF audit;
- visual manifest validator.

Các script mặc định không được tự sửa source dự án trừ khi người dùng yêu cầu.
