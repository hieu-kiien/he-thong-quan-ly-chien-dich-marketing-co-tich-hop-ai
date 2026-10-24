#!/usr/bin/env python3
"""Smoke tests for MarketFlow v2 post-cutover verification."""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

def test_health():
    print("=== [1] HEALTH CHECK ===")
    req = urllib.request.Request("http://127.0.0.1:8080/api/v1/health", headers={"User-Agent": "curl/8.5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print("127.0.0.1:8080 /api/v1/health:", data)
        assert data.get("db") == "ok", f"DB not ok: {data}"
        assert data.get("ai_runner") == "ok", f"ai_runner not ok: {data}"
        assert data.get("status") == "ok", f"status not ok: {data}"

    # Also via Cloudflare with non-blocked UA
    req_cf = urllib.request.Request(
        "https://marketing.kienhieu.id.vn/api/v1/health",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req_cf, timeout=10) as resp:
        data_cf = json.loads(resp.read().decode())
        print("https://marketing.kienhieu.id.vn /api/v1/health:", data_cf)
        assert data_cf.get("db") == "ok"
        assert data_cf.get("ai_runner") == "ok"

    print("=> Health check PASS!")


def test_login():
    print("\n=== [2] LOGIN MANAGER CHECK ===")
    payload = json.dumps({"email": "manager@marketflow.vn", "password": "Manager@123"}).encode()
    
    # Via local Nginx 127.0.0.1:8080
    req_local = urllib.request.Request(
        "http://127.0.0.1:8080/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_local, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        token = data.get("access_token")
        assert token, f"No access token: {data}"
        user = data.get("user", {})
        print(f"Local login PASS! User: {user.get('email')} Role: {user.get('role')}")

    # Via Cloudflare
    req_cf = urllib.request.Request(
        "https://marketing.kienhieu.id.vn/api/v1/auth/login",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    )
    with urllib.request.urlopen(req_cf, timeout=10) as resp:
        data_cf = json.loads(resp.read().decode())
        token_cf = data_cf.get("access_token")
        assert token_cf, f"No access token via Cloudflare: {data_cf}"
        print(f"Cloudflare login PASS! Token prefix: {token_cf[:25]}...")

    return token


def test_mcp_access():
    print("\n=== [3] MCP SECURITY & ACCESS CHECK ===")
    # 1. External /mcp through Nginx should return 404
    req_ext = urllib.request.Request("http://127.0.0.1:8080/mcp")
    try:
        urllib.request.urlopen(req_ext, timeout=5)
        raise AssertionError("Nginx /mcp should have returned 404, but succeeded!")
    except urllib.error.HTTPError as exc:
        print(f"Nginx external /mcp returned HTTP {exc.code} (Expected 404): PASS")
        assert exc.code == 404, f"Expected 404, got {exc.code}"

    # 2. Internal runner access to http://127.0.0.1:8000/mcp/
    # POST initialize without token should be 400/401/403/406-ish, NOT connection refused
    req_int = urllib.request.Request(
        "http://127.0.0.1:8000/mcp/",
        data=b'{"jsonrpc":"2.0","method":"initialize","id":1}',
        headers={"Content-Type": "application/json", "Accept": "text/event-stream, application/json"}
    )
    try:
        urllib.request.urlopen(req_int, timeout=5)
        print("Internal MCP /mcp/ reachable: PASS")
    except urllib.error.HTTPError as exc:
        print(f"Internal MCP /mcp/ reachable (HTTP {exc.code}, not connection refused): PASS")
        assert exc.code in (400, 401, 403, 406), f"Unexpected HTTP status {exc.code}"
    except Exception as exc:
        raise AssertionError(f"Internal MCP /mcp/ connection failed: {exc}")


def test_ai_turn_and_memory(token):
    print("\n=== [4] AI ASSISTANT SSE STREAM & MEMORY CHECK ===")
    # 1. Create a thread
    thread_data = json.dumps({"title": "Smoke test thread"}).encode()
    req_thread = urllib.request.Request(
        "http://127.0.0.1:8080/api/v1/assistant/threads",
        data=thread_data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req_thread, timeout=10) as resp:
        thread = json.loads(resp.read().decode())
        thread_id = thread["id"]
        print(f"Created thread #{thread_id}: '{thread['title']}'")

    # 2. Memory before turn
    def get_mem():
        free_out = subprocess.check_output(["free", "-m"], text=True)
        try:
            api_mem = subprocess.check_output(
                ["systemctl", "show", "marketflow-api", "--property=MemoryCurrent"], text=True
            ).strip()
            runner_mem = subprocess.check_output(
                ["systemctl", "show", "marketflow-ai-runner", "--property=MemoryCurrent"], text=True
            ).strip()
        except Exception:
            api_mem, runner_mem = "N/A", "N/A"
        return free_out, api_mem, runner_mem

    free_before, api_mem_before, runner_mem_before = get_mem()
    print("Memory Before AI Turn:")
    print(free_before)
    print(f"Service memory: marketflow-api={api_mem_before}, marketflow-ai-runner={runner_mem_before}")

    # 3. Stream a single AI message
    msg_data = json.dumps({
        "content": "Chào bạn, hãy giới thiệu thật ngắn gọn về bản thân trong 1 câu."
    }).encode()
    req_msg = urllib.request.Request(
        f"http://127.0.0.1:8080/api/v1/assistant/threads/{thread_id}/messages",
        data=msg_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
        }
    )

    print("\nStarting SSE stream request (1 real AI turn)...")
    events = []
    t0 = time.time()
    mem_peaks = []

    with urllib.request.urlopen(req_msg, timeout=120) as stream_resp:
        # Check buffering header
        accel = stream_resp.headers.get("X-Accel-Buffering")
        print(f"X-Accel-Buffering header: {accel}")

        buffer = ""
        while True:
            line = stream_resp.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            buffer += line_str

            # Record memory during turn
            if len(mem_peaks) < 5:
                _, a_mem, r_mem = get_mem()
                mem_peaks.append((time.time() - t0, a_mem, r_mem))

            if line_str.startswith("event:"):
                event_type = line_str[6:].strip()
                events.append({"event": event_type, "time": round(time.time() - t0, 2)})
                print(f"[{round(time.time() - t0, 2)}s] Event received: {event_type}")
            elif line_str.startswith("data:"):
                data_str = line_str[5:].strip()
                try:
                    parsed = json.loads(data_str)
                    if events and "data" not in events[-1]:
                        events[-1]["data_preview"] = (
                            parsed.get("content", "")[:60]
                            or parsed.get("phase", "")
                            or parsed.get("code", "")
                            or list(parsed.keys())
                        )
                except Exception:
                    pass

    duration = round(time.time() - t0, 2)
    print(f"\nAI stream finished in {duration} seconds.")
    print("Events sequence received:")
    for ev in events:
        print(f"  - [{ev['time']}s] event: {ev['event']} (preview: {ev.get('data_preview', '')})")

    free_after, api_mem_after, runner_mem_after = get_mem()
    print("\nMemory After AI Turn:")
    print(free_after)
    print(f"Service memory: marketflow-api={api_mem_after}, marketflow-ai-runner={runner_mem_after}")
    print("Memory samples during turn (t, api, runner):", mem_peaks)

    return events, duration, (api_mem_before, api_mem_after), (runner_mem_before, runner_mem_after)


if __name__ == "__main__":
    test_health()
    mgr_token = test_login()
    test_mcp_access()
    test_ai_turn_and_memory(mgr_token)
    print("\nALL SMOKE CHECKS COMPLETED SUCCESSFULLY!")
