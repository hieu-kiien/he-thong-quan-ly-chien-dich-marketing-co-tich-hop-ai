"""Lỗi nghiệp vụ có kiểu và exception handler theo định dạng CONTRACT §4.

Body lỗi: {"detail": {"code": "SNAKE_UPPER", "message": "...", "fields": {...}?}}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DomainError(Exception):
    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "Yêu cầu không hợp lệ"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        if code:
            self.code = code
        self.fields = fields
        self.headers = headers
        super().__init__(self.message)

    def to_detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.fields:
            detail["fields"] = self.fields
        return detail


class BadRequest(DomainError):
    status_code = 400


class Unauthorized(DomainError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Bạn cần đăng nhập để tiếp tục"


class PermissionDenied(DomainError):
    status_code = 403
    code = "FORBIDDEN"
    message = "Bạn không có quyền thực hiện thao tác này"


class NotFound(DomainError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Không tìm thấy dữ liệu"


class Conflict(DomainError):
    status_code = 409
    code = "CONFLICT"
    message = "Dữ liệu xung đột"


class InvalidTransition(Conflict):
    code = "INVALID_TRANSITION"
    message = "Không thể chuyển trạng thái này"


class PayloadTooLarge(DomainError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    message = "Dữ liệu gửi lên quá lớn"


class ValidationFailed(DomainError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "Dữ liệu không hợp lệ"

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        fields = kwargs.get("fields")
        if message is None and fields:
            message = "; ".join(list(dict.fromkeys(fields.values()))[:3])
        super().__init__(message, **kwargs)


class RateLimited(DomainError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Bạn thao tác quá nhanh, vui lòng thử lại sau"


def error_body(code: str, message: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if fields:
        detail["fields"] = fields
    return {"detail": detail}


_HTTP_CODES = {
    400: ("BAD_REQUEST", "Yêu cầu không hợp lệ"),
    401: ("UNAUTHORIZED", "Bạn cần đăng nhập để tiếp tục"),
    403: ("FORBIDDEN", "Bạn không có quyền thực hiện thao tác này"),
    404: ("NOT_FOUND", "Không tìm thấy đường dẫn"),
    405: ("METHOD_NOT_ALLOWED", "Phương thức không được hỗ trợ"),
    413: ("PAYLOAD_TOO_LARGE", "Dữ liệu gửi lên quá lớn"),
    429: ("RATE_LIMITED", "Bạn thao tác quá nhanh, vui lòng thử lại sau"),
}


def _translate_validation_error(err: dict[str, Any]) -> str:
    etype = err.get("type", "")
    ctx = err.get("ctx") or {}
    if etype == "missing":
        return "Trường này là bắt buộc"
    if etype == "string_too_short":
        if ctx.get("min_length", 1) <= 1:
            return "Không được để trống"
        return f"Tối thiểu {ctx.get('min_length')} ký tự"
    if etype == "string_too_long":
        return f"Tối đa {ctx.get('max_length')} ký tự"
    if etype in ("greater_than_equal",):
        return f"Phải lớn hơn hoặc bằng {ctx.get('ge')}"
    if etype in ("greater_than",):
        return f"Phải lớn hơn {ctx.get('gt')}"
    if etype in ("less_than_equal",):
        return f"Phải nhỏ hơn hoặc bằng {ctx.get('le')}"
    if etype in ("less_than",):
        return f"Phải nhỏ hơn {ctx.get('lt')}"
    if etype in ("int_parsing", "int_type", "int_from_float"):
        return "Phải là số nguyên"
    if etype in ("decimal_parsing", "float_parsing", "decimal_type", "float_type"):
        return "Phải là số"
    if etype.startswith("date") and "datetime" not in etype:
        return "Ngày không hợp lệ (định dạng YYYY-MM-DD)"
    if etype.startswith(("datetime", "timezone")) :
        return "Thời điểm không hợp lệ (định dạng ISO-8601 có múi giờ)"
    if etype in ("enum", "literal_error"):
        expected = ctx.get("expected")
        return f"Giá trị không hợp lệ (chấp nhận: {expected})" if expected else "Giá trị không hợp lệ"
    if etype in ("bool_parsing", "bool_type"):
        return "Phải là true/false"
    if etype == "value_error":
        msg = str(err.get("msg", ""))
        if "email" in msg.lower():
            return "Email không hợp lệ"
        return msg.removeprefix("Value error, ")
    if etype in ("json_invalid",):
        return "JSON không hợp lệ"
    if etype in ("list_type",):
        return "Phải là danh sách"
    if etype in ("too_long",):
        return f"Tối đa {ctx.get('max_length')} phần tử"
    if etype in ("too_short",):
        return f"Tối thiểu {ctx.get('min_length')} phần tử"
    if etype in ("model_attributes_type", "dict_type", "model_type"):
        return "Phải là object JSON"
    if etype in ("string_type",):
        return "Phải là chuỗi"
    if etype in ("url_parsing", "url_scheme", "url_type"):
        return "URL không hợp lệ"
    return str(err.get("msg", "Giá trị không hợp lệ"))


def validation_fields(errors: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for err in errors:
        loc = [str(p) for p in err.get("loc", ())]
        if loc and loc[0] in ("body", "query", "path", "header", "cookie", "form"):
            loc = loc[1:]
        key = ".".join(loc) or "_"
        fields.setdefault(key, _translate_validation_error(err))
    return fields


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.to_detail()}, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_ERROR", "Dữ liệu không hợp lệ", validation_fields(list(exc.errors()))
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            content = {"detail": exc.detail}
        else:
            code, default_msg = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", "Lỗi yêu cầu"))
            content = error_body(code, default_msg)
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception):  # pragma: no cover - safety net
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500, content=error_body("INTERNAL_ERROR", "Lỗi hệ thống, vui lòng thử lại sau")
        )
