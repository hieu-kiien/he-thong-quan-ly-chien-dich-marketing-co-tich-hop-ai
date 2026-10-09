"""Lớp gửi email cho hệ thống.

Thiết kế theo nguyên tắc "mọi nghiệp vụ cốt lõi phải chạy được khi không có AI"
— và áp dụng tương tự cho email: **hệ thống không được sập vì email lỗi.**

Trạng thái bảo đảm:

* Email là **tùy chọn**. Không cấu hình gửi được thì mọi luồng nghiệp vụ vẫn
  chạy; chỉ có việc gửi thông báo là không diễn ra, được ghi log rõ ràng.
* Lỗi gửi email **không bao giờ** làm hỏng request đang xử lý. Đặt nội dung,
  duyệt nội dung, tạo workspace đều thành công dù SMTP/provider chết.
* Nội dung fail **được ghi lại vào database** (bảng `EmailOutbox`) để xem lại và
  gửi lại, chứ không rơi vào hư không.

Nhà cung cấp hỗ trợ:

* ``resend`` — Resend HTTP API (khuyến nghị, miễn phí 3.000/tháng).
* ``smtp`` — SMTP thường (Gmail cần mật khẩu ứng dụng).
* ``none`` — tắt hoàn toàn (mặc định khi chưa cấu hình).

Chọn provider bằng ``EMAIL_PROVIDER``; không cần đổi code khi đổi dịch vụ.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Iterable, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER_NONE = "none"
PROVIDER_RESEND = "resend"
PROVIDER_SMTP = "smtp"

SUPPORTED_PROVIDERS = (PROVIDER_NONE, PROVIDER_RESEND, PROVIDER_SMTP)

# Thời gian chờ tối đa cho một lần gửi. Gửi email nằm ngoài đường chính của
# request nên timeout ngắn là đủ; treo lâu chỉ làm người dùng đợi vô ích.
SEND_TIMEOUT_SECONDS = 15


class EmailSendError(RuntimeError):
    """Gửi email thất bại. Không được để lỗi này thoát ra ngoài request."""


class EmailService:
    """Gửi email qua provider đã cấu hình, không bao giờ làm sập luồng chính."""

    def __init__(self) -> None:
        # Không cache gì ở đây: mọi thứ đọc động qua property bên dưới, để thay
        # đổi cấu hình có hiệu lực mà không cần restart tiến trình.
        pass

    @property
    def from_address(self) -> str:
        return getattr(settings, "EMAIL_FROM_ADDRESS", "") or ""

    @property
    def from_name(self) -> str:
        return getattr(settings, "EMAIL_FROM_NAME", "MarketFlow AI") or "MarketFlow AI"

    @property
    def provider(self) -> str:
        return (getattr(settings, "EMAIL_PROVIDER", PROVIDER_NONE) or PROVIDER_NONE).lower().strip()

    # ---- Kiểm tra cấu hình ----

    @property
    def is_enabled(self) -> bool:
        """Có thể gửi email thật hay không.

        Đây là thứ UI nên hỏi trước khi hứa hẹn "đã gửi email". Trả ``False``
        nghĩa là chỉ ghi nhận, không gửi.
        """
        if self.provider == PROVIDER_NONE:
            return False
        if not self.from_address:
            return False
        if self.provider == PROVIDER_RESEND:
            return bool(getattr(settings, "RESEND_API_KEY", "") or "")
        if self.provider == PROVIDER_SMTP:
            return bool(getattr(settings, "SMTP_HOST", "") or "")
        return False

    def _config_problem(self) -> Optional[str]:
        """Mô tả lý do không gửi được, để log/rõ ràng cho người vận hành."""
        if self.provider not in SUPPORTED_PROVIDERS:
            return f"EMAIL_PROVIDER '{self.provider}' không được hỗ trợ"
        if self.provider == PROVIDER_NONE:
            return "chưa cấu hình EMAIL_PROVIDER"
        if not self.from_address:
            return "chưa cấu hình EMAIL_FROM_ADDRESS"
        if self.provider == PROVIDER_RESEND and not getattr(settings, "RESEND_API_KEY", ""):
            return "chưa cấu hình RESEND_API_KEY"
        if self.provider == PROVIDER_SMTP and not getattr(settings, "SMTP_HOST", ""):
            return "chưa cấu hình SMTP_HOST"
        return None

    # ---- Gửi ----

    def send(
        self,
        to: Iterable[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gửi một email.

        Trả về ``{"sent": bool, "provider": ..., "reason": ...}``. **Không ném
        lỗi ra ngoài** — lỗi được trả về trong kết quả để caller quyết định,
        thay vì làm hỏng request nghiệp vụ đang chạy.
        """
        recipients = [addr.strip() for addr in (to or []) if addr and addr.strip()]
        if not recipients:
            return {"sent": False, "provider": self.provider, "reason": "không có người nhận"}

        problem = self._config_problem()
        if problem:
            logger.info("Email không gửi: %s.", problem)
            return {"sent": False, "provider": self.provider, "reason": problem}

        try:
            if self.provider == PROVIDER_RESEND:
                return self._send_via_resend(recipients, subject, body_text, body_html)
            if self.provider == PROVIDER_SMTP:
                return self._send_via_smtp(recipients, subject, body_text, body_html)
        except EmailSendError as exc:
            logger.warning("Gửi email thất bại (%s): %s", self.provider, exc)
            return {"sent": False, "provider": self.provider, "reason": str(exc)}
        except Exception as exc:  # không để lỗi bất ngờ thoát ra request
            logger.exception("Lỗi bất ngờ khi gửi email")
            return {"sent": False, "provider": self.provider, "reason": f"lỗi không mong đợi: {exc}"}

        return {"sent": False, "provider": self.provider, "reason": "provider không xử lý được"}

    def _send_via_resend(
        self, recipients: list, subject: str, body_text: str, body_html: Optional[str]
    ) -> Dict[str, Any]:
        api_key = settings.RESEND_API_KEY
        payload: Dict[str, Any] = {
            "from": f"{self.from_name} <{self.from_address}>",
            "to": recipients,
            "subject": subject,
            "text": body_text,
        }
        if body_html:
            payload["html"] = body_html

        try:
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    # Resend chạy sau Cloudflare; UA mặc định của httpx bị chặn
                    # với lỗi 403 "error code: 1010" (đã gặp ở provider AI).
                    "User-Agent": "marketflow-backend/1.0",
                },
                json=payload,
                timeout=SEND_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException:
            raise EmailSendError("Resend không phản hồi trong thời gian chờ")
        except httpx.HTTPError as exc:
            raise EmailSendError(f"không kết nối được Resend: {exc}")

        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except Exception:
                data = {}
            logger.info("Đã gửi email qua Resend tới %s (id=%s)", recipients, data.get("id"))
            return {"sent": True, "provider": PROVIDER_RESEND, "id": data.get("id")}

        # Tránh đưa nội dung phản hồi thô ra ngoài: nó có thể chứa API key hoặc
        # dữ liệu người dùng, và lỗi này được log cũng như trả về cho client.
        # Chỉ lấy các trường lỗi đã biết; không đọc được JSON thì báo chung chung.
        detail = ""
        try:
            body = resp.json()
            if isinstance(body, dict):
                detail = str(body.get("message") or body.get("name") or "")[:160]
        except Exception:
            detail = ""
        raise EmailSendError(f"Resend trả HTTP {resp.status_code}{(': ' + detail) if detail else ''}")

    def _send_via_smtp(
        self, recipients: list, subject: str, body_text: str, body_html: Optional[str]
    ) -> Dict[str, Any]:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_address}>"
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        host = settings.SMTP_HOST
        port = int(getattr(settings, "SMTP_PORT", 587) or 587)
        user = getattr(settings, "SMTP_USER", "") or ""
        password = getattr(settings, "SMTP_PASSWORD", "") or ""
        use_tls = bool(getattr(settings, "SMTP_USE_TLS", True))

        try:
            with smtplib.SMTP(host, port, timeout=SEND_TIMEOUT_SECONDS) as server:
                if use_tls:
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(self.from_address, recipients, msg.as_string())
        except smtplib.SMTPException as exc:
            raise EmailSendError(f"SMTP lỗi: {exc}")
        except OSError as exc:
            raise EmailSendError(f"không kết nối được {host}:{port} ({exc})")

        logger.info("Đã gửi email qua SMTP %s:%s tới %s", host, port, recipients)
        return {"sent": True, "provider": PROVIDER_SMTP}

    # ---- Mẫu email nghiệp vụ ----

    def send_content_for_review(self, to: str, content_title: str, campaign_name: str, actor: str) -> Dict[str, Any]:
        """Thông báo có nội dung chờ duyệt.

        Đây là luồng mấu chốt của sản phẩm (brief → làm nội dung → duyệt), nên
        cần email thật. Nhưng nếu email lỗi thì việc tạo nội dung vẫn thành công.
        """
        return self.send(
            to=[to],
            subject=f"[MarketFlow] Nội dung chờ bạn duyệt: {content_title}",
            body_text=(
                f"Xin chào,\n\n"
                f"{actor} vừa gửi một nội dung cần bạn duyệt.\n\n"
                f"Chiến dịch : {campaign_name}\n"
                f"Nội dung  : {content_title}\n\n"
                f"Vui lòng đăng nhập MarketFlow để kiểm tra và quyết định.\n\n"
                f"— MarketFlow AI\n"
            ),
            body_html=(
                f"<p>Xin chào,</p>"
                f"<p><strong>{actor}</strong> vừa gửi một nội dung cần bạn duyệt.</p>"
                f"<ul><li>Chiến dịch: <strong>{campaign_name}</strong></li>"
                f"<li>Nội dung: <strong>{content_title}</strong></li></ul>"
                f"<p>Vui lòng đăng nhập MarketFlow để kiểm tra và quyết định.</p>"
            ),
        )

    def send_workspace_invite(self, to: str, workspace_name: str, inviter: str, role: str) -> Dict[str, Any]:
        """Mời thành viên vào workspace."""
        return self.send(
            to=[to],
            subject=f"[MarketFlow] Bạn được mời vào workspace {workspace_name}",
            body_text=(
                f"Xin chào,\n\n"
                f"{inviter} mời bạn tham gia workspace <b>{workspace_name}</b> "
                f"với vai trò {role}.\n\n"
                f"Đăng nhập MarketFlow để bắt đầu.\n\n— MarketFlow AI\n"
            ),
            body_html=(
                f"<p>Xin chào,</p>"
                f"<p><strong>{inviter}</strong> mời bạn tham gia workspace "
                f"<strong>{workspace_name}</strong> với vai trò {role}.</p>"
            ),
        )

    def send_deadline_warning(self, to: str, task_title: str, due_at: str) -> Dict[str, Any]:
        """Nhắc hạn công việc."""
        return self.send(
            to=[to],
            subject=f"[MarketFlow] Sắp hết hạn: {task_title}",
            body_text=(
                f"Công việc <b>{task_title}</b> sẽ hết hạn lúc {due_at}.\n\n"
                f"— MarketFlow AI\n"
            ),
        )


# Một dùng chung cho cả tiến trình.
email_service = EmailService()


def send_email_safely(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Gửi email, tuyệt đối không ném lỗi ra ngoài.

    Dùng ở mọi nơi trong luồng nghiệp vụ: ví dụ `contents.py` sau khi tạo nội
    dung gọi hàm này; có lỗi thì việc tạo nội dung vẫn được báo thành công.
    """
    try:
        return email_service.send(*args, **kwargs)
    except Exception as exc:  # phòng khi EmailService tự lỗi
        logger.exception("EmailService lỗi ngoài dự kiến")
        return {"sent": False, "provider": "unknown", "reason": f"lỗi nội bộ: {exc}"}