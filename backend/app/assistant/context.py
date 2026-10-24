"""Ngữ cảnh thực thi công cụ (ToolContext)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.ai import AiMessage, AiThread
from app.models.user import User


@dataclass
class ToolContext:
    db: Session
    user: User
    thread: AiThread
    message: AiMessage


@contextmanager
def get_db_context() -> Iterator[Session]:
    """Lấy database session: tự động dùng override khi chạy test suite hoặc SessionLocal khi chạy thật."""
    from app.core.database import SessionLocal, get_db
    from app.main import app

    if get_db in app.dependency_overrides:
        override = app.dependency_overrides[get_db]
        gen = override()
        yield next(gen)
    else:
        with SessionLocal() as session:
            yield session
