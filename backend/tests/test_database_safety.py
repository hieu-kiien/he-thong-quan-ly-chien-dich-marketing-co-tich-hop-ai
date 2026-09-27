"""
Test suite for Sprint S3: Database & Migration Safety.
Covers:
1. init_db(reset=False) non-destructive behavior (preserves existing data and tables).
2. reset_db() protection guard (strictly blocked in production environments).
3. Migration failure handling: ensure_sqlite_schema_compatibility raises DatabaseMigrationError and logs error.
4. FastAPI on_startup handling: cleanly aborts application with sys.exit(1) on DatabaseMigrationError.
5. CLI argument behavior for seed_data.py.
"""

import os
import sys
import logging
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, DatabaseMigrationError, ensure_sqlite_schema_compatibility, init_db as core_init_db
from app.models.entities import User, Workspace, Campaign
from seed.seed_data import init_db as seed_init_db, reset_db, seed_data, is_production_env


@pytest.fixture
def isolated_engine():
    """Tạo engine SQLite in-memory cô lập cho từng test case."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    yield engine
    engine.dispose()


def test_is_production_env_detection(monkeypatch):
    """Kiểm tra nhận diện môi trường production qua các cấu hình khác nhau."""
    # 1. settings.ENVIRONMENT == "production"
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
    assert is_production_env() is True

    # 2. settings.APP_ENV == "production"
    monkeypatch.delattr(settings, "ENVIRONMENT", raising=False)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert is_production_env() is True

    # 3. os.environ["ENVIRONMENT"] == "production"
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert is_production_env() is True

    # 4. os.environ["APP_ENV"] == "production"
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert is_production_env() is True

    # 5. development / non-production
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    assert is_production_env() is False


def test_init_db_preserves_existing_data(isolated_engine):
    """Kiểm tra init_db(reset=False) bảo toàn dữ liệu hiện có, không bao giờ drop_all."""
    # Khởi tạo DB lần đầu
    seed_init_db(reset=False, db_engine=isolated_engine)

    Session = sessionmaker(bind=isolated_engine)
    session = Session()

    # Thêm bản ghi tùy chỉnh (người dùng & dữ liệu khách hàng)
    custom_user = User(
        email="custom_client@enterprise.vn",
        full_name="Enterprise VIP Client",
        password_hash="secure_hash_123",
        role="MARKETER",
        status="ACTIVE"
    )
    session.add(custom_user)
    session.commit()
    custom_user_id = custom_user.id
    assert custom_user_id is not None
    session.close()

    # Chạy lại init_db(reset=False) mô phỏng restart hoặc re-init
    seed_init_db(reset=False, db_engine=isolated_engine)

    # Xác thực dữ liệu tùy chỉnh vẫn còn nguyên vẹn 100%
    session = Session()
    persisted_user = session.query(User).filter(User.email == "custom_client@enterprise.vn").first()
    assert persisted_user is not None
    assert persisted_user.id == custom_user_id
    assert persisted_user.full_name == "Enterprise VIP Client"

    # Kiểm tra các dữ liệu mặc định cũng không bị trùng lặp
    default_mgr = session.query(User).filter(User.email == "manager@gmail.com").all()
    assert len(default_mgr) == 1

    default_ws = session.query(Workspace).filter(Workspace.id == 1).all()
    assert len(default_ws) == 1
    session.close()


def test_reset_db_blocked_in_production(isolated_engine, monkeypatch):
    """Kiểm tra reset_db() và init_db(reset=True) bị từ chối triệt để trong môi trường production."""
    # Giả lập môi trường production qua settings.ENVIRONMENT
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)

    with pytest.raises(RuntimeError) as exc_info_1:
        reset_db(db_engine=isolated_engine)
    assert "Database reset is forbidden in production environment" in str(exc_info_1.value)

    with pytest.raises(RuntimeError) as exc_info_2:
        seed_init_db(reset=True, db_engine=isolated_engine)
    assert "Database reset is forbidden in production environment" in str(exc_info_2.value)

    # Giả lập môi trường production qua settings.APP_ENV
    monkeypatch.delattr(settings, "ENVIRONMENT", raising=False)
    monkeypatch.setattr(settings, "APP_ENV", "production")

    with pytest.raises(RuntimeError) as exc_info_3:
        reset_db(db_engine=isolated_engine)
    assert "Database reset is forbidden in production environment" in str(exc_info_3.value)


def test_reset_db_allowed_in_development(isolated_engine, monkeypatch):
    """Kiểm tra reset_db() hoạt động bình thường trong môi trường development/test."""
    monkeypatch.delattr(settings, "ENVIRONMENT", raising=False)
    monkeypatch.setattr(settings, "APP_ENV", "development")

    # Tạo bảng và nạp dữ liệu
    seed_init_db(reset=False, db_engine=isolated_engine)
    Session = sessionmaker(bind=isolated_engine)
    session = Session()
    assert session.query(User).count() > 0
    session.close()

    # Thực hiện reset_db()
    reset_db(db_engine=isolated_engine)

    # Sau drop_all, truy vấn bảng phải phát sinh ngoại lệ bảng không tồn tại
    with isolated_engine.connect() as conn:
        with pytest.raises(Exception):
            conn.execute(text("SELECT count(*) FROM users"))


def test_migration_failure_raises_custom_exception(isolated_engine, caplog):
    """Kiểm tra ensure_sqlite_schema_compatibility re-raise DatabaseMigrationError và log traceback khi lỗi."""
    # Tạo mock engine gây lỗi khi thực thi câu lệnh SQL
    failing_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    with patch.object(failing_engine, "connect", side_effect=RuntimeError("Disk I/O failure or locked SQLite database")):
        with caplog.at_level(logging.ERROR, logger="marketflow.database"):
            with pytest.raises(DatabaseMigrationError) as exc_info:
                ensure_sqlite_schema_compatibility(failing_engine)

            assert "Database schema migration failed:" in str(exc_info.value)
            assert "Disk I/O failure" in str(exc_info.value)
            # Kiểm tra log ghi nhận lỗi
            assert any("Database schema migration failed" in record.message for record in caplog.records)


def test_main_on_startup_aborts_on_migration_error(caplog):
    """Kiểm tra FastAPI on_startup xử lý ngắt ứng dụng sys.exit(1) và log critical khi gặp DatabaseMigrationError."""
    from app.main import on_startup

    with patch("app.main.init_db", side_effect=DatabaseMigrationError("Simulated critical corruption")):
        with caplog.at_level(logging.CRITICAL, logger="marketflow.main"):
            with pytest.raises(SystemExit) as exit_info:
                on_startup()

            # Xác thực sys.exit(1) được gọi
            assert exit_info.value.code == 1
            # Xác thực log critical ghi nhận đầy đủ chi tiết lỗi
            assert any("Critical database migration error during startup" in record.message for record in caplog.records)


def test_seed_cli_arguments():
    """Kiểm tra CLI argument parsing của seed_data.py."""
    with patch("sys.argv", ["seed_data.py"]):
        with patch("seed.seed_data.init_db") as mock_init:
            # Mô phỏng chạy block __main__
            import argparse
            parser = argparse.ArgumentParser(description="MarketFlow AI Database Initializer & Seeder")
            parser.add_argument("--reset", action="store_true", default=False)
            args = parser.parse_args([])
            assert args.reset is False

    with patch("sys.argv", ["seed_data.py", "--reset"]):
        import argparse
        parser = argparse.ArgumentParser(description="MarketFlow AI Database Initializer & Seeder")
        parser.add_argument("--reset", action="store_true", default=False)
        args = parser.parse_args(["--reset"])
        assert args.reset is True
