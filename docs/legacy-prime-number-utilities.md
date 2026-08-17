---
document_id: BAI03-LEGACY-PRIME-README
document_type: unrelated-utility-readme
project_id: UNRELATED-PRIME-UTILITY
status: LEGACY
source: ../README.md (nội dung README cũ)
---

# Prime Number Utilities

Module này cung cấp các hàm tiện ích để kiểm tra số nguyên tố và tính tổng các
số nguyên tố trong một danh sách số nguyên. Nội dung này không thuộc dự án
`BAI03-SALES-AI`, nhưng được giữ lại để không làm mất tài liệu của các file
`func*.py` và `test_func*.py`.

## `is_prime(n: int) -> bool`

Kiểm tra một số nguyên có phải là số nguyên tố hay không. `n` phải là số nguyên;
giá trị trả về là `True` nếu `n` là số nguyên tố, ngược lại là `False`.

## `sum_of_primes(numbers: list[int]) -> int`

Tính tổng các số nguyên tố trong danh sách. Đầu vào phải là một danh sách số
nguyên; dữ liệu không hợp lệ làm phát sinh lỗi kiểu hoặc giá trị tương ứng.

```python
sum_of_primes([1, 2, 3, 4, 5, 10])  # 10
sum_of_primes([4, 6, 8])             # 0
```
