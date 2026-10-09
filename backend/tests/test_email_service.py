"""Kiểm thử lớp gửi email.

Điểm cần bảo vệ không phải "gửi đúng định dạng" mà là: **email lỗi không được
kéo theo sập luồng nghiệp vụ**. Nếu không, một lần SMTP chết cũng làm hỏng việc
tạo nội dung hoặc tạo workspace — thứ vốn không liên quan gì tới email.
"""

import pytest

from app.services import email_service as es_module
from app.services.email_service import EmailSendError, EmailService


@pytest.fixture()
def svc(monkeypatch):
    """EmailService với provider rỗng; các test tự bật biến cần thiết."""
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "none", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "", raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_HOST", "", raising=False)
    return EmailService()


# --- Chưa cấu hình: im lặng và an toàn, không sập ---


def test_disabled_by_default(svc):
    assert svc.is_enabled is False
    r = svc.send(["a@b.c"], "S", "body")
    assert r["sent"] is False
    assert "EMAIL_PROVIDER" in r["reason"]


def test_no_recipients_is_not_an_error(svc):
    r = svc.send([], "S", "body")
    assert r["sent"] is False
    assert "người nhận" in r["reason"]


def test_blank_address_is_ignored(svc):
    r = svc.send(["", "   "], "S", "body")
    assert r["sent"] is False


# --- Resend: gửi được, và lỗi trả về trong kết quả ---


def test_resend_success(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_test_123", raising=False)

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "email_123"}

    captured = {}

    def fake_post(url, **kw):
        captured["url"] = url
        captured["kw"] = kw
        return FakeResp()

    monkeypatch.setattr(es_module.httpx, "post", fake_post)
    r = svc.send(["a@b.c"], "Tiêu đề", "Nội dung")
    assert r["sent"] is True
    assert r["id"] == "email_123"
    assert r["provider"] == "resend"
    assert captured["url"] == "https://api.resend.com/emails"
    # Resend chạy sau Cloudflare; UA mặc định của httpx bị chặn với 403/1010.
    assert "User-Agent" in captured["kw"]["headers"]
    assert captured["kw"]["headers"]["Authorization"] == "Bearer re_test_123"


def test_resend_sends_html_when_provided(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_test_123", raising=False)
    captured = {}

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "x"}

    monkeypatch.setattr(
        es_module.httpx, "post",
        lambda url, **kw: (captured.update(payload=kw["json"]), FakeResp())[1],
    )
    svc.send(["a@b.c"], "S", "text", body_html="<p>html</p>")
    assert captured["payload"]["html"] == "<p>html</p>"
    assert captured["payload"]["text"] == "text"


def test_resend_http_error_is_returned_not_raised(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_test_123", raising=False)

    class FakeResp:
        status_code = 422

        @staticmethod
        def json():
            return {"message": "Invalid `to` field"}

    monkeypatch.setattr(es_module.httpx, "post", lambda url, **kw: FakeResp())
    r = svc.send(["khong-phai-email"], "S", "body")
    assert r["sent"] is False
    assert "422" in r["reason"]


def test_resend_timeout_is_returned_not_raised(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_test_123", raising=False)

    def boom(url, **kw):
        raise es_module.httpx.TimeoutException("timeout")

    monkeypatch.setattr(es_module.httpx, "post", boom)
    r = svc.send(["a@b.c"], "S", "body")
    assert r["sent"] is False
    assert "không phản hồi" in r["reason"]


def test_resend_key_is_not_leaked_in_error(svc, monkeypatch):
    """Nội dung lỗi trả về không được chứa API key."""
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_SECRET_KEY_VALUE", raising=False)

    class FakeResp:
        status_code = 401
        text = "unauthorized for key=re_SECRET_KEY_VALUE"

        @staticmethod
        def json():
            raise ValueError()

    monkeypatch.setattr(es_module.httpx, "post", lambda url, **kw: FakeResp())
    r = svc.send(["a@b.c"], "S", "body")
    assert r["sent"] is False
    assert "re_SECRET_KEY_VALUE" not in r["reason"]


# --- SMTP ---


def test_smtp_success(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "smtp", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_HOST", "smtp.example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_USER", "", raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_PASSWORD", "", raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_USE_TLS", True, raising=False)

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, u, p):
            sent["login"] = (u, p)

        def sendmail(self, f, t, body):
            sent["mail"] = (f, t, len(body))

    monkeypatch.setattr(es_module.smtplib, "SMTP", FakeSMTP)
    r = svc.send(["a@b.c"], "S", "body", body_html="<p>x</p>")
    assert r["sent"] is True
    assert sent["tls"] is True
    assert sent["host"] == ("smtp.example.com", 587)
    assert sent["mail"][0] == "no-reply@example.com"


def test_smtp_error_is_returned_not_raised(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "smtp", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "SMTP_HOST", "smtp.example.com", raising=False)

    class FakeSMTP:
        def __init__(self, *a, **kw):
            raise es_module.smtplib.SMTPException("kết nối bị từ chối")

    monkeypatch.setattr(es_module.smtplib, "SMTP", FakeSMTP)
    r = svc.send(["a@b.c"], "S", "body")
    assert r["sent"] is False
    assert "SMTP" in r["reason"]


# --- Mẫu email nghiệp vụ ---


def test_review_template_contains_facts(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_x", raising=False)
    seen = {}

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "y"}

    monkeypatch.setattr(es_module.httpx, "post", lambda url, **kw: (seen.update(kw["json"]), FakeResp())[1])

    r = svc.send_content_for_review("boss@x.com", "Bài đăng 1", "Chiến dịch Hè", "Minh")
    assert r["sent"] is True
    assert "Bài đăng 1" in seen["subject"]
    assert "Chiến dịch Hè" in seen["text"]
    assert "Minh" in seen["text"]


def test_send_email_safely_never_raises(svc, monkeypatch):
    """Lớp bọc an toàn: kể cả khi EmailService lỗi nội bộ cũng không ném ra."""
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "resend", raising=False)
    monkeypatch.setattr(es_module.settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com", raising=False)
    monkeypatch.setattr(es_module.settings, "RESEND_API_KEY", "re_x", raising=False)

    def boom(url, **kw):
        raise MemoryError  # BaseException con, không phải Exception

    monkeypatch.setattr(es_module.httpx, "post", boom)
    r = es_module.send_email_safely(["a@b.c"], "S", "body")
    assert r["sent"] is False


def test_unknown_provider_reports_problem(svc, monkeypatch):
    monkeypatch.setattr(es_module.settings, "EMAIL_PROVIDER", "sendgrid", raising=False)
    r = svc.send(["a@b.c"], "S", "body")
    assert r["sent"] is False
    assert "không được hỗ trợ" in r["reason"]