"""Kiểm thử cho Interactive Canvas & Multi-Turn Conversational AI Copilot (`POST /api/v1/ai/chat`)."""

from fastapi.testclient import TestClient


def test_ai_chat_canvas_multi_turn_and_context_control(client: TestClient, marketer_headers: dict):
    """Người dùng bật/tắt chip ngữ cảnh (`context_flags`) thì AI chỉ nhận đúng dữ liệu được cho phép
    và trả về nguyên văn `prompt_preview` minh bạch."""
    payload = {
        "channel_code": "facebook",
        "message": "Làm cho đoạn mở đầu sắc bén hơn nhưng giữ nguyên ý của tôi",
        "history": [
            {"role": "user", "content": "Tôi đang viết bài bán khóa học thực chiến"},
            {"role": "assistant", "content": "Chào bạn, hãy gửi bản nháp trên bàn viết để tôi hỗ trợ."},
        ],
        "canvas": {
            "title": "Khóa học Marketing cho chủ shop nhỏ",
            "body": "Tự tay chạy quảng cáo và chốt đơn trên Zalo, không cần thuê agency đắt đỏ.",
            "cta": "Nhắn tin nhận lộ trình học",
        },
        "context_flags": {
            "include_campaign": False,
            "include_product_usp": True,
            "include_brand_kit": False,
            "include_canvas_draft": True,
            "custom_product_name": "Lớp Học Quảng Cáo Thực Chiến 1 Kèm 1",
            "custom_product_usp": "Cầm tay chỉ việc trên tài khoản thật, hoàn học phí nếu không tự chạy được",
        },
        "preferred_provider": "gemini",
        "preferred_model": "gemini-2.5-flash",
    }
    resp = client.post("/api/v1/ai/chat", json=payload, headers=marketer_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["reply"]
    assert data["suggested_canvas"] is not None
    assert "Lớp Học Quảng Cáo Thực Chiến 1 Kèm 1" in data["prompt_preview"]
    assert "=== SYSTEM PROMPT ===" in data["prompt_preview"]
    assert "=== USER PROMPT ===" in data["prompt_preview"]
    # Kiểm tra quyền kiểm soát ngữ cảnh: đã tắt include_campaign và include_brand_kit
    joined_ctx = " | ".join(data["context_used"])
    assert "Sản phẩm & USP" in joined_ctx
    assert "Bàn soạn thảo hiện tại" in joined_ctx
    assert "Chiến dịch:" not in joined_ctx
    assert "Brand Kit:" not in joined_ctx


def test_ai_chat_canvas_vn_zalo_inbox_and_livestream_scripts(client: TestClient, marketer_headers: dict):
    """Kiểm thử 2 định dạng thực chiến SME Việt Nam: Kịch bản Chốt đơn Inbox Zalo/Messenger & Livestream."""
    zalo_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "zalo_oa",
            "message": "Viết kịch bản chốt đơn inbox",
            "quick_action": "ZALO_INBOX_SCRIPT",
            "canvas": {"title": "", "body": "", "cta": ""},
            "context_flags": {
                "include_campaign": False,
                "include_product_usp": True,
                "include_brand_kit": False,
                "include_canvas_draft": False,
                "custom_product_name": "Serum Nghệ Đỏ Nano",
                "custom_product_usp": "Mờ thâm mụn sau 14 ngày, đổi trả miễn phí 7 ngày nếu kích ứng",
            },
        },
        headers=marketer_headers,
    )
    assert zalo_resp.status_code == 200, zalo_resp.text
    zalo_data = zalo_resp.json()
    assert "BƯỚC 1" in zalo_data["suggested_canvas"]["body"]
    assert "BƯỚC 3 — XỬ LÝ 3 TỪ CHỐI" in zalo_data["suggested_canvas"]["body"]
    assert "Serum Nghệ Đỏ Nano" in zalo_data["suggested_canvas"]["body"]
    assert len(zalo_data["alternatives"]) >= 3

    live_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "tiktok",
            "message": "Lên khung kịch bản livestream 15 phút",
            "quick_action": "LIVESTREAM_SCRIPT",
            "canvas": {"title": "", "body": "", "cta": ""},
            "context_flags": {
                "include_campaign": False,
                "include_product_usp": True,
                "include_brand_kit": False,
                "include_canvas_draft": False,
                "custom_product_name": "Nồi Chiên Hơi Nước 7L",
                "custom_product_usp": "Giữ trọn độ ẩm món nướng, bảo hành 24 tháng tận nhà",
            },
        },
        headers=marketer_headers,
    )
    assert live_resp.status_code == 200, live_resp.text
    live_data = live_resp.json()
    assert "PHÚT 00:00 - 03:00" in live_data["suggested_canvas"]["body"]
    assert "Nồi Chiên Hơi Nước 7L" in live_data["suggested_canvas"]["body"]


