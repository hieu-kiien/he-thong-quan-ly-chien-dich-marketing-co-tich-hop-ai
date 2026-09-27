#!/usr/bin/env python3
"""
scripts/measure_api_latency.py
==============================
Wave 4 Benchmark: Non-AI API Latency across 50 iterations.

Authoritative Specification:
- Benchmarks core non-AI endpoints across 50 iterations:
  1. Health: GET /health and GET /api/v1/health
  2. Auth: POST /api/v1/auth/login and GET /api/v1/auth/me
  3. Campaigns: GET /api/v1/campaigns and GET /api/v1/campaigns/1
  4. Contents: GET /api/v1/contents and GET /api/v1/contents/1
  5. Workspaces: GET /api/v1/workspaces and GET /api/v1/workspaces/1
  6. Brand Kit: GET /api/v1/brand-kit?workspace_id=1
  7. Metrics: GET /api/v1/campaigns/1/kpi and GET /api/v1/campaigns/1/metrics
- Measures round-trip latency and reads server-side X-Process-Time header.
- Computes p50, p95, p99, min, max, avg statistics.
- Asserts non-AI p95 <= 800ms.
- Preserves backend/marketing_campaigns.db SHA256 immutability by operating on an isolated copy.
"""

import os
import sys
import time
import math
import shutil
import tempfile
import hashlib
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


