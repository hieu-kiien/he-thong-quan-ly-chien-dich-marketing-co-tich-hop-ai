from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Kích hoạt bắt buộc kiểm tra ràng buộc khóa ngoại trên SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
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
    with db_engine.connect() as conn:
        try:
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
        except Exception:
            pass


def init_db(db_engine=engine):
    """Khởi tạo toàn bộ các bảng trong CSDL và đảm bảo tính tương thích schema SQLite."""
    Base.metadata.create_all(bind=db_engine)
    ensure_sqlite_schema_compatibility(db_engine)

