"""Kiểm thử toàn diện 3 trụ cột Thương mại hóa SaaS & Bộ công cụ Marketing Đặc thù Việt Nam:
1. Gói cước SaaS (FREE / PRO / AGENCY), VietQR Napas 247 & SePay Webhook mở khóa Quota.
2. Bảo mật Khóa POS Webhook (webhook_key) & Chế độ Production Sạch (clean_demo_mode).
3. Bộ tính Điểm Hòa Vốn (Break-Even ROAS) & Lợi Nhuận Ròng TikTok Shop / Shopee (trừ phí sàn, KOC, bom COD).
4. Phễu Chốt Đơn Tin Nhắn (Zalo OA / ZNS & Messenger 24h Care) + 1-Click Chốt Đơn Sang POS.
5. Kịch bản Mùa Vụ & Khung Giờ Vàng Mega Sale Việt Nam (Ngày Đôi 11/11, Lương về 15/25, Tết).
"""


def test_saas_billing_vietqr_and_sepay_webhook_unlocks_quota(
    client, marketer_headers, workspace_alpha
):
    ws_id = workspace_alpha.id

    # 1. Mặc định Workspace ở gói FREE
    plan_res = client.get(
        f"/api/v1/ad-accounts/billing-plan?workspace_id={ws_id}",
        headers=marketer_headers,
    )
    assert plan_res.status_code == 200
    data = plan_res.json()
    assert data["plan_tier"] == "FREE"
    assert "img.vietqr.io" in data["vietqr"]["pro_qr_url"]

    # 2. Giả lập ngân hàng MBBank / SePay bắn Webhook thanh toán 499.000đ cho gói PRO
    wh_res = client.post(
        "/api/v1/ad-accounts/billing-webhook",
        json={
            "content": f"CHUYEN KHOAN MARKETFLOW WS{ws_id} PRO",
            "transferAmount": 499000,
            "referenceCode": "MBVCB.99887766",
        },
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["upgraded_to"] == "PRO"

    # 3. Kiểm tra hạn mức Quota đã tự động mở khóa lên trần PRO (150 AI jobs/ngày, 50 chiến dịch)
    after_res = client.get(
        f"/api/v1/ad-accounts/billing-plan?workspace_id={ws_id}",
        headers=marketer_headers,
    )
    assert after_res.status_code == 200
    after_data = after_res.json()
    assert after_data["plan_tier"] == "PRO"
    limits_by_code = {
        item["limit_code"]: item["limit"]
        for item in after_data["quota_snapshot"]["limits"]
    }
    assert limits_by_code["ai_jobs_per_day"] >= 150
    assert limits_by_code["campaigns"] >= 50


def test_clean_workspace_mode_and_pos_webhook_key_security(
    client, marketer_headers, workspace_alpha, rich_metrics_campaign
):
    ws_id = workspace_alpha.id
    camp_id = rich_metrics_campaign["id"] if isinstance(rich_metrics_campaign, dict) else rich_metrics_campaign.id

    # Bật Chế độ Production Sạch (xóa dữ liệu mẫu)
    clean_res = client.post(
        "/api/v1/ad-accounts/clean-workspace",
        json={"workspace_id": ws_id, "mode": "purge_demo"},
        headers=marketer_headers,
    )
    assert clean_res.status_code == 200
    assert clean_res.json()["clean_demo_mode"] is True

    # Khi ở chế độ Production Sạch, gọi external-webhook KHÔNG có webhook_key phải bị chặn 401
    unauth_wh = client.post(
        "/api/v1/ad-accounts/external-webhook",
        json={
            "workspace_id": ws_id,
            "campaign_id": camp_id,
            "order_count": 1,
            "order_value": 500000,
        },
    )
    assert unauth_wh.status_code == 401

    # Truyền đúng webhook_key của workspace thì ghi nhận đơn thành công 200
    valid_wh = client.post(
        "/api/v1/ad-accounts/external-webhook",
        headers={"X-MarketFlow-Webhook-Key": f"mf_pos_live_ws{ws_id}_2026"},
        json={
            "workspace_id": ws_id,
            "campaign_id": camp_id,
            "order_count": 2,
            "order_value": 1200000,
        },
    )
    assert valid_wh.status_code == 200
    assert valid_wh.json()["webhook_verified"] is True
    assert valid_wh.json()["added_orders"] == 2


def test_vn_ecommerce_pnl_and_zalo_lead_crm_and_mega_sale_blueprint(
    client, marketer_headers, workspace_alpha, rich_metrics_campaign
):
    ws_id = workspace_alpha.id
    camp_id = rich_metrics_campaign["id"] if isinstance(rich_metrics_campaign, dict) else rich_metrics_campaign.id

    # 1. Tính Điểm Hòa Vốn (Break-Even ROAS) sàn TikTok Shop / Shopee
    pnl_res = client.post(
        "/api/v1/ad-accounts/vn-ecommerce-pnl",
        headers=marketer_headers,
        json={
            "campaign_id": camp_id,
            "selling_price": 400000,
            "cogs_per_unit": 120000,
            "platform_fee_pct": 12.5,
            "affiliate_commission_pct": 10.0,
            "return_rate_pct": 15.0,
            "return_shipping_fee": 30000,
            "current_ad_spend": 10000000,
            "current_orders": 80,
            "current_revenue": 32000000,
        },
    )
    assert pnl_res.status_code == 200
    pnl = pnl_res.json()
    assert pnl["unit_economics"]["break_even_roas"] > 1.5
    assert pnl["unit_economics"]["max_allowable_cpa"] > 0
    assert "recommendations" in pnl

    # 2. Tạo Lead từ Quảng cáo Tin nhắn -> Bắn Zalo ZNS -> 1-Click Chốt Đơn Sang POS
    lead_res = client.post(
        "/api/v1/ad-accounts/vn-leads",
        headers=marketer_headers,
        json={
            "workspace_id": ws_id,
            "campaign_id": camp_id,
            "customer_name": "Chị Hoàng Mai (Q.3, TP.HCM)",
            "phone": "0912345678",
            "source_channel": "ZALO_OA",
            "lead_stage": "SILENT_24H",
            "product_interest": "Combo Mỹ Phẩm Chuyên Sâu",
            "estimated_value": 950000,
        },
    )
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["id"]

    zns_res = client.post(
        f"/api/v1/ad-accounts/vn-leads/{lead_id}/send-zns",
        headers=marketer_headers,
        json={"template_type": "REMIND_24H_META"},
    )
    assert zns_res.status_code == 200
    assert zns_res.json()["lead"]["zns_sent_count"] == 1

    close_res = client.post(
        f"/api/v1/ad-accounts/vn-leads/{lead_id}/close-order",
        headers=marketer_headers,
    )
    assert close_res.status_code == 200
    assert close_res.json()["lead"]["lead_stage"] == "CLOSED_POS"
    assert close_res.json()["added_revenue"] == 950000

    # 3. Áp dụng Kịch bản Mùa Vụ Mega Sale Ngày Đôi (11/11 - 12/12)
    bp_res = client.post(
        "/api/v1/ad-accounts/vn-mega-sale-blueprint",
        headers=marketer_headers,
        json={
            "campaign_id": camp_id,
            "blueprint_code": "DOUBLE_DAY",
        },
    )
    assert bp_res.status_code == 200
    assert bp_res.json()["created_tasks_count"] >= 3


def test_product_crud_and_campaign_custom_product_and_clean_reads(
    client, manager_headers, workspace_alpha
):
    ws_id = workspace_alpha.id

    # 1. CRUD Sản phẩm & USP
    create_prod = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={
            "name": "Serum Vitamin C 20% Kiên Hiếu",
            "description": "Tinh chất dưỡng sáng mờ thâm",
            "usp": "Công nghệ bọc Liposome thẩm thấu gấp 3 lần, không châm chích",
        },
    )
    assert create_prod.status_code == 201
    prod_data = create_prod.json()
    prod_id = prod_data["id"]
    assert prod_data["name"] == "Serum Vitamin C 20% Kiên Hiếu"
    assert "Liposome" in prod_data["usp"]

    upd_prod = client.put(
        f"/api/v1/products/{prod_id}",
        headers=manager_headers,
        json={"usp": "Bọc Liposome thế hệ mới + Niacinamide 5%"},
    )
    assert upd_prod.status_code == 200
    assert upd_prod.json()["usp"] == "Bọc Liposome thế hệ mới + Niacinamide 5%"

    # 2. Tạo chiến dịch truyền trực tiếp product_name + product_usp mới
    camp_res = client.post(
        "/api/v1/campaigns",
        headers=manager_headers,
        json={
            "workspace_id": ws_id,
            "product_name": "Kem Chống Nắng Phổ Rộng SPF50+",
            "product_usp": "Kiềm dầu 12h, không nâng tông trắng bệch",
            "name": "Chiến dịch Ra mắt Kem Chống Nắng Mùa Hè",
            "objective": "Tối ưu đơn hàng chuyển đổi",
            "audience": "Nữ 20-35 tuổi da dầu mụn",
            "start_date": "2026-10-01",
            "end_date": "2026-11-01",
            "budget": 15000000,
        },
    )
    assert camp_res.status_code == 201
    camp_json = camp_res.json()
    camp_id = camp_json["id"]

    # Cập nhật USP sản phẩm ngay từ PUT /campaigns/{id}
    upd_camp = client.put(
        f"/api/v1/campaigns/{camp_id}",
        headers=manager_headers,
        json={
            "product_name": "Kem Chống Nắng Phổ Rộng SPF50+ Pro",
            "product_usp": "Kiềm dầu 14h, kháng nước vượt trội",
        },
    )
    assert upd_camp.status_code == 200

    # Xóa sản phẩm đầu tiên (chưa gắn chiến dịch)
    del_prod = client.delete(f"/api/v1/products/{prod_id}", headers=manager_headers)
    assert del_prod.status_code == 200
    assert del_prod.json()["status"] == "DELETED"

    # 3. Kiểm tra không tự động seed dữ liệu giả khi GET và luôn che mặt nạ access_token dài
    acc_create = client.post(
        "/api/v1/ad-accounts",
        headers=manager_headers,
        json={
            "workspace_id": ws_id,
            "platform": "META_ADS",
            "account_name": "BM Chính Hãng",
            "account_code": "act_9988776655",
            "access_token": "EAABsbCS1iHgBOlongsecretaccesstoken1234567890",
        },
    )
    assert acc_create.status_code == 201
    masked_tok = acc_create.json()["access_token_masked"]
    assert "..." in masked_tok
    assert "longsecretaccesstoken" not in masked_tok
