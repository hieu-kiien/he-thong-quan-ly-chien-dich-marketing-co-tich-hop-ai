"""Enterprise Upgrade Test Suite:
Kiểm thử toàn diện các tính năng nâng cấp cấp doanh nghiệp:
1. Funnel-Stage Dynamic AI Doctor (ToFU / MoFU / BoFU) + Learning Phase Protection
2. Time-Based Budget Pacing & Time-Series Creative Fatigue Detection
3. 1,000-Campaign Command Grid (page_size=200, grid-summary, bulk-action, portfolio-triage, winning-patterns, seed-angle-matrix)
4. Bulk Content Review & Semantic Compliance Batch Auto-Fix
5. Smart CSV Metrics Ingestion (auto-detect Facebook/TikTok/Google Ads, currency/date normalization, anomaly preview, idempotent commit)
6. Creative Angle × Hook Matrix (3x3) & Pre-Launch Focus Group Critic
"""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


def test_tofu_awareness_campaign_ai_doctor_healthy_without_revenue(client: TestClient, manager_headers: dict):
    """Chiến dịch ToFU (Brand Awareness) có revenue=0 nhưng CTR & CPM tốt phải đạt HEALTHY, không bị phạt ROAS."""
    today = datetime.now(timezone.utc).date()
    start_str = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=25)).strftime("%Y-%m-%d")

    create_res = client.post(
        "/api/v1/campaigns",
        headers=manager_headers,
        json={
            "product_id": 1,
            "name": "Chiến dịch Nhận diện Thương hiệu Mùa Hè",
            "objective": "Tăng nhận diện thương hiệu và độ phủ sóng (Reach & Impressions)",
            "funnel_stage": "ToFU",
            "audience": "Gen Z & Millennials toàn quốc",
            "start_date": start_str,
            "end_date": end_str,
            "budget": 30000000.0,
            "status": "ACTIVE",
            "tags": ["awareness", "summer"],
        },
    )
    assert create_res.status_code == 201, create_res.text
    camp = create_res.json()
    camp_id = camp["id"]
    assert camp["funnel_stage"] == "ToFU"
    assert camp["campaign_code"].startswith("CMP-")
    assert "awareness" in camp["tags"]

    # Nạp metric: 150,000 views, 3,200 clicks (CTR ~2.13%), 0 conversions, 0 revenue, cost 5,000,000 VND (CPM ~33,333đ)
    metric_res = client.post(
        f"/api/v1/campaigns/{camp_id}/metrics",
        headers=manager_headers,
        json={
            "campaign_id": camp_id,
            "channel_id": 1,
            "metric_date": today.strftime("%Y-%m-%d"),
            "views": 150000,
            "clicks": 3200,
            "conversions": 0,
            "cost": 5000000.0,
            "revenue": 0.0,
        },
    )
    assert metric_res.status_code == 201, metric_res.text

    doc_res = client.post(f"/api/v1/campaigns/{camp_id}/ai-doctor", headers=manager_headers)
    assert doc_res.status_code == 200, doc_res.text
    doc = doc_res.json()
    assert doc["funnel_stage"] == "ToFU"
    assert doc["health_score"] >= 80
    assert doc["health_status"] == "HEALTHY"
    assert doc["overall_status"] == "HEALTHY"
    assert not any("roas" in str(b).lower() for b in doc["bottlenecks"])


