"""Smoke-test key endpoints with real HTTP over uvicorn (CONTRACT §4).

Tự khởi động uvicorn trên cổng 8000, kiểm tra toàn bộ endpoint chính, sau đó tắt tiến trình.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import httpx

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parents[1]


def run_smoke_test():
    print("Khởi động uvicorn app.main:app trên 127.0.0.1:8000...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=5.0)

    try:
        # Wait for server to start
        connected = False
        for _ in range(30):
            try:
                resp = client.get("/health")
                if resp.status_code == 200:
                    connected = True
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.3)

        if not connected:
            stdout, stderr = proc.communicate(timeout=2)
            print("LỖI: Server uvicorn không phản hồi!")
            print("STDOUT:", stdout.decode("utf-8", errors="replace"))
            print("STDERR:", stderr.decode("utf-8", errors="replace"))
            sys.exit(1)

        print("-> Đã kết nối tới uvicorn server!")

        # 1. GET /health
        h_resp = client.get("/health")
        print(f"1. GET /health -> {h_resp.status_code} {h_resp.json()}")
        assert h_resp.status_code == 200
        assert h_resp.json()["db"] == "ok"

        # 2. POST /api/v1/auth/login
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "manager@marketflow.vn", "password": "Manager@123"},
        )
        print(f"2. POST /api/v1/auth/login -> {login_resp.status_code}")
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. GET /api/v1/auth/me
        me_resp = client.get("/api/v1/auth/me", headers=headers)
        print(f"3. GET /api/v1/auth/me -> {me_resp.status_code} ({me_resp.json()['full_name']})")
        assert me_resp.status_code == 200

        # 4. GET /api/v1/channels
        ch_resp = client.get("/api/v1/channels", headers=headers)
        print(f"4. GET /api/v1/channels -> {ch_resp.status_code} ({len(ch_resp.json())} kênh)")
        assert ch_resp.status_code == 200
        assert len(ch_resp.json()) >= 7

        # 5. GET /api/v1/campaigns
        c_resp = client.get("/api/v1/campaigns", headers=headers)
        print(f"5. GET /api/v1/campaigns -> {c_resp.status_code} ({c_resp.json()['total']} chiến dịch)")
        assert c_resp.status_code == 200
        assert c_resp.json()["total"] >= 5

        # 6. GET /api/v1/contents
        cnt_resp = client.get("/api/v1/contents", headers=headers)
        print(f"6. GET /api/v1/contents -> {cnt_resp.status_code} ({cnt_resp.json()['total']} nội dung)")
        assert cnt_resp.status_code == 200
        assert cnt_resp.json()["total"] >= 5

        # 7. GET /api/v1/schedules
        s_resp = client.get("/api/v1/schedules", headers=headers)
        print(f"7. GET /api/v1/schedules -> {s_resp.status_code} ({len(s_resp.json())} lịch)")
        assert s_resp.status_code == 200

        # 8. GET /api/v1/metrics
        m_resp = client.get("/api/v1/metrics", headers=headers)
        print(f"8. GET /api/v1/metrics -> {m_resp.status_code} ({m_resp.json()['total']} dòng số liệu)")
        assert m_resp.status_code == 200
        assert m_resp.json()["total"] >= 50

        # 9. GET /api/v1/stats/overview
        st_resp = client.get("/api/v1/stats/overview", headers=headers)
        print(f"9. GET /api/v1/stats/overview -> {st_resp.status_code} (views: {st_resp.json()['totals']['views']}, cost: {st_resp.json()['totals']['cost']})")
        assert st_resp.status_code == 200
        assert st_resp.json()["totals"]["views"] > 0
        assert st_resp.json()["has_seed_data"] is True

        # 10. GET /api/v1/brand-profile
        bp_resp = client.get("/api/v1/brand-profile", headers=headers)
        print(f"10. GET /api/v1/brand-profile -> {bp_resp.status_code} ({bp_resp.json()['brand_name']})")
        assert bp_resp.status_code == 200
        assert len(bp_resp.json()["banned_keywords"]) >= 10

        print("\n=> TOÀN BỘ 10 ENDPOINTS ĐÃ ĐƯỢC SMOKE-TEST THÀNH CÔNG VỚI REAL HTTP!")

    finally:
        client.close()
        print("Đang tắt tiến trình uvicorn server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Tiến trình uvicorn server đã dừng.")


if __name__ == "__main__":
    run_smoke_test()