def test_ai_chat_canvas_rewrite_selected_text_and_anti_cliche(client: TestClient, marketer_headers: dict):
    """Kiểm thử bôi đen sửa cục bộ (`selected_text`) và khử văn mẫu AI (`ANTI_CLICHE`)."""
    sel_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "facebook",
            "message": "Viết lại câu đang bôi đen cho ấn tượng hơn",
            "quick_action": "REWRITE_SELECTION",
            "canvas": {
                "title": "Bàn nâng hạ thông minh",
                "body": "Đoạn đầu giữ nguyên. Chiếc bàn này giúp làm việc đỡ đau lưng. Đoạn cuối giữ nguyên.",
                "cta": "Đặt mua ngay",
                "selected_text": "Chiếc bàn này giúp làm việc đỡ đau lưng.",
            },
            "context_flags": {
                "include_campaign": False,
                "include_product_usp": True,
                "include_brand_kit": False,
                "include_canvas_draft": True,
                "custom_product_name": "Bàn Nâng Hạ Ergonomic",
                "custom_product_usp": "Motor kép nâng tải 120kg siêu êm dưới 45dB",
            },
        },
        headers=marketer_headers,
    )
    assert sel_resp.status_code == 200, sel_resp.text
    sel_data = sel_resp.json()
    assert sel_data["suggested_canvas"]["replaced_selection"]
    assert "120kg" in sel_data["suggested_canvas"]["replaced_selection"]
    assert "Đoạn đầu giữ nguyên." in sel_data["suggested_canvas"]["body"]
    assert "Đoạn cuối giữ nguyên." in sel_data["suggested_canvas"]["body"]

    cliche_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "facebook",
            "message": "Khử văn mẫu AI",
            "quick_action": "ANTI_CLICHE",
            "canvas": {
                "title": "Phần mềm kế toán SME",
                "body": "Trong bối cảnh hiện nay, chúng tôi mang đến giải pháp tối ưu và toàn diện với đội ngũ tận tâm.",
                "cta": "Tìm hiểu thêm",
            },
        },
        headers=marketer_headers,
    )
    assert cliche_resp.status_code == 200, cliche_resp.text
    cliche_body = cliche_resp.json()["suggested_canvas"]["body"].lower()
    assert "giải pháp tối ưu" not in cliche_body
    assert "tận tâm" not in cliche_body
    assert "tìm hiểu thêm" not in cliche_resp.json()["suggested_canvas"]["cta"].lower()


def test_test_ai_connection_with_custom_base_url(client: TestClient, marketer_headers: dict):
    """Kiểm thử hỗ trợ `base_url` tùy chỉnh cho các cổng OpenAI-compatible."""
    ok_resp = client.post(
        "/api/v1/settings/test-ai-connection",
        json={
            "provider": "opencode",
            "api_key": "sk-mock-custom-gateway-key",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
        },
        headers=marketer_headers,
    )
    assert ok_resp.status_code == 200, ok_resp.text
    assert ok_resp.json()["success"] is True

    bad_resp = client.post(
        "/api/v1/settings/test-ai-connection",
        json={
            "provider": "opencode",
            "api_key": "real_looking_key_for_url_check",
            "model": "deepseek-chat",
            "base_url": "ftp://invalid-scheme.example.com",
        },
        headers=marketer_headers,
    )
    assert bad_resp.status_code == 200
    assert bad_resp.json()["success"] is False
    assert "http://" in bad_resp.json()["message"]


