import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("marketflow.database")

class DatabaseMigrationError(RuntimeError):
    """Ngoại lệ tùy chỉnh khi quá trình migration hoặc kiểm tra tương thích schema CSDL thất bại."""
    pass

from pathlib import Path

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
elif db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////") and db_url != "sqlite:///:memory:":
    raw_path = db_url[len("sqlite:///"):]
    p = Path(raw_path)
    if not p.is_absolute():
        base_target = (settings.BASE_DIR / raw_path.lstrip("./")).resolve()
        if base_target.exists():
            db_url = f"sqlite:///{base_target.as_posix()}"

engine_kwargs = {"echo": False}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(db_url, **engine_kwargs)

# Kích hoạt bắt buộc kiểm tra ràng buộc khóa ngoại và tối ưu hóa đồng thời WAL trên SQLite
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_schema_compatibility(db_engine=engine):
    """Tự động kiểm tra và bổ sung các cột mới vào CSDL SQLite hiện hữu nếu thiếu (Idempotent Zero Migration Failure)."""
    if not str(db_engine.url).startswith("sqlite"):
        return
    try:
        with db_engine.connect() as conn:
            res = conn.exec_driver_sql("PRAGMA table_info(marketing_contents)")
            existing_cols = [row[1] for row in res.fetchall()]
            if existing_cols:
                if "image_url" not in existing_cols:
                    conn.exec_driver_sql("ALTER TABLE marketing_contents ADD COLUMN image_url VARCHAR(1024)")
                if "workspace_id" not in existing_cols:
                    conn.exec_driver_sql("ALTER TABLE marketing_contents ADD COLUMN workspace_id INTEGER DEFAULT 1")
                if "warnings_json" not in existing_cols:
                    conn.exec_driver_sql("ALTER TABLE marketing_contents ADD COLUMN warnings_json TEXT DEFAULT '[]'")

            # 2. Bảng custom_api_keys (Zero Migration Failure)
            table_check = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_api_keys'")
            if not table_check.fetchone():
                from app.models.entities import CustomApiKey
                CustomApiKey.__table__.create(bind=conn)
            else:
                key_cols_res = conn.exec_driver_sql("PRAGMA table_info(custom_api_keys)")
                key_cols = [row[1] for row in key_cols_res.fetchall()]
                if "workspace_id" not in key_cols:
                    conn.exec_driver_sql("ALTER TABLE custom_api_keys ADD COLUMN workspace_id INTEGER")
                if "user_id" not in key_cols:
                    conn.exec_driver_sql("ALTER TABLE custom_api_keys ADD COLUMN user_id INTEGER")
                if "is_active" not in key_cols:
                    conn.exec_driver_sql("ALTER TABLE custom_api_keys ADD COLUMN is_active BOOLEAN DEFAULT 1")
            conn.commit()
    except Exception as e:
        logger.error("Database schema migration failed: %s", e, exc_info=True)
        raise DatabaseMigrationError(f"Database schema migration failed: {e}") from e


def init_db(db_engine=engine):
    """Khởi tạo toàn bộ các bảng trong CSDL và đảm bảo tính tương thích schema SQLite."""
    Base.metadata.create_all(bind=db_engine)
    ensure_sqlite_schema_compatibility(db_engine)