def test_budget_pacing_and_creative_fatigue_detection(client: TestClient, manager_headers: dict):
    """Kiểm tra phát hiện suy giảm CTR theo chuỗi thời gian (Creative Fatigue) và tốc độ đốt ngân sách (Budget Pacing)."""
    today = datetime.now(timezone.utc).date()
    start_str = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=10)).strftime("%Y-%m-%d")

    create_res = client.post(
        "/api/v1/campaigns",
        headers=manager_headers,
        json={
            "product_id": 1,
            "name": "Chiến dịch Chuyển đổi BoFU Flash Sale",
            "objective": "Tối ưu doanh số và ROAS",
            "funnel_stage": "BoFU",
            "audience": "Khách hàng đã xem giỏ hàng",
            "start_date": start_str,
            "end_date": end_str,
            "budget": 20000000.0,
            "status": "ACTIVE",
        },
    )
    assert create_res.status_code == 201
    camp_id = create_res.json()["id"]

    # 3 ngày đầu CTR cao (500 clicks / 10,000 views = 5.0%), 3 ngày sau CTR tụt mạnh (150 clicks / 10,000 views = 1.5%)
    for i in range(6):
        d_str = (today - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        is_early = i < 3
        r = client.post(
            f"/api/v1/campaigns/{camp_id}/metrics",
            headers=manager_headers,
            json={
                "campaign_id": camp_id,
                "channel_id": 1,
                "metric_date": d_str,
                "views": 10000,
                "clicks": 500 if is_early else 150,
                "conversions": 25 if is_early else 8,
                "cost": 3000000.0,
                "revenue": 9500000.0 if is_early else 4500000.0,
            },
        )
        assert r.status_code == 201

    doc_res = client.post(f"/api/v1/campaigns/{camp_id}/ai-doctor", headers=manager_headers)
    assert doc_res.status_code == 200
    doc = doc_res.json()
    assert doc["fatigue_detected"] is True
    assert doc["pacing_status"] in ("OVER_PACING", "ON_TRACK", "EXHAUSTED")
    assert any("bão hòa" in str(b).lower() or "fatigue" in str(b).lower() for b in doc["bottlenecks"])


def test_campaign_grid_summary_bulk_action_and_triage(client: TestClient, manager_headers: dict):
    """Kiểm tra bộ API quản lý 1,000 chiến dịch: page_size=200, grid-summary, bulk-action, portfolio-triage, winning-patterns, seed-angle-matrix."""
    list_res = client.get("/api/v1/campaigns?page=1&page_size=200", headers=manager_headers)
    assert list_res.status_code == 200
    page_data = list_res.json()
    assert page_data["page_size"] == 200
    assert len(page_data["items"]) >= 1
    first_camp = page_data["items"][0]
    assert "metrics_summary" in first_camp
    assert "roas" in first_camp["metrics_summary"]

    grid_res = client.get("/api/v1/campaigns/grid-summary", headers=manager_headers)
    assert grid_res.status_code == 200
    grid = grid_res.json()
    assert grid["total_campaigns"] >= 1
    assert "overall_roas" in grid

    camp_id = first_camp["id"]
    bulk_res = client.post(
        "/api/v1/campaigns/bulk-action",
        headers=manager_headers,
        json={
            "campaign_ids": [camp_id],
            "action": "ADD_TAG",
            "tag": "priority-q4",
        },
    )
    assert bulk_res.status_code == 200
    assert bulk_res.json()["updated_count"] == 1

    triage_res = client.get("/api/v1/campaigns/portfolio-triage", headers=manager_headers)
    assert triage_res.status_code == 200
    triage = triage_res.json()
    assert "total_scanned" in triage
    assert "anomalies" in triage

    win_res = client.get("/api/v1/campaigns/winning-patterns", headers=manager_headers)
    assert win_res.status_code == 200
    assert "patterns" in win_res.json()

    seed_res = client.post(
        f"/api/v1/campaigns/{camp_id}/seed-angle-matrix",
        headers=manager_headers,
        json={"channel_code": "facebook", "persist_to_db": True},
    )
    assert seed_res.status_code == 201, seed_res.text
    seed_data = seed_res.json()
    assert seed_data["created_count"] == 9
    assert len(seed_data["content_ids"]) == 9


def test_content_bulk_review_and_batch_auto_fix(client: TestClient, manager_headers: dict, marketer_headers: dict):
    """Kiểm tra tự động sửa lỗi vi phạm từ khóa cấm (Batch Auto-Fix) và duyệt hàng loạt (Bulk Review)."""
    create_res = client.post(
        "/api/v1/contents",
        headers=marketer_headers,
        json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Cam kết 100% khỏi hoàn toàn chỉ sau 1 ngày",
            "body": "Sản phẩm trị dứt điểm mọi vấn đề, cam kết 100% hiệu quả tức thì không hoàn tiền.",
            "cta": "Mua ngay",
            "creative_angle": "PAIN_POINT",
            "hook_variant": "HOOK_1",
        },
    )
    assert create_res.status_code == 201, create_res.text
    content = create_res.json()
    cid = content["id"]
    assert content["utm_params"] is not None
    assert "utm_source=" in content["utm_params"]

    fix_res = client.post(
        "/api/v1/contents/batch-auto-fix",
        headers=marketer_headers,
        json={"content_ids": [cid]},
    )
    assert fix_res.status_code == 200, fix_res.text
    fix_data = fix_res.json()
    assert fix_data["processed_count"] == 1
    assert fix_data["items"][0]["new_score"] >= fix_data["items"][0]["original_score"]
    assert fix_data["items"][0]["can_submit"] is True

    sub_res = client.post(
        "/api/v1/contents/bulk-review",
        headers=marketer_headers,
        json={"content_ids": [cid], "action": "SUBMIT"},
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["processed_count"] == 1

    app_res = client.post(
        "/api/v1/contents/bulk-review",
        headers=manager_headers,
        json={"content_ids": [cid], "action": "APPROVE", "reason": "Đạt chuẩn sau khi AI Auto-Fix"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["processed_count"] == 1


def test_smart_csv_importer_analyze_and_commit(client: TestClient, manager_headers: dict):
    """Kiểm tra Smart CSV Importer: nhận diện Facebook Ads, chuẩn hóa tiền Việt Nam và nạp idempotent."""
    csv_text = (
        "Reporting starts,Campaign name,Platform,Impressions,Link clicks,Results,Amount spent (VND),Purchases conversion value\n"
        "15/10/2026,Chiến dịch Tết 2026,facebook,45000,1850,95,4.500.000 đ,18.900.000 đ\n"
    )
    analyze_res = client.post(
        "/api/v1/metrics/smart-import/analyze",
        headers=manager_headers,
        json={"csv_text": csv_text, "default_campaign_id": 1},
    )
    assert analyze_res.status_code == 200, analyze_res.text
    analysis = analyze_res.json()
    assert analysis["detected_platform"] == "Facebook Ads"
    assert analysis["total_rows"] == 1
    assert analysis["valid_rows"] == 1
    row0 = analysis["preview_rows"][0]
    assert row0["cost"] == 4500000.0
    assert row0["revenue"] == 18900000.0
    assert row0["metric_date"] == "2026-10-15"

    commit_res = client.post(
        "/api/v1/metrics/smart-import/commit",
        headers=manager_headers,
        json={
            "default_campaign_id": 1,
            "replace_seed_data": False,
            "rows": [
                {
                    "campaign_id": 1,
                    "channel_code": "facebook",
                    "metric_date": "2026-10-15",
                    "views": 45000,
                    "clicks": 1850,
                    "conversions": 95,
                    "cost": 4500000.0,
                    "revenue": 18900000.0,
                }
            ],
        },
    )
    assert commit_res.status_code == 200, commit_res.text
    committed = commit_res.json()
    assert committed["imported_rows"] + committed["updated_rows"] == 1
    assert 1 in committed["affected_campaign_ids"]


def test_ai_angle_matrix_and_prelaunch_critic(client: TestClient, manager_headers: dict):
    """Kiểm tra 2 động cơ AI mới: Ma trận 4x3 Angle × Hook và Hội đồng 4 Persona Pre-Launch Critic."""
    matrix_res = client.post(
        "/api/v1/ai/angle-matrix",
        headers=manager_headers,
        json={
            "campaign_id": 1,
            "channel_code": "facebook",
            "funnel_stage": "BoFU",
            "brief": "Tăng tỷ lệ chốt đơn cuối tuần với ưu đãi miễn phí vận chuyển",
        },
    )
    assert matrix_res.status_code == 200, matrix_res.text
    matrix_data = matrix_res.json()
    assert len(matrix_data["variants"]) == 12
    angles = {v["creative_angle"] for v in matrix_data["variants"]}
    assert angles == {"PAIN_POINT", "SOCIAL_PROOF", "MYTH_BUSTER", "OFFER_FOMO"}

    critic_res = client.post(
        "/api/v1/ai/prelaunch-critic",
        headers=manager_headers,
        json={
            "campaign_id": 1,
            "title": "Ưu đãi 30% cho 50 đơn hàng đầu tiên hôm nay — Đổi trả miễn phí 30 ngày",
            "body": (
                "Hơn 12.500 khách hàng doanh nghiệp đã tiết kiệm 45% thời gian vận hành chiến dịch. "
                "Đăng ký ngay hôm nay để nhận ưu đãi 30% và bảo hành hoàn tiền trong 30 ngày."
            ),
            "cta": "Nhận ưu đãi 30% ngay",
            "channel_code": "facebook",
            "funnel_stage": "BoFU",
        },
    )
    assert critic_res.status_code == 200, critic_res.text
    critic_data = critic_res.json()
    assert 0 <= critic_data["overall_readiness_score"] <= 100
    assert len(critic_data["personas"]) == 4
    assert len(critic_data["persona_critiques"]) == 3
    assert critic_data["launch_recommendation"] in ("READY_TO_LAUNCH", "NEEDS_MINOR_TUNING", "HIGH_RISK_REWRITE")
