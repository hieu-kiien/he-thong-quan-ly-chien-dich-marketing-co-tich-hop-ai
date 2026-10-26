#!/usr/bin/env python3
"""Chạy 1 lượt tương tác trợ lý AI thực tế (live turn) qua Nginx trên VPS."""

import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = "http://127.0.0.1:8080/api/v1"
EMAIL = "marketer@marketflow.vn"
PASSWORD = "Marketer@123"
CAMPAIGN_ID = 1  # "Ra Mắt Dòng Cold Brew Đóng Chai Tiện Lợi"


def post_json(url: str, data: dict, headers: dict | None = None) -> dict:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=req_headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login() -> str:
    print(f"[*] Đăng nhập {EMAIL}...")
    res = post_json(f"{BASE_URL}/auth/login", {"email": EMAIL, "password": PASSWORD})
    token = res.get("access_token")
    if not token:
        raise RuntimeError(f"Đăng nhập thất bại: {res}")
    print("    Đăng nhập thành công!")
    return token


def create_thread(token: str) -> int:
    print(f"[*] Tạo phiên hội thoại mới gắn với campaign_id={CAMPAIGN_ID}...")
    headers = {"Authorization": f"Bearer {token}"}
    res = post_json(
        f"{BASE_URL}/assistant/threads",
        {"title": "Đánh giá hiệu quả chiến dịch Cold Brew & Đề xuất bài FB", "campaign_id": CAMPAIGN_ID},
        headers=headers,
    )
    thread_id = res.get("id")
    print(f"    Tạo phiên thành công: thread_id={thread_id}")
    return thread_id


def stream_message(token: str, thread_id: int, prompt: str) -> dict:
    url = f"{BASE_URL}/assistant/threads/{thread_id}/messages"
    print(f"[*] Gửi tin nhắn tới thread_id={thread_id} qua SSE:\n    \"{prompt}\"\n")
    req = urllib.request.Request(
        url,
        data=json.dumps({"content": prompt}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    events = []
    text_content = ""
    tool_calls = []
    actions = []
    start_time = time.monotonic()

    current_event = "message"

    with urllib.request.urlopen(req, timeout=240) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace")
            # Heartbeat ping
            if line.startswith(":"):
                continue
            line = line.strip()
            if not line:
                continue

            if line.startswith("event:"):
                current_event = line[6:].strip()
                continue

            if line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    payload = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                events.append({"event": current_event, "data": payload})

                if current_event == "text":
                    text_content = payload.get("content", "")
                elif current_event == "tool_call":
                    tool_calls.append(payload)
                    print(f"\n[TOOL CALL] {payload.get('name')}: status={payload.get('status')}, summary={payload.get('summary')}")
                elif current_event == "action":
                    actions.append(payload)
                    print(f"\n[ACTION PROPOSED] action_id={payload.get('id')}, action_type={payload.get('action_type')}")
                elif current_event == "message_end":
                    msg_obj = payload.get("message", {})
                    if msg_obj.get("content"):
                        text_content = msg_obj["content"]
                    print("\n[MESSAGE END]")
                elif current_event == "error":
                    print(f"\n[ERROR] {payload}")

    total_latency = round(time.monotonic() - start_time, 2)
    return {
        "latency_s": total_latency,
        "events": events,
        "full_text": text_content,
        "tool_calls": tool_calls,
        "actions": actions,
    }


def confirm_proposal(token: str, action_id: int) -> dict:
    print(f"[*] Xác nhận đề xuất action_id={action_id} qua /assistant/actions/{action_id}/confirm...")
    req = urllib.request.Request(
        f"{BASE_URL}/assistant/actions/{action_id}/confirm",
        data=b"{}",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"    Xác nhận thành công: id={res.get('id')}, status={res.get('status')}")
        return res


def main():
    token = login()
    thread_id = create_thread(token)

    prompt = (
        "Hãy tóm tắt hiệu quả chiến dịch này theo từng kênh dựa trên số liệu thực tế trong hệ thống, "
        "soạn 1 bản nháp caption Facebook giúp tăng chuyển đổi và tạo đề xuất bản nháp này lên hệ thống để gửi duyệt."
    )

    result = stream_message(token, thread_id, prompt)

    print("\n" + "=" * 80)
    print("LIVE TURN EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Thread ID: {thread_id}")
    print(f"Turn Latency: {result['latency_s']} s")
    print(f"SSE Events Received: {len(result['events'])}")
    print(f"Tool Calls Count: {len(result['tool_calls'])}")
    for tc in result["tool_calls"]:
        print(f"  - Tool: {tc.get('name')} | Status: {tc.get('status')} | Summary: {tc.get('summary')}")
    print(f"Proposals (Actions) Created: {len(result['actions'])}")
    for a in result["actions"]:
        print(f"  - Action ID {a.get('id')}: {a.get('action_type')} | Title: {a.get('title')}")

    confirmed_action = None
    if result["actions"]:
        first_action_id = result["actions"][0].get("id")
        confirmed_action = confirm_proposal(token, first_action_id)

    # Save to JSON for report generation
    out_data = {
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "campaign_id": CAMPAIGN_ID,
        "thread_id": thread_id,
        "prompt": prompt,
        "latency_s": result["latency_s"],
        "tool_calls": result["tool_calls"],
        "actions": result["actions"],
        "confirmed_action": confirmed_action,
        "full_text": result["full_text"],
        "events_count": len(result["events"]),
    }

    out_file = Path("live_turn_result.json")
    out_file.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Đã lưu kết quả chi tiết vào {out_file}")


if __name__ == "__main__":
    main()
