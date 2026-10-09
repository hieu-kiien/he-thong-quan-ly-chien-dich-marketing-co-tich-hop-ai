"""Kiểm thử việc xác định IP client sau Cloudflare Tunnel.

Đây là hồi quy cho một sự cố thật. Khi hệ thống chạy sau cloudflared + nginx,
header CF-Connecting-IP KHÔNG được nginx chuyển tiếp, còn X-Forwarded-For lại chứa
IP điểm vào dùng chung của Cloudflare. Nếu đọc sai header, mọi người dùng bị gộp
vào một bucket rate limit và một người gõ sai mật khẩu sẽ khoá luôn cả hệ thống.
"""

from starlette.requests import Request

from app.api.v1.auth import _resolve_client_ip


def _request(headers=None, peer="127.0.0.1"):
    """Dựng Request tối giản giống hệ thống thật sau proxy."""
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/auth/login",
        "headers": raw,
        "client": (peer, 12345),
        "scheme": "https",
        "server": ("127.0.0.1", 8080),
        "query_string": b"",
    }
    return Request(scope)


def test_cf_connecting_ip_wins_over_xff():
    """CF-Connecting-IP là IP thật của client, phải thắng X-Forwarded-For."""
    req = _request({
        "cf-connecting-ip": "203.0.113.9",
        "x-forwarded-for": "198.51.100.7, 10.0.0.1",
    })
    assert _resolve_client_ip(req) == "203.0.113.9"


def test_cf_connecting_ip_alone():
    req = _request({"cf-connecting-ip": "203.0.113.9"})
    assert _resolve_client_ip(req) == "203.0.113.9"


def test_distinct_clients_get_distinct_keys():
    """Hai người dùng khác IP phải ra hai khoá khác nhau — điểm mấu chốt."""
    a = _request({"cf-connecting-ip": "203.0.113.1"})
    b = _request({"cf-connecting-ip": "203.0.113.2"})
    assert _resolve_client_ip(a) != _resolve_client_ip(b)


def test_falls_back_to_xff_without_cloudflare():
    """Không có Cloudflare thì vẫn phải lấy được client thật từ XFF."""
    req = _request({"x-forwarded-for": "203.0.113.5, 10.0.0.1"})
    assert _resolve_client_ip(req) == "203.0.113.5"


def test_falls_back_to_x_real_ip():
    req = _request({"x-real-ip": "203.0.113.6"})
    assert _resolve_client_ip(req) == "203.0.113.6"


def test_untrusted_peer_ignores_forwarded_headers():
    """Nếu peer không phải proxy tin cậy thì bỏ qua header, chống giả mạo.

    Không có bước này, kẻ tấn công tự đặt CF-Connecting-IP để né rate limit.
    """
    req = _request(
        {"cf-connecting-ip": "203.0.113.9", "x-forwarded-for": "1.2.3.4"},
        peer="8.8.8.8",
    )
    assert _resolve_client_ip(req) == "8.8.8.8"


def test_no_headers_falls_back_to_peer():
    req = _request({})
    assert _resolve_client_ip(req) == "127.0.0.1"


def test_blank_cf_ip_falls_through_to_xff():
    """CF-Connecting-IP rỗng không được che mất XFF hợp lệ."""
    req = _request({"cf-connecting-ip": "   ", "x-forwarded-for": "203.0.113.8"})
    assert _resolve_client_ip(req) == "203.0.113.8"