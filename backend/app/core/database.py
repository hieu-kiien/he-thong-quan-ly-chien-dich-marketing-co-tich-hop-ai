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


def _backfill_tenant_workspace_ids(db_engine=engine, conn=None):
    """Gán workspace_id cho các bản ghi còn NULL dựa trên campaign cha.

    - Content : lấy workspace_id từ campaign cha (nếu campaign đã có workspace).
    - Campaign: ưu tiên workspace mà ``workspaces.owner_id = campaigns.owner_id``;
                nếu không có, lấy workspace đầu tiên mà owner là thành viên
                (``workspace_members``); nếu vẫn không có thì giữ NULL
                (không đoán bừa) và chỉ log cảnh báo.

    Idempotent: chỉ UPDATE dòng có ``workspace_id IS NULL``.

    Thứ tự: content (theo campaign đã có workspace) -> campaign -> content lần 2
    (theo campaign vừa được gán ở bước trên) để không sót nội dung.
    """
    own_conn = conn is None
    try:
        if own_conn:
            conn = db_engine.connect()

        required = {"marketing_contents", "campaigns", "workspaces", "workspace_members"}
        existing = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if not required.issubset(existing):
            logger.info("Tenant backfill skipped: thiếu bảng %s", sorted(required - existing))
            return

        # SAVEPOINT để lỗi ở backfill không làm hỏng phần schema ALTER đã chạy trước đó.
        savepoint_ok = False
        try:
            conn.exec_driver_sql("SAVEPOINT tenant_ws_backfill")
            savepoint_ok = True
        except Exception:
            logger.debug("Khong tao duoc SAVEPOINT cho tenant backfill", exc_info=True)

        stats = {}
        try:
            # 1) Content -> workspace của campaign cha (campaign đã có workspace)
            res = conn.exec_driver_sql(
                "UPDATE marketing_contents "
                "SET workspace_id = (SELECT c.workspace_id FROM campaigns c WHERE c.id = marketing_contents.campaign_id) "
                "WHERE workspace_id IS NULL "
                "AND campaign_id IN (SELECT id FROM campaigns WHERE workspace_id IS NOT NULL)"
            )
            stats["content_from_campaign"] = max(int(getattr(res, "rowcount", 0) or 0), 0)

            # 2) Campaign -> workspace mà owner sở hữu
            res = conn.exec_driver_sql(
                "UPDATE campaigns "
                "SET workspace_id = (SELECT w.id FROM workspaces w WHERE w.owner_id = campaigns.owner_id ORDER BY w.id LIMIT 1) "
                "WHERE workspace_id IS NULL "
                "AND owner_id IN (SELECT owner_id FROM workspaces WHERE owner_id IS NOT NULL)"
            )
            stats["campaign_from_owner"] = max(int(getattr(res, "rowcount", 0) or 0), 0)

            # 3) Campaign -> workspace đầu tiên mà owner là thành viên
            res = conn.exec_driver_sql(
                "UPDATE campaigns "
                "SET workspace_id = (SELECT MIN(wm.workspace_id) FROM workspace_members wm WHERE wm.user_id = campaigns.owner_id) "
                "WHERE workspace_id IS NULL "
                "AND owner_id IN (SELECT user_id FROM workspace_members)"
            )
            stats["campaign_from_membership"] = max(int(getattr(res, "rowcount", 0) or 0), 0)

            # 4) Content lần 2: nội dung của campaign vừa được gán workspace ở bước 2-3
            res = conn.exec_driver_sql(
                "UPDATE marketing_contents "
                "SET workspace_id = (SELECT c.workspace_id FROM campaigns c WHERE c.id = marketing_contents.campaign_id) "
                "WHERE workspace_id IS NULL "
                "AND campaign_id IN (SELECT id FROM campaigns WHERE workspace_id IS NOT NULL)"
            )
            stats["content_after_campaign"] = max(int(getattr(res, "rowcount", 0) or 0), 0)
        except Exception:
            logger.warning(
                "Tenant workspace backfill khong hoan tat, giu nguyen du lieu cu: %s",
                exc_info=True,
            )
            if savepoint_ok:
                try:
                    conn.exec_driver_sql("ROLLBACK TO SAVEPOINT tenant_ws_backfill")
                    conn.exec_driver_sql("RELEASE SAVEPOINT tenant_ws_backfill")
                except Exception:
                    logger.debug("Khong rollback duoc SAVEPOINT tenant backfill", exc_info=True)
            return
        finally:
            if savepoint_ok:
                try:
                    conn.exec_driver_sql("RELEASE SAVEPOINT tenant_ws_backfill")
                except Exception:
                    logger.debug("Khong release duoc SAVEPOINT tenant backfill", exc_info=True)

        assigned = sum(stats.values())
        if assigned:
            logger.info(
                "Tenant backfill: da gan workspace_id cho %s dong (content_from_campaign=%s, "
                "campaign_from_owner=%s, campaign_from_membership=%s, content_after_campaign=%s)",
                assigned,
                stats["content_from_campaign"],
                stats["campaign_from_owner"],
                stats["campaign_from_membership"],
                stats["content_after_campaign"],
            )
    except Exception:
        # Không được phép làm hỏng startup vì migration dữ liệu.
        logger.warning("Tenant workspace backfill that bai, bo qua.", exc_info=True)
    finally:
        if own_conn and conn is not None:
            try:
                conn.commit()
            except Exception:
                logger.debug("Khong commit duoc tenant backfill", exc_info=True)
            finally:
                conn.close()


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

            # Backfill tenant: gán workspace_id cho dữ liệu legacy còn NULL để không
            # rơi vào vùng fail-closed của tầng phân quyền (idempotent, bọc try/except).
            _backfill_tenant_workspace_ids(db_engine=db_engine, conn=conn)

            # Cảnh báo toàn vẹn tenant: các bản ghi còn thiếu workspace_id sẽ bị từ chối
            # truy cập ở tầng phân quyền (fail-closed). Cần migration để gán workspace.
            try:
                orphan_campaigns = conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM campaigns WHERE workspace_id IS NULL"
                ).scalar()
                orphan_contents = conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM marketing_contents WHERE workspace_id IS NULL"
                ).scalar()
                if orphan_campaigns or orphan_contents:
                    logger.warning(
                        "Tenant integrity: %s campaign(s) and %s content row(s) still have NULL workspace_id "
                        "and will be rejected by record-level authorization. Run a data migration.",
                        orphan_campaigns, orphan_contents,
                    )
            except Exception:
                logger.debug("Tenant integrity probe skipped", exc_info=True)

            conn.commit()
    except Exception as e:
        logger.error("Database schema migration failed: %s", e, exc_info=True)
        raise DatabaseMigrationError(f"Database schema migration failed: {e}") from e


def init_db(db_engine=engine):
    """Khởi tạo toàn bộ các bảng trong CSDL và đảm bảo tính tương thích schema SQLite."""
    Base.metadata.create_all(bind=db_engine)
    ensure_sqlite_schema_compatibility(db_engine)

