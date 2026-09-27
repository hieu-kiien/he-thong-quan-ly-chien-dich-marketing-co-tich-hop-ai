#!/usr/bin/env python3
"""
scripts/run_load_test.py
========================
Wave 4 Benchmark: 20-Session Concurrent Load Test Harness.

Authoritative Specification:
- 20 concurrent worker sessions simulating continuous CRUD and read operations.
- Verifies 0 "database is locked" errors under concurrent write pressure (WAL mode & busy_timeout).
- Verifies overall error rate < 1.0% and zero data corruption (PRAGMA integrity_check == ok).
- Preserves backend/marketing_campaigns.db SHA256 immutability by operating on an isolated copy.
"""

import os
import sys
import time
import math
import shutil
import tempfile
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

LIVE_DB_PATH = BACKEND_DIR / "marketing_campaigns.db"
EXPECTED_LIVE_SHA256 = "5283845BC15EFA66DEE866262229D6C003E56B2A45098CA692AC903DFF8BBB3B"


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    d0 = s[int(f)] * (c - k)
    d1 = s[int(c)] * (k - f)
    return d0 + d1


def run_load_test():
    print("=" * 80)
    print(" MARKETFLOW AI — WAVE 4 CONCURRENT LOAD TEST (20 SESSIONS)")
    print("=" * 80)

    # 1. Baseline DB Verification
    if LIVE_DB_PATH.exists():
        initial_hash = get_file_sha256(LIVE_DB_PATH)
        print(f"[*] Live DB Baseline SHA256: {initial_hash}")

    # 2. Create isolated temporary database with WAL mode
    temp_dir = tempfile.mkdtemp(prefix="marketflow_load_")
    temp_db_path = Path(temp_dir) / "load_test_marketing.db"
    if LIVE_DB_PATH.exists():
        shutil.copy2(LIVE_DB_PATH, temp_db_path)

    load_db_url = f"sqlite:///{temp_db_path.as_posix()}"
    # CRITICAL: set os.environ["DATABASE_URL"] BEFORE any app imports to isolate FastAPI startup
    os.environ["DATABASE_URL"] = load_db_url

    try:
        from app.core.config import settings
        settings.DATABASE_URL = load_db_url

        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker
        import app.core.database as core_database

        load_engine = create_engine(
            load_db_url,
            connect_args={"check_same_thread": False},
            pool_size=30,
            max_overflow=20,
            echo=False
        )

        @event.listens_for(load_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        LoadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=load_engine)
        core_database.engine = load_engine
        core_database.SessionLocal = LoadSessionLocal
        core_database.ensure_sqlite_schema_compatibility(load_engine)

        import app.main as app_main
        app_main.engine = load_engine
        from app.main import app

        def override_get_db():
            db = LoadSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[core_database.get_db] = override_get_db

        from fastapi.testclient import TestClient
        from app.core.security import create_access_token
        from app.models.entities import User

        # Obtain valid authentication token for users
        with LoadSessionLocal() as s:
            manager_user = s.query(User).filter(User.email == "manager@ictu.edu.vn").first()
            if not manager_user:
                manager_user = s.query(User).first()
            token = create_access_token(data={
                "sub": str(manager_user.id),
                "email": manager_user.email,
                "role": manager_user.role
            })

        auth_headers = {"Authorization": f"Bearer {token}"}

        CONCURRENT_SESSIONS = 20
        CYCLES_PER_SESSION = 15
        print(f"[*] Configuration: {CONCURRENT_SESSIONS} concurrent sessions, {CYCLES_PER_SESSION} CRUD cycles per session")
        print(f"[*] Total planned operations: ~{CONCURRENT_SESSIONS * CYCLES_PER_SESSION * 6} requests")
        print(f"[*] Testing under concurrent read and write pressure...")
        print("-" * 80)

        # Thread-safe telemetry collectors
        telemetry_lock = threading.Lock()
        latencies_ms: List[float] = []
        op_counts = {
            "create": 0,
            "read": 0,
            "update": 0,
            "delete": 0,
            "metrics": 0,
            "success": 0,
            "failed": 0,
            "database_locked_errors": 0
        }
        error_details: List[str] = []

        def worker_session(session_id: int):
            client = TestClient(app)
            local_latencies = []

            for cycle in range(CYCLES_PER_SESSION):
                # 1. READ: List Campaigns
                t0 = time.perf_counter()
                r1 = client.get("/api/v1/campaigns", headers=auth_headers)
                t1 = time.perf_counter()
                local_latencies.append((t1 - t0) * 1000.0)

                with telemetry_lock:
                    op_counts["read"] += 1
                    if r1.status_code == 200:
                        op_counts["success"] += 1
                    else:
                        op_counts["failed"] += 1
                        if "locked" in r1.text.lower():
                            op_counts["database_locked_errors"] += 1
                        error_details.append(f"Session {session_id} read fail: {r1.status_code}")

                # 2. CREATE (WRITE): Create Marketing Content
                payload = {
                    "campaign_id": 1,
                    "channel_id": 1,
                    "title": f"Load Test Content S{session_id}-C{cycle}",
                    "body": f"Continuous load test content payload under 20-thread concurrency. Session {session_id}, cycle {cycle}.",
                    "cta": "Test CTA",
                    "status": "DRAFT"
                }
                t0 = time.perf_counter()
                r2 = client.post("/api/v1/contents", json=payload, headers=auth_headers)
                t1 = time.perf_counter()
                local_latencies.append((t1 - t0) * 1000.0)

                created_id = None
                with telemetry_lock:
                    op_counts["create"] += 1
                    if r2.status_code in (200, 201):
                        op_counts["success"] += 1
                        try:
                            created_id = r2.json().get("id")
                        except Exception:
                            pass
                    else:
                        op_counts["failed"] += 1
                        if "locked" in r2.text.lower():
                            op_counts["database_locked_errors"] += 1
                        error_details.append(f"Session {session_id} create fail: {r2.status_code} - {r2.text[:100]}")

                if created_id:
                    # 3. READ: Get Content by ID
                    t0 = time.perf_counter()
                    r3 = client.get(f"/api/v1/contents/{created_id}", headers=auth_headers)
                    t1 = time.perf_counter()
                    local_latencies.append((t1 - t0) * 1000.0)

                    with telemetry_lock:
                        op_counts["read"] += 1
                        if r3.status_code == 200:
                            op_counts["success"] += 1
                        else:
                            op_counts["failed"] += 1
                            if "locked" in r3.text.lower():
                                op_counts["database_locked_errors"] += 1

                    # 4. UPDATE (WRITE): Update Content
                    t0 = time.perf_counter()
                    r4 = client.put(f"/api/v1/contents/{created_id}", json={
                        "body": f"Updated body content by session {session_id} in cycle {cycle}."
                    }, headers=auth_headers)
                    t1 = time.perf_counter()
                    local_latencies.append((t1 - t0) * 1000.0)

                    with telemetry_lock:
                        op_counts["update"] += 1
                        if r4.status_code == 200:
                            op_counts["success"] += 1
                        else:
                            op_counts["failed"] += 1
                            if "locked" in r4.text.lower():
                                op_counts["database_locked_errors"] += 1
                            error_details.append(f"Session {session_id} update fail: {r4.status_code}")

                    # 5. SUBMIT (STATE TRANSITION): Submit content for review
                    t0 = time.perf_counter()
                    r5 = client.post(f"/api/v1/contents/{created_id}/submit", headers=auth_headers)
                    t1 = time.perf_counter()
                    local_latencies.append((t1 - t0) * 1000.0)

                    with telemetry_lock:
                        op_counts["submit"] = op_counts.get("submit", 0) + 1
                        if r5.status_code == 200:
                            op_counts["success"] += 1
                        else:
                            op_counts["failed"] += 1
                            if "locked" in r5.text.lower():
                                op_counts["database_locked_errors"] += 1
                            error_details.append(f"Session {session_id} submit fail: {r5.status_code} - {r5.text[:100]}")

                    # 6. READ: Campaign KPI / Metrics
                    t0 = time.perf_counter()
                    r6 = client.get("/api/v1/campaigns/1/kpi", headers=auth_headers)
                    t1 = time.perf_counter()
                    local_latencies.append((t1 - t0) * 1000.0)

                    with telemetry_lock:
                        op_counts["metrics"] += 1
                        if r6.status_code == 200:
                            op_counts["success"] += 1
                        else:
                            op_counts["failed"] += 1
                            if "locked" in r6.text.lower():
                                op_counts["database_locked_errors"] += 1

                # Brief sleep between iterations to mimic realistic user pacing (10ms)
                time.sleep(0.01)

            with telemetry_lock:
                latencies_ms.extend(local_latencies)

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=CONCURRENT_SESSIONS) as executor:
            futures = [executor.submit(worker_session, i + 1) for i in range(CONCURRENT_SESSIONS)]
            for f in as_completed(futures):
                f.result()

        total_elapsed = time.perf_counter() - start_time
        total_requests = op_counts["success"] + op_counts["failed"]
        error_rate = (op_counts["failed"] / total_requests * 100.0) if total_requests > 0 else 0.0
        rps = total_requests / total_elapsed if total_elapsed > 0 else 0.0

        p50 = percentile(latencies_ms, 50)
        p95 = percentile(latencies_ms, 95)
        p99 = percentile(latencies_ms, 99)

        print("\n" + "=" * 80)
        print(" LOAD TEST RESULTS (20 CONCURRENT SESSIONS)")
        print("=" * 80)
        print(f" Total Requests Executed      : {total_requests}")
        print(f" Total Elapsed Time          : {total_elapsed:.2f} s")
        print(f" Throughput                   : {rps:.1f} req/s")
        print(f" Successful Operations        : {op_counts['success']}")
        print(f" Failed Operations            : {op_counts['failed']}")
        print(f" Error Rate                   : {error_rate:.2f}%")
        print(f" 'Database is locked' Errors : {op_counts['database_locked_errors']}")
        print(f" Operation Breakdown:")
        print(f"   - Creates (Write)         : {op_counts['create']}")
        print(f"   - Reads (Read)            : {op_counts['read']}")
        print(f"   - Updates (Write)         : {op_counts['update']}")
        print(f"   - Submits (Write)         : {op_counts.get('submit', 0)}")
        print(f"   - Metrics Queries (Read)  : {op_counts['metrics']}")
        print(f" Latency Profile:")
        print(f"   - p50                     : {p50:.2f} ms")
        print(f"   - p95                     : {p95:.2f} ms")
        print(f"   - p99                     : {p99:.2f} ms")
        print(f"   - Max                     : {max(latencies_ms):.2f} ms")
        print("-" * 80)

        # 3. Database Integrity Verification
        with load_engine.connect() as conn:
            integrity_result = conn.exec_driver_sql("PRAGMA integrity_check").fetchone()
            integrity_status = integrity_result[0] if integrity_result else "unknown"
            print(f"[*] SQLite PRAGMA integrity_check: {integrity_status}")

        print("=" * 80)

        # 4. Assertions
        print("[*] Verifying Load Test Success Criteria:")
        print(f"    1. Database Locked Errors == 0: {op_counts['database_locked_errors']} == 0 -> {'PASS' if op_counts['database_locked_errors'] == 0 else 'FAIL'}")
        print(f"    2. Error Rate < 1.0%: {error_rate:.2f}% < 1.0% -> {'PASS' if error_rate < 1.0 else 'FAIL'}")
        print(f"    3. Data Integrity ok: {integrity_status} == 'ok' -> {'PASS' if integrity_status == 'ok' else 'FAIL'}")

        assert op_counts["database_locked_errors"] == 0, (
            f"Concurrency Failure: Encountered {op_counts['database_locked_errors']} 'database is locked' errors!"
        )
        assert error_rate < 1.0, f"Error rate too high: {error_rate:.2f}% >= 1.0%"
        assert integrity_status == "ok", f"Database corruption detected: {integrity_status}"

        print("\n[+] SUCCESS: Concurrent load test passed with 0 locked errors and < 1% error rate.")

    finally:
        try:
            if 'app' in locals() and hasattr(app, 'dependency_overrides'):
                app.dependency_overrides.clear()
        except Exception:
            pass
        try:
            load_engine.dispose()
        except Exception:
            pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.environ.pop("DATABASE_URL", None)

    # 5. Verify live database integrity
    if LIVE_DB_PATH.exists():
        final_hash = get_file_sha256(LIVE_DB_PATH)
        print(f"[*] Live DB Final SHA256: {final_hash}")
        assert final_hash == EXPECTED_LIVE_SHA256, (
            f"FATAL: Live database was modified! Expected {EXPECTED_LIVE_SHA256}, got {final_hash}"
        )
        print("[+] Live database marketing_campaigns.db SHA256 verified strictly preserved.")


if __name__ == "__main__":
    try:
        run_load_test()
        sys.exit(0)
    except AssertionError as ae:
        print(f"[-] Load Test Assertion Failure: {ae}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[-] Load Test Execution Error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