def test_freeform_scratchpad_content_and_locked_blocks(client: TestClient, marketer_headers: dict):
    """Kiểm thử Lưu Nháp Tự Do (không cần chọn Chiến dịch trước -> tự gắn vào Scratchpad)
    và cơ chế Khóa Khối (Block Locking 🔒) không bao giờ bị AI ghi đè."""
    import json

    blocks_payload = [
        {"id": "b_hook", "type": "hook", "label": "Hook 3 giây", "content": "Mở bài thủ công đã chốt cứng!", "locked": True},
        {"id": "b_body", "type": "body", "label": "Thân bài", "content": "Nội dung nháp cần AI viết thêm", "locked": False},
        {"id": "b_fc", "type": "first_comment", "label": "Comment đầu tiên", "content": "Link đặt hàng: https://shop.vn", "locked": True},
    ]

    # 1. Lưu bài viết tự do không truyền campaign_id
    create_resp = client.post(
        "/api/v1/contents",
        json={
            "channel_id": 1,
            "title": "Bài viết tự do chưa gắn chiến dịch",
            "body": "Nội dung nháp cần AI viết thêm",
            "cta": "Nhắn tin ngay",
            "blocks_json": json.dumps(blocks_payload, ensure_ascii=False),
        },
        headers=marketer_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["campaign_id"] is not None
    assert "Mở bài thủ công đã chốt cứng!" in created["blocks_json"]

    # 2. Gửi vào AI Chat kèm khối đã khóa (locked=True) -> AI tuyệt đối giữ nguyên khối đã khóa
    chat_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "facebook",
            "message": "Viết lại thân bài và gợi ý 5 câu hook mới",
            "quick_action": "HOOK_5",
            "canvas": {
                "title": "Mở bài thủ công đã chốt cứng!",
                "body": "Nội dung nháp cần AI viết thêm",
                "cta": "Nhắn tin ngay",
                "blocks": blocks_payload,
            },
            "context_flags": {
                "include_campaign": False,
                "include_product_usp": True,
                "include_brand_kit": False,
                "include_canvas_draft": True,
                "custom_product_name": "Máy Ép Chậm Nguyên Quả",
                "custom_product_usp": "Ép kiệt bã 98%, bảo hành động cơ 5 năm",
            },
        },
        headers=marketer_headers,
    )
    assert chat_resp.status_code == 200, chat_resp.text
    sug = chat_resp.json()["suggested_canvas"]
    # Vì khối hook và first_comment đã locked=True nên phải giữ nguyên 100%
    assert sug["title"] == "Mở bài thủ công đã chốt cứng!"
    assert sug["first_comment"] == "Link đặt hàng: https://shop.vn"
    out_hook_block = next(b for b in sug["blocks"] if b["id"] == "b_hook")
    assert out_hook_block["locked"] is True
    assert out_hook_block["content"] == "Mở bài thủ công đã chốt cứng!"


def test_persistent_chat_threads_and_muse_memory_board(client: TestClient, marketer_headers: dict):
    """Kiểm thử Hội thoại Dài hạn (Persistent Threads) & Bảng Tư Duy Muse AI (Winning Post + Custom /skill)."""
    # 1. Tạo thẻ Bài Mẫu Ra Đơn (WINNING_POST) và Lệnh tắt (/seeding_zalo) trên Bảng Muse AI
    win_resp = client.post(
        "/api/v1/ai/muse-cards",
        json={
            "title": "Bài bán Combo Trà Dưỡng Nhan chốt 80 đơn",
            "card_type": "WINNING_POST",
            "content": "Chị em văn phòng thức khuya da xỉn màu thì chỉ cần 1 bình trà kỷ tử táo đỏ mỗi sáng!",
            "tags": ["tra_duong_nhan", "winning"],
            "is_pinned": True,
        },
        headers=marketer_headers,
    )
    assert win_resp.status_code == 201, win_resp.text

    skill_resp = client.post(
        "/api/v1/ai/muse-cards",
        json={
            "title": "Lệnh viết kịch bản Seeding 3 người",
            "card_type": "CUSTOM_SKILL",
            "content": "Người A hỏi giá -> Người B khen đã mua dùng tốt -> Chủ shop chốt ưu đãi.",
            "skill_trigger": "seeding_3_nguoi",
            "skill_instruction": "Viết đoạn hội thoại seeding tự nhiên gồm 3 bình luận qua lại dưới bài quảng cáo.",
            "is_pinned": True,
        },
        headers=marketer_headers,
    )
    assert skill_resp.status_code == 201, skill_resp.text
    assert skill_resp.json()["skill_trigger"] == "/seeding_3_nguoi"

    # 2. Tạo Cuộc trò chuyện dài hạn (Thread)
    thread_resp = client.post(
        "/api/v1/ai/threads",
        json={"title": "Chiến lược Trà Dưỡng Nhan Tháng 11", "channel_code": "facebook"},
        headers=marketer_headers,
    )
    assert thread_resp.status_code == 201, thread_resp.text
    thread_id = thread_resp.json()["id"]

    # 3. Chat trong Thread và dùng lệnh /seeding_3_nguoi
    chat_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "thread_id": thread_id,
            "channel_code": "facebook",
            "message": "/seeding_3_nguoi cho sản phẩm Trà Dưỡng Nhan",
            "canvas": {"title": "", "body": "", "cta": ""},
            "context_flags": {
                "include_muse_memory": True,
                "include_winning_posts": True,
                "custom_product_name": "Trà Dưỡng Nhan 7 Vị",
                "custom_product_usp": "Thảo mộc sấy lạnh giữ nguyên dưỡng chất",
            },
        },
        headers=marketer_headers,
    )
    assert chat_resp.status_code == 200, chat_resp.text
    chat_data = chat_resp.json()
    assert chat_data["thread_id"] == thread_id
    ctx_str = " | ".join(chat_data["context_used"])
    assert "Kho Bài Mẫu Ra Đơn" in ctx_str
    assert "/seeding_3_nguoi" in ctx_str

    # 4. Mở lại Thread kiểm tra tin nhắn đã được lưu bền vững trong CSDL
    detail_resp = client.get(f"/api/v1/ai/threads/{thread_id}", headers=marketer_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["message_count"] == 2
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"


def test_agent_staged_proposal_execute_and_atomic_undo(client: TestClient, marketer_headers: dict):
    """Kiểm thử LLM Điều khiển Dự án: Đề xuất Thẻ Kế Hoạch -> Bấm [Thực thi] -> Bấm [Hoàn tác (Undo)]."""
    # 1. Nhập số liệu bằng ngôn ngữ tự nhiên trong khung chat
    chat_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "facebook",
            "message": "Báo cáo hôm nay: tiêu 500k, ra 25 tin nhắn, chốt 6 đơn thu về 2tr4",
            "canvas": {"title": "", "body": "", "cta": ""},
            "context_flags": {"enable_project_control": True},
        },
        headers=marketer_headers,
    )
    assert chat_resp.status_code == 200, chat_resp.text
    proposal = chat_resp.json()["staged_proposal"]
    assert proposal is not None
    assert proposal["status"] == "PENDING"
    assert proposal["actions"][0]["tool_name"] == "log_daily_metrics"
    assert proposal["actions"][0]["params"]["cost"] == 500_000.0
    assert proposal["actions"][0]["params"]["revenue"] == 2_400_000.0
    assert proposal["actions"][0]["params"]["clicks"] == 25
    assert proposal["actions"][0]["params"]["conversions"] == 6

    prop_id = proposal["id"]

    # 2. Người dùng bấm [Thực thi]
    exec_resp = client.post(
        f"/api/v1/ai/proposals/{prop_id}/execute",
        json={},
        headers=marketer_headers,
    )
    assert exec_resp.status_code == 200, exec_resp.text
    exec_data = exec_resp.json()
    assert exec_data["status"] == "EXECUTED"
    assert exec_data["can_undo"] is True
    assert exec_data["executed_result"]["metrics_logged"] == 1

    # 3. Người dùng bấm [Hoàn tác (Undo)] -> xóa sạch bản ghi vừa tạo
    undo_resp = client.post(
        f"/api/v1/ai/proposals/{prop_id}/undo",
        headers=marketer_headers,
    )
    assert undo_resp.status_code == 200, undo_resp.text
    undo_data = undo_resp.json()
    assert undo_data["status"] == "ROLLED_BACK"
    assert undo_data["can_undo"] is False