def run_benchmark():
    print("=" * 80)
    print(" MARKETFLOW AI — WAVE 4 NON-AI API LATENCY BENCHMARK (50 ITERATIONS)")
    print("=" * 80)

    # 1. Verify live database baseline
    if LIVE_DB_PATH.exists():
        initial_hash = get_file_sha256(LIVE_DB_PATH)
        print(f"[*] Live DB Baseline SHA256: {initial_hash}")
        if initial_hash != EXPECTED_LIVE_SHA256:
            print(f"[!] Warning: Baseline hash differs from expected: {EXPECTED_LIVE_SHA256}")
    else:
        print(f"[!] Live DB not found at {LIVE_DB_PATH}")

    # 2. Create isolated temporary database for benchmarking
    temp_dir = tempfile.mkdtemp(prefix="marketflow_perf_")
    temp_db_path = Path(temp_dir) / "bench_marketing.db"
    if LIVE_DB_PATH.exists():
        shutil.copy2(LIVE_DB_PATH, temp_db_path)
    
    bench_db_url = f"sqlite:///{temp_db_path.as_posix()}"
    # CRITICAL: set os.environ["DATABASE_URL"] BEFORE any app imports to isolate FastAPI startup
    os.environ["DATABASE_URL"] = bench_db_url

    try:
        from app.core.config import settings
        settings.DATABASE_URL = bench_db_url

        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker
        import app.core.database as core_database

        bench_engine = create_engine(
            bench_db_url,
            connect_args={"check_same_thread": False},
            echo=False
        )

        @event.listens_for(bench_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        BenchSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bench_engine)
        core_database.engine = bench_engine
        core_database.SessionLocal = BenchSessionLocal

        # Initialize schema compatibility & seed if needed
        core_database.ensure_sqlite_schema_compatibility(bench_engine)

        import app.main as app_main
        app_main.engine = bench_engine
        from app.main import app

        def override_get_db():
            db = BenchSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[core_database.get_db] = override_get_db

        from fastapi.testclient import TestClient

        client = TestClient(app)

        # 3. Obtain authentication token for protected endpoints
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "manager@ictu.edu.vn",
            "password": "Manager@123"
        })
        if login_resp.status_code != 200:
            # Fallback to creating token directly
            from app.core.security import create_access_token
            from app.models.entities import User
            with BenchSessionLocal() as s:
                u = s.query(User).filter(User.email == "manager@ictu.edu.vn").first()
                if not u:
                    u = s.query(User).first()
                token = create_access_token(data={
                    "sub": str(u.id),
                    "email": u.email,
                    "role": u.role
                })
        else:
            token = login_resp.json()["access_token"]

        auth_headers = {"Authorization": f"Bearer {token}"}

        # 4. Define non-AI benchmark targets
        test_endpoints = [
            ("Health Check (Root)", "GET", "/health", {}, {}),
            ("Health Check (API v1)", "GET", "/api/v1/health", {}, {}),
            ("Auth Login (Manager)", "POST", "/api/v1/auth/login", {"email": "manager@ictu.edu.vn", "password": "Manager@123"}, {}),
            ("Auth Profile (GET /me)", "GET", "/api/v1/auth/me", {}, auth_headers),
            ("List Campaigns", "GET", "/api/v1/campaigns", {}, auth_headers),
            ("Get Campaign Details", "GET", "/api/v1/campaigns/1", {}, auth_headers),
            ("List Marketing Contents", "GET", "/api/v1/contents", {}, auth_headers),
            ("Get Content Details", "GET", "/api/v1/contents/1", {}, auth_headers),
            ("List Workspaces", "GET", "/api/v1/workspaces", {}, auth_headers),
            ("Get Workspace Details", "GET", "/api/v1/workspaces/1", {}, auth_headers),
            ("Get Brand Kit", "GET", "/api/v1/brand-kit?workspace_id=1", {}, auth_headers),
            ("Get Campaign KPI", "GET", "/api/v1/campaigns/1/kpi", {}, auth_headers),
            ("Get Campaign Metrics", "GET", "/api/v1/campaigns/1/metrics", {}, auth_headers),
        ]

        ITERATIONS = 50
        print(f"[*] Running {ITERATIONS} iterations across {len(test_endpoints)} non-AI endpoints...")
        print(f"[*] Total API calls to execute: {ITERATIONS * len(test_endpoints)}")
        print("-" * 80)

        results_by_endpoint: Dict[str, List[float]] = {}
        server_times_by_endpoint: Dict[str, List[float]] = {}
        all_latencies_ms: List[float] = []
        all_server_times_ms: List[float] = []
        error_count = 0

        # Warm-up pass (3 iterations)
        for name, method, path, payload, headers in test_endpoints:
            if method == "GET":
                client.get(path, headers=headers)
            elif method == "POST":
                client.post(path, json=payload, headers=headers)

        # Main benchmark loop
        for it in range(1, ITERATIONS + 1):
            if it % 10 == 0 or it == 1:
                print(f"    --> Iteration {it}/{ITERATIONS} in progress...")

            for name, method, path, payload, headers in test_endpoints:
                if name not in results_by_endpoint:
                    results_by_endpoint[name] = []
                    server_times_by_endpoint[name] = []

                t_start = time.perf_counter()
                if method == "GET":
                    resp = client.get(path, headers=headers)
                elif method == "POST":
                    resp = client.post(path, json=payload, headers=headers)
                t_end = time.perf_counter()

                latency_ms = (t_end - t_start) * 1000.0
                results_by_endpoint[name].append(latency_ms)
                all_latencies_ms.append(latency_ms)

                # Parse X-Process-Time from TimingMiddleware
                x_proc = resp.headers.get("X-Process-Time")
                if x_proc:
                    try:
                        s_time_ms = float(x_proc) * 1000.0
                        server_times_by_endpoint[name].append(s_time_ms)
                        all_server_times_ms.append(s_time_ms)
                    except ValueError:
                        pass

                if resp.status_code >= 500:
                    error_count += 1
                    print(f"    [!] Error on {name}: {resp.status_code} - {resp.text}")

        print("\n" + "=" * 80)
        print(" BENCHMARK RESULTS SUMMARY TABLE (50 ITERATIONS)")
        print("=" * 80)
        print(f"{'Endpoint':<26} | {'Min':>6} | {'Avg':>6} | {'p50':>6} | {'p95':>6} | {'p99':>6} | {'Max':>6} | {'Status'}")
        print("-" * 80)

        individual_pass = True
        for name, latencies in results_by_endpoint.items():
            min_l = min(latencies)
            avg_l = sum(latencies) / len(latencies)
            p50_l = percentile(latencies, 50)
            p95_l = percentile(latencies, 95)
            p99_l = percentile(latencies, 99)
            max_l = max(latencies)
            status = "PASS" if p95_l <= 800.0 else "FAIL"
            if p95_l > 800.0:
                individual_pass = False

            print(f"{name:<26} | {min_l:>5.1f}ms | {avg_l:>5.1f}ms | {p50_l:>5.1f}ms | {p95_l:>5.1f}ms | {p99_l:>5.1f}ms | {max_l:>5.1f}ms | {status}")

        print("-" * 80)
        overall_min = min(all_latencies_ms)
        overall_avg = sum(all_latencies_ms) / len(all_latencies_ms)
        overall_p50 = percentile(all_latencies_ms, 50)
        overall_p95 = percentile(all_latencies_ms, 95)
        overall_p99 = percentile(all_latencies_ms, 99)
        overall_max = max(all_latencies_ms)
        overall_status = "PASS" if overall_p95 <= 800.0 else "FAIL"

        print(f"{'OVERALL NON-AI METRICS':<26} | {overall_min:>5.1f}ms | {overall_avg:>5.1f}ms | {overall_p50:>5.1f}ms | {overall_p95:>5.1f}ms | {overall_p99:>5.1f}ms | {overall_max:>5.1f}ms | {overall_status}")
        print("=" * 80)

        if all_server_times_ms:
            srv_p50 = percentile(all_server_times_ms, 50)
            srv_p95 = percentile(all_server_times_ms, 95)
            print(f"[*] TimingMiddleware (X-Process-Time) Server-Side: p50={srv_p50:.2f}ms, p95={srv_p95:.2f}ms")

        # 5. Assertions
        print(f"\n[*] SLA Verification:")
        print(f"    - Target Threshold: non-AI p95 <= 800.0 ms")
        print(f"    - Measured Overall p95: {overall_p95:.2f} ms")
        print(f"    - Server 500 Errors: {error_count}")

        assert error_count == 0, f"Expected 0 server errors, got {error_count}"
        assert overall_p95 <= 800.0, f"Latency SLA violated! Overall p95 {overall_p95:.2f}ms > 800ms"
        assert individual_pass, "At least one individual endpoint exceeded 800ms p95 threshold"

        print("\n[+] SUCCESS: Non-AI API latency SLA strictly satisfied (p95 <= 800ms) across 50 iterations.")

    finally:
        # Cleanup temporary benchmark database
        try:
            if 'app' in locals() and hasattr(app, 'dependency_overrides'):
                app.dependency_overrides.clear()
        except Exception:
            pass
        try:
            bench_engine.dispose()
        except Exception:
            pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.environ.pop("DATABASE_URL", None)

    # 6. Verify live database integrity
    if LIVE_DB_PATH.exists():
        final_hash = get_file_sha256(LIVE_DB_PATH)
        print(f"[*] Live DB Final SHA256: {final_hash}")
        assert final_hash == EXPECTED_LIVE_SHA256, (
            f"FATAL: Live database was modified! Expected {EXPECTED_LIVE_SHA256}, got {final_hash}"
        )
        print("[+] Live database marketing_campaigns.db SHA256 verified strictly preserved.")


if __name__ == "__main__":
    try:
        run_benchmark()
        sys.exit(0)
    except AssertionError as ae:
        print(f"[-] SLA Assertion Failure: {ae}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[-] Benchmark Execution Error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
