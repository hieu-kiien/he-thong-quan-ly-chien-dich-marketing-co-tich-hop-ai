> **Metadata:** `document_id=BAI03-LEGACY-PRIME-PROMPT`; `project_id=UNRELATED-PRIME-UTILITY`; `status=LEGACY`. Dùng thư mục hiện tại, không dùng đường dẫn máy cá nhân.

Làm việc với thư mục hiện tại của bộ tiện ích số nguyên tố.

tạo file python có nội dung sau
## 1. Ngữ cảnh (Context)

Bạn là một **lập trình viên Python có kinh nghiệm**, am hiểu về thuật toán, cấu trúc dữ liệu và các nguyên tắc viết mã nguồn rõ ràng, dễ bảo trì.

## 2. Bối cảnh (Background)

Tôi đang học cách xây dựng các hàm xử lý một dãy số nguyên bằng Python. Tôi cần giải quyết bài toán xác định các **số nguyên tố** xuất hiện trong một danh sách và tính tổng của chúng.

Một số nguyên tố là số nguyên lớn hơn 1 và chỉ có đúng hai ước dương là 1 và chính nó.

## 3. Nhiệm vụ (Task)

Hãy viết một hàm Python có tên:

`sum_of_primes(numbers)`

Hàm nhận vào một danh sách các số nguyên, xác định những phần tử là số nguyên tố và trả về **tổng của tất cả các số nguyên tố trong danh sách**.

Cần xây dựng thêm hàm phụ:

`is_prime(n)`

để kiểm tra một số nguyên có phải là số nguyên tố hay không.

kết quả ghi ra file có tên là func1.py cùng thư mục chứa prompts

## 4. Ràng buộc (Constraints)

* Sử dụng Python 3.
* Sử dụng type hints.
* Tuân thủ chuẩn PEP 8.
* Không sử dụng thư viện bên ngoài.
* Số nhỏ hơn hoặc bằng 1 không được coi là số nguyên tố.
* Thuật toán kiểm tra số nguyên tố nên tối ưu bằng cách chỉ kiểm tra các ước đến `√n`.
* Nếu `numbers` không phải là `list`, hãy phát sinh `TypeError`.
* Nếu một phần tử trong danh sách không phải số nguyên, hãy phát sinh `ValueError`.
* Nếu danh sách rỗng hoặc không chứa số nguyên tố, trả về `0`.

## 5. Định dạng đầu ra (Output Format)

Trả lời bằng mã nguồn Python hoàn chỉnh.

Mỗi hàm cần có **docstring theo chuẩn Google**, bao gồm:

* Mô tả chức năng.
* `Args`: mô tả tham số.
* `Returns`: mô tả giá trị trả về.
* `Raises`: các ngoại lệ có thể phát sinh.
* `Examples`: ví dụ sử dụng.

Sau phần code, giải thích ngắn gọn **thuật toán** và **độ phức tạp thời gian**.

## 6. Ví dụ (Examples)

**Ví dụ 1:**

Input:

`[1, 2, 3, 4, 5, 6, 7]`

Các số nguyên tố:

`2, 3, 5, 7`

Output:

`17`

**Ví dụ 2:**

Input:

`[4, 6, 8, 10]`

Output:

`0`

**Ví dụ 3:**

Input:

`[-5, 0, 1, 2, 11, 15]`

Các số nguyên tố:

`2, 11`

Output:

`13`

## 7. Giọng điệu (Tone)

Trình bày theo phong cách **kỹ thuật, logic, khoa học và dễ hiểu**. Code cần rõ ràng, có cấu trúc tốt, phù hợp để sử dụng làm ví dụ giảng dạy cho sinh viên học lập trình Python.