def test_deep_workspace_intervention_and_vps_awareness(client: TestClient, marketer_headers: dict):
    """Kiểm thử khả năng tự nhận thức tài nguyên VPS & can thiệp sâu (Upsert Product + Undo)."""
    # 1. Hỏi trạng thái RAM VPS & OpenCode
    vps_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "facebook",
            "message": "Kiểm tra máy chủ VPS đang dùng bao nhiêu RAM và trạng thái OpenCode CLI",
            "canvas": {"title": "", "body": "", "cta": ""},
        },
        headers=marketer_headers,
    )
    assert vps_resp.status_code == 200, vps_resp.text
    vps_data = vps_resp.json()
    assert "RAM" in vps_data["reply"]
    assert any("Toàn cảnh Dự án & VPS" in c for c in vps_data["context_used"])

    # 2. Ra lệnh thêm sản phẩm mới vào dự án
    prod_resp = client.post(
        "/api/v1/ai/chat",
        json={
            "channel_code": "facebook",
            "message": "Thêm sản phẩm mới vào dự án với USP bảo hành 24 tháng 1 đổi 1",
            "canvas": {"title": "", "body": "", "cta": ""},
            "context_data": {
                "product_name": "Máy lọc không khí Ion Pro",
                "product_usp": "Lọc bụi mịn PM2.5 99.97%, bảo hành 24 tháng 1 đổi 1",
            },
            "context_flags": {"enable_project_control": True},
        },
        headers=marketer_headers,
    )
    assert prod_resp.status_code == 200, prod_resp.text
    prop = prod_resp.json()["staged_proposal"]
    assert prop is not None
    assert prop["actions"][0]["tool_name"] == "upsert_product"

    # Thực thi & Hoàn tác
    exec_r = client.post(f"/api/v1/ai/proposals/{prop['id']}/execute", json={}, headers=marketer_headers)
    assert exec_r.status_code == 200
    assert exec_r.json()["executed_result"]["products_upserted"] == 1

    undo_r = client.post(f"/api/v1/ai/proposals/{prop['id']}/undo", headers=marketer_headers)
    assert undo_r.status_code == 200
    assert undo_r.json()["status"] == "ROLLED_BACK"

