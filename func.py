"""Các hàm tiện ích cho ví dụ số học cơ bản."""


def add(a, b):
    """Cộng hai giá trị bằng toán tử cộng của Python.

    Hàm này trả về kết quả của biểu thức ``a + b``. Hàm hỗ trợ mọi cặp
    giá trị mà Python có thể cộng được, chẳng hạn số, chuỗi, danh sách,
    hoặc tuple tương thích.

    Args:
        a (object): Giá trị thứ nhất cần cộng.
        b (object): Giá trị thứ hai cần cộng.

    Returns:
        object: Kết quả của phép cộng ``a`` và ``b``.

    Raises:
        TypeError: Nếu ``a`` và ``b`` không tương thích với toán tử ``+``.

    Example:
        >>> add(10, 20)
        30
        >>> add("AI", " Course")
        'AI Course'
    """
    return a + b

print(add(10, 20))
