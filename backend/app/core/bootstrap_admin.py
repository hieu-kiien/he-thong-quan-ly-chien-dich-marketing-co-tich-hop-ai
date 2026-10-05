"""Bootstrap tai khoan ADMIN tu bien moi truong (self-host).

Ly do can co: endpoint dang ky co chu dong chan leo thang dac quyen (tu dang ky
luon la MARKETER). Do do khong co duong nao tao ADMIN qua API. Neu khong co
co che nay, moi endpoint gan ADMIN - ke ca GET /export/data - se khong bao gio
goi duoc tren moi deployment.

Quy tac an toan:
- Chi tao user moi. KHONG demote user dang ton tai (ke ca khi bien sai).
- KHONG tu sinh mat khau: thieu BOOTSTRAP_ADMIN_PASSWORD thi bo qua, khong ghi log.
- Idempotent: chay lai nhieu lan khong tao trung.
"""

import logging
import os

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 12


def ensure_bootstrap_admin(db: Session) -> str:
    """Dam bao co it nhat mot ADMIN. Tra ve trang thai de log."""
    email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or ""

    if not email or not password:
        return "skipped"

    if len(password) < MIN_PASSWORD_LENGTH:
        # Chi bao loi, KHONG ghi ban ro password.
        return "rejected_weak_password"

    user = db.query(User).filter(User.email == email).first()
    if user:
        if user.role == "ADMIN":
            return "already_admin"
        # KHONG tu demote: co the la tai khoan that dang dung chung email.
        return "conflict_email_in_use"

    db.add(
        User(
            email=email,
            full_name=(os.getenv("BOOTSTRAP_ADMIN_NAME") or "Platform Admin").strip(),
            password_hash=hash_password(password),
            role="ADMIN",
            status="ACTIVE",
        )
    )
    db.commit()
    return "created"


def run_bootstrap_admin() -> str:
    """Tao session rieng, khong phu thuocc request dang chay."""
    db = SessionLocal()
    try:
        result = ensure_bootstrap_admin(db)
    finally:
        db.close()

    if result == "created":
        logger.info("Bootstrap ADMIN created from BOOTSTRAP_ADMIN_EMAIL.")
    elif result == "already_admin":
        logger.info("Bootstrap ADMIN already present; no change.")
    elif result == "rejected_weak_password":
        logger.warning(
            "BOOTSTRAP_ADMIN_PASSWORD shorter than %d chars; ADMIN not created.",
            MIN_PASSWORD_LENGTH,
        )
    elif result == "conflict_email_in_use":
        logger.error(
            "BOOTSTRAP_ADMIN_EMAIL matches an existing non-ADMIN user; "
            "ADMIN not created. Promote that user manually."
        )
    else:
        logger.info("BOOTSTRAP_ADMIN_EMAIL/PASSWORD not set; skipping ADMIN bootstrap.")
    return result
