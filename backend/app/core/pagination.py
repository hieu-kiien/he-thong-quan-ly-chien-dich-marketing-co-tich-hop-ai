"""Hợp đồng phân trang DUY NHẤT cho toàn bộ endpoint trả về danh sách.

VÌ SAO CẦN MỘT MÔDUN RIÊNG
-------------------------
Trước đây mỗi endpoint tự chế ra cách phân trang riêng (hoặc không phân trang):
`GET /ai/jobs` dùng `page`/`page_size`/`has_next`, `GET /notifications` dùng
`limit`, còn `GET /campaigns`, `/contents`, `/schedules`, `/tasks/*` trả về
mảng không giới hạn. Frontend vì thế không có cách nào để biết còn bao nhiêu
bản ghi để dựng nút phân trang, và mỗi endpoint lại phải tự chịu trách nhiệm
đặt trần cho tham số — quên một chỗ là một vector làm cạn bộ nhớ trên Render
free (512 MB).

Module này gom phần đó lại một chỗ: một `PageParams` dependency để đọc và chặn
trần tham số, một model `Page[T]` để trả về, và một hàm `paginate_query()` để
áp `filter -> order -> count -> offset/limit` đúng thứ tự.

HỢP ĐỒNG
--------
Query:  `page` (mặc định 1, >= 1), `page_size` (mặc định 20, 1..100)
Response: { items, total, page, page_size, total_pages, has_next, has_prev }

`items` luôn là danh sách (kể cả rỗng), `total` là TỔNG SỐ bản ghi sau khi lọc —
không phải số bản ghi của trang hiện tại. Frontend dùng `total_pages` để dựng
nút trang mà không phải tự chia.

THỨ TỰ ÁP DỤNG (chỗ dễ sai nhất)
----------------------------------
`paginate_query()` BẮT BUỘC lọc + sắp xếp TRƯỚC rồi mới offset/limit. Lọc sau
khi đã cắt trang là "phân trang rồi lọc": `total` sai, trang cuối rỗng bất thường,
và quan trọng nhất là `offset` được tính trên tập chưa lọc nên người dùng có thể
đọc lọt dòng của tenant khác nếu bộ lọc tenant vốn nằm sai chỗ. Hàm này đặt
`count()` TRƯỚC `offset`/`limit` và sau tất cả filter để điều đó không thể xảy ra
do sơ suất.

VỀ `page_size` TỐI ĐA
---------------------
Trần `PAGE_SIZE_MAX = 100` là bắt buộc, không phải tuỳ chọn: một tham số `limit`
không trần là đường DoS, và instance thật chạy trên Render free chỉ có 512 MB RAM
với 0.1 CPU — trả về vài chục nghìn dòng JSON sẽ bóp chết mọi route khác. Client
cũ gọi không có tham số vẫn nhận trang mặc định 20 dòng, tức không hỏng gì.
"""

from typing import Generic, List, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query as SQLAlchemyQuery

# Trần cứng cho tham số `page_size`. Xem module docstring.
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100

T = TypeVar("T")


class PageParams(BaseModel):
    """Tham số phân trang đã được kiểm tra trần.

    Dùng như dependency của FastAPI:

        params: PageParams = Depends(page_params)

    `page_size` vượt trần bị FastAPI trả 422 (do `Query(le=...)`) — client nhận
    thông báo rõ ràng thay vì âm thầm bị cắt, tránh hiệu ứng "tôi yêu cầu 500 mà
    chỉ nhận 100" rất khó chẩn đoán.
    """

    page: int = Field(1, ge=1, description="Số trang, bắt đầu từ 1")
    page_size: int = Field(
        PAGE_SIZE_DEFAULT,
        ge=1,
        le=PAGE_SIZE_MAX,
        description=f"Số bản ghi mỗi trang (1..{PAGE_SIZE_MAX})",
    )

    @property
    def offset(self) -> int:
        """Số bản ghi cần bỏ qua. Trang ngoài tổng số bản ghi cho offset lớn hơn
        tổng — SQL vẫn trả về danh sách rỗng chứ không lỗi, đó là hành vi đúng."""
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, description="Số trang, bắt đầu từ 1"),
    page_size: int = Query(
        PAGE_SIZE_DEFAULT,
        ge=1,
        le=PAGE_SIZE_MAX,
        description=f"Số bản ghi mỗi trang (1..{PAGE_SIZE_MAX})",
    ),
) -> PageParams:
    """Dependency FastAPI đọc `page`/`page_size` từ query string."""
    return PageParams(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    """Envelope phân trang. Đây là hợp đồng DUY NHẤT của API cho danh sách."""

    items: List[T] = Field(default_factory=list, description="Bản ghi của trang hiện tại")
    total: int = Field(0, ge=0, description="TỔNG số bản ghi sau khi lọc, không phải số bản ghi của trang này")
    page: int = Field(1, ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(
        0, ge=0, description="Số trang = ceil(total / page_size). Bằng 0 khi không có bản ghi nào."
    )
    has_next: bool = Field(False, description="Còn trang sau không")
    has_prev: bool = Field(False, description="Còn trang trước không")

    @classmethod
    def build(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "Page[T]":
        """Dựng envelope từ kết quả đã cắt trang + tổng đã đếm.

        `total_pages = ceil(total / page_size)` và bằng 0 khi `total == 0`, để
        frontend có thể hiện "0 kết quả" thay vì "trang 1/0".
        """
        total = max(int(total), 0)
        page_size = max(int(page_size), 1)
        total_pages = -(-total // page_size)  # chia lên tròn, tránh float
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page * page_size < total,
            has_prev=page > 1,
        )


def paginate_query(
    query: SQLAlchemyQuery,
    params: PageParams,
    *,
    serializer=None,
) -> Page:
    """Cắt trang một query đã LỌC và ĐÃ SẮP XẾP, rồi bọc kết quả thành `Page`.

    `query` phải là query đã áp đủ tenant scope + filter + order_by. Hàm chỉ
    thêm `count()` và `offset/limit` — không tự thêm bộ lọc nào, để không bao giờ
    có một đường lọc tenant nào đi qua `paginate_query` mà không có ý đồ.

    `serializer` biến đổi từng dòng ORM thành Pydantic model; mặc định giữ nguyên
    đối tượng (FastAPI tự validate theo `response_model`).
    """
    # `count()` đặt TRƯỚC offset/limit để `total` là tổng sau lọc, không phải
    # số dòng của trang. Với query có `distinct()` SQLAlchemy bọc trong subquery
    # nên vẫn đếm đúng số chiến dịch/khoá duy nhất.
    total = query.count()
    rows = query.offset(params.offset).limit(params.page_size).all()
    items = [serializer(row) for row in rows] if serializer is not None else list(rows)
    return Page.build(items=items, total=total, page=params.page, page_size=params.page_size)