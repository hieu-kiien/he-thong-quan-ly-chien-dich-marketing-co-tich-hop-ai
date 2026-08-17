# PROMPT: Tạo bộ Prompt thực hành cho Chương 3 – Ứng dụng AI

## 1. Nguồn dữ liệu

Hãy đọc và phân tích **toàn bộ nội dung Chương 3** tại thư mục:

thư mục/tài liệu Chương 3 được cung cấp trong workspace. Nếu không có nguồn,
phải báo thiếu thay vì dùng một đường dẫn máy cá nhân.

Đồng thời đọc file mô tả bài toán **Quản lý bán hàng** tại:

`project.md` trong cùng thư mục với prompt này.

File `project.md` là ngữ cảnh dự án xuyên suốt để xây dựng các prompt ví dụ.

---

## 2. Xác định các kỹ thuật Prompt Engineering

Từ nội dung Chương 3:

* Xác định đầy đủ các **kỹ thuật Prompt Engineering** được trình bày.
* Giữ nguyên logic phân nhóm và thứ tự xuất hiện trong Chương 3.
* Không tự ý bổ sung kỹ thuật không có trong nội dung chương.
* Với mỗi kỹ thuật, xác định các nội dung, trường hợp sử dụng và ví dụ cần được minh họa bằng prompt thực hành.

---

## 3. Tạo thư mục theo từng kỹ thuật

Mỗi **nhóm kỹ thuật Prompt Engineering** tạo thành một thư mục riêng.

Tên thư mục theo định dạng:

```text
XX-Ten-ky-thuat
```

Trong đó:

* `XX`: số thứ tự `01, 02, 03, ...`
* `Ten-ky-thuat`: tên kỹ thuật.
* Tên thư mục viết không dấu.
* Sử dụng dấu `-` để phân cách các từ.

Ví dụ:

```text
01-Zero-Shot-Prompting/
02-Few-Shot-Prompting/
03-Role-Prompting/
04-Chain-of-Thought/
```

Tên và số lượng thư mục thực tế phải được xác định từ nội dung Chương 3.

---

## 4. Tạo các prompt cho từng kỹ thuật

Trong mỗi thư mục, hãy tạo **nhiều file prompt tùy theo nội dung của kỹ thuật được trình bày trong Chương 3**.

**Không cố định số lượng prompt cho mỗi kỹ thuật.**

Một kỹ thuật đơn giản có thể chỉ cần một vài prompt, trong khi kỹ thuật có nhiều nội dung, biến thể hoặc trường hợp sử dụng có thể cần nhiều prompt hơn.

Mục tiêu là các prompt phải **bao phủ đầy đủ nội dung thực hành của kỹ thuật đó trong Chương 3**, nhưng tránh tạo các prompt dư thừa hoặc lặp lại.

---

## 5. Quy tắc đặt tên file

Các file prompt trong từng thư mục được đánh số liên tục:

```text
01-Ten-ky-thuat-Ten-bai-toan.md
02-Ten-ky-thuat-Ten-bai-toan.md
03-Ten-ky-thuat-Ten-bai-toan.md
...
```

Tên file cần thể hiện được:

**Số thứ tự + Tên kỹ thuật + Nội dung/tác vụ của prompt**

Ví dụ:

```text
01-Zero-Shot-Prompting/
├── 01-Zero-Shot-Phan-tich-yeu-cau.md
├── 02-Zero-Shot-Sinh-User-Story.md
├── 03-Zero-Shot-Sinh-SQL.md
└── 04-Zero-Shot-Kiem-thu-chuc-nang.md
```

Số lượng file tùy theo số lượng kỹ thuật 

---

## 6. Bài toán xuyên suốt: Quản lý bán hàng

Tất cả các prompt ví dụ phải gắn với **bài toán Quản lý bán hàng** được mô tả trong:

`project.md` trong cùng thư mục với prompt này.

Trước khi tạo prompt:

1. Đọc toàn bộ `project.md`.
2. Xác định các chức năng, đối tượng, nghiệp vụ, dữ liệu và yêu cầu của hệ thống Quản lý bán hàng.
3. Sử dụng chính các thông tin này làm ngữ cảnh cho các prompt.
4. Không tự ý đưa vào các yêu cầu nghiệp vụ mâu thuẫn với `project.md`.

Các prompt nên khai thác đa dạng các công việc trong quá trình phát triển hệ thống, chẳng hạn:

