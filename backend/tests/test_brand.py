"""Test hồ sơ thương hiệu & từ cấm (CONTRACT §4, §10)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_and_update_brand_profile(
    client: TestClient, manager_headers: dict[str, str], marketer1_headers: dict[str, str]
):
    # Marketer can view brand profile
    resp = client.get("/api/v1/brand-profile", headers=marketer1_headers)
    assert resp.status_code == 200

    # Marketer cannot update brand profile -> 403
    resp_bad = client.put(
        "/api/v1/brand-profile",
        headers=marketer1_headers,
        json={"brand_name": "Tên Giả Mạo"},
    )
    assert resp_bad.status_code == 403

    # Manager updates brand profile
    payload = {
        "brand_name": "Cà phê An Nam",
        "description": "Chuỗi xưởng rang",
        "tone_of_voice": "Chân thành, ấm áp",
        "target_audience": "Dân văn phòng",
        "guidelines": "Rang mộc 100%",
        "banned_keywords": [
            {"keyword": "Cam Kết 100%", "note": "Không cam kết tuyệt đối"},
            {"keyword": "rẻ nhất", "note": "Không tuyên bố rẻ nhất"},
        ],
    }
    resp_ok = client.put("/api/v1/brand-profile", headers=manager_headers, json=payload)
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["brand_name"] == "Cà phê An Nam"
    assert len(data["banned_keywords"]) == 2
    # Check normalized keyword stored lowercase
    kws = [k["keyword"] for k in data["banned_keywords"]]
    assert "cam kết 100%" in kws