* Phân tích yêu cầu.
* Xác định actor và chức năng.
* Viết User Story.
* Xây dựng Use Case.
* Thiết kế cơ sở dữ liệu.
* Xác định entity.
* Sinh SQL.
* Thiết kế class.
* Viết mã nguồn.
* Giải thích mã nguồn.
* Refactoring.
* Debugging.
* Sinh dữ liệu kiểm thử.
* Sinh test case.
* Viết tài liệu.
* Đánh giá hoặc cải tiến giải pháp.

Chỉ lựa chọn các bài toán phù hợp để **thể hiện rõ kỹ thuật Prompt Engineering tương ứng**.

---

## 7. Yêu cầu đối với mỗi prompt

Mỗi file `.md` phải chứa một **prompt hoàn chỉnh có thể sao chép và sử dụng trực tiếp với ChatGPT hoặc LLM tương tự**.

Prompt cần:

* Thể hiện rõ kỹ thuật Prompt Engineering đang được minh họa.
* Có mục tiêu cụ thể.
* Có ngữ cảnh cần thiết.
* Có yêu cầu đầu vào rõ ràng khi cần.
* Mô tả nhiệm vụ cụ thể.
* Quy định đầu ra rõ ràng.
* Gắn với bài toán Quản lý bán hàng trong `project.md`.
* Phù hợp với nội dung lý thuyết tương ứng trong Chương 3.
* Có giá trị thực hành đối với sinh viên học môn Ứng dụng AI.

Không tạo nhiều prompt chỉ bằng cách thay đổi vài từ hoặc thay đổi chủ đề. Mỗi prompt phải minh họa một **cách sử dụng, biến thể hoặc tình huống thực hành có ý nghĩa** của kỹ thuật.

---

## 8. Mối quan hệ giữa các prompt

Khi phù hợp, hãy thiết kế các prompt theo hướng **liên kết thành chuỗi công việc phát triển phần mềm**.

Ví dụ:

```text
Phân tích yêu cầu
        ↓
Xác định chức năng
        ↓
Sinh User Story
        ↓
Thiết kế CSDL
        ↓
Sinh mã nguồn
        ↓
Kiểm thử
        ↓
Debug
        ↓
Refactoring
        ↓
Viết tài liệu
```

Tuy nhiên, mục tiêu chính vẫn là minh họa **kỹ thuật Prompt Engineering của từng phần trong Chương 3**, không phải cố gắng bao phủ toàn bộ quy trình phát triển phần mềm trong mỗi kỹ thuật.

---

## 9. Kiểm tra tính nhất quán

Sau khi tạo xong, hãy kiểm tra:

* Tất cả kỹ thuật Prompt Engineering trong Chương 3 đã được xử lý.
* Mỗi kỹ thuật có thư mục tương ứng.
* Số lượng prompt của từng kỹ thuật phù hợp với lượng nội dung được trình bày trong Chương 3.
* Không áp đặt số lượng prompt giống nhau cho tất cả kỹ thuật.
* Các prompt không bị trùng lặp về mục tiêu.
* Tất cả ví dụ đều gắn với bài toán Quản lý bán hàng.
* Nội dung nghiệp vụ thống nhất với `project.md`.
* Prompt thể hiện đúng kỹ thuật mà nó được dùng để minh họa.
* Tên file phản ánh đúng nội dung prompt.
* Thứ tự file trong mỗi thư mục liên tục từ `01` trở đi.

---

## 10. Kết quả đầu ra

Tạo các thư mục và file trực tiếp trên hệ thống file.

Sau khi hoàn thành, hiển thị cây thư mục, ví dụ:

```text
Bai 03/
├── project.md
└── prompts/
    ├── 01-Zero-Shot-Prompting/
    │   ├── 01-Zero-Shot-Phan-tich-yeu-cau.txt
    │   ├── 02-Zero-Shot-Sinh-User-Story.txt
    │   ├── 03-Zero-Shot-Sinh-SQL.txt
    │   └── ...
    │
    ├── 02-Few-Shot-Prompting/
    │   ├── 01-Few-Shot-Phan-loai-yeu-cau.txt
    │   ├── 02-Few-Shot-Sinh-User-Story.txt
    │   └── ...
    │
    └── ...
```

Cuối cùng, tạo báo cáo tóm tắt gồm:

* Tổng số kỹ thuật Prompt Engineering tìm thấy trong Chương 3.
* Danh sách các kỹ thuật.
* Số prompt được tạo cho từng kỹ thuật.
* Tổng số file prompt đã tạo.
* Mỗi prompt tương ứng với nội dung/mục nào trong Chương 3.
* Xác nhận tất cả prompt ví dụ đều dựa trên bài toán Quản lý bán hàng trong `project.md`.
