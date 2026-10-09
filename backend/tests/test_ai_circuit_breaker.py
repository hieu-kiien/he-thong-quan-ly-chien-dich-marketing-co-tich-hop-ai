"""Kiểm thử circuit breaker của lớp AI.

Cốt lõi không phải "đếm đúng" mà là: một provider chết phải bị cắt nhanh, và phải
cho phép hồi phục sau đó. Hai điều đó được kiểm tra bằng cách cấu hình thời gian
rất ngắn rồi thao tác trực tiếp lên đồng hồ, không ngủ thật.
"""

import pytest

from app.services.ai import circuit_breaker as cb_module
from app.services.ai.circuit_breaker import (
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
    CircuitBreaker,
    CircuitOpenError,
)


@pytest.fixture()
def clock(monkeypatch):
    """Điều khiển đồng hồ để kiểm thử điều kiện thời gian mà không ngủ thật."""
    now = [1000.0]
    monkeypatch.setattr(cb_module.time, "monotonic", lambda: now[0])
    return now


@pytest.fixture()
def br():
    # Ngưỡng 2 lỗi, nghỉ 60s: ngắt nhanh nhưng vẫn kiểm chứng được hồi phục.
    return CircuitBreaker(failure_threshold=2, cooldown_seconds=60.0)


# --- Trạng thái đóng (bình thường) ---


def test_allows_when_closed(br):
    br.allow("opencode")  # không ném


def test_one_failure_keeps_closed(br):
    br.record_failure("opencode", "boom")
    assert br.snapshot()["opencode"]["state"] == STATE_CLOSED
    br.allow("opencode")


def test_success_resets_failure_count(br):
    br.record_failure("opencode", "boom")
    br.record_success("opencode", 1.0)
    br.record_failure("opencode", "boom")
    # Chỉ 1 lỗi sau khi đã thành công -> chưa tới ngưỡng 2.
    assert br.snapshot()["opencode"]["state"] == STATE_CLOSED


# --- Ngắt circuit ---


def test_opens_after_threshold_and_blocks(br):
    br.record_failure("opencode", "lỗi 1")
    br.record_failure("opencode", "lỗi 2")
    assert br.snapshot()["opencode"]["state"] == STATE_OPEN
    with pytest.raises(CircuitOpenError):
        br.allow("opencode")


def test_open_blocks_without_network_call(br):
    """Đây là điểm cốt lõi: khi OPEN thì KHÔNG được chạm mạng.

    Nếu lệnh gọi vẫn đi ra, mỗi job hỏng vẫn giữ chân slot AI hết thời gian
    timeout và breaker trở nên vô dụng.
    """
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    for _ in range(5):
        with pytest.raises(CircuitOpenError):
            br.allow("opencode")
    assert br.snapshot()["opencode"]["retry_after_seconds"] > 0


def test_error_message_names_provider(br):
    br.record_failure("gemini", "a")
    br.record_failure("gemini", "b")
    with pytest.raises(CircuitOpenError, match="gemini"):
        br.allow("gemini")


# --- Hồi phục ---


def test_half_open_after_cooldown_then_success_closes(br, clock):
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    assert br.snapshot()["opencode"]["state"] == STATE_OPEN

    clock[0] += 61.0  # vượt thời gian nghỉ

    br.allow("opencode")  # được qua để dò
    assert br.snapshot()["opencode"]["state"] == STATE_HALF_OPEN

    br.record_success("opencode", 2.0)
    assert br.snapshot()["opencode"]["state"] == STATE_CLOSED


def test_still_open_before_cooldown_elapses(br, clock):
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    clock[0] += 30.0  # chưa đủ 60s
    with pytest.raises(CircuitOpenError):
        br.allow("opencode")


def test_only_one_probe_allowed_in_half_open(br, clock):
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    clock[0] += 61.0

    br.allow("opencode")  # lần dò đầu
    with pytest.raises(CircuitOpenError):
        br.allow("opencode")  # lần thứ hai phải bị chặn


def test_failed_probe_reopens_and_resets_cooldown(br, clock):
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    clock[0] += 61.0

    br.allow("opencode")
    br.record_failure("opencode", "vẫn lỗi")
    snap = br.snapshot()["opencode"]
    assert snap["state"] == STATE_OPEN
    # Phải lại đủ thời gian nghỉ trước lần dò kế tiếp.
    assert snap["retry_after_seconds"] > 0
    with pytest.raises(CircuitOpenError):
        br.allow("opencode")


# --- Báo cáo và điều khiển ---


def test_snapshot_tracks_counts_and_latency(br):
    br.record_success("opencode", 1.0)
    br.record_success("opencode", 3.0)
    br.record_failure("opencode", "x")
    snap = br.snapshot()["opencode"]
    assert snap["total_ok"] == 2
    assert snap["total_fail"] == 1
    assert snap["avg_latency_seconds"] == 2.0


def test_reset_clears_single_provider(br):
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    br.reset("opencode")
    br.allow("opencode")  # không còn ném


def test_providers_are_isolated(br):
    br.record_failure("opencode", "a")
    br.record_failure("opencode", "b")
    assert br.snapshot()["opencode"]["state"] == STATE_OPEN
    # Provider khác không bị ảnh hưởng.
    br.allow("gemini")
    assert br.snapshot()["gemini"]["state"] == STATE_CLOSED


def test_blank_provider_is_ignored(br):
    br.allow("")
    br.record_failure("", "x")
    br.record_success("")


def test_threshold_floor_is_one():
    # Ngưỡng 0 hoặc âm không được khiến breaker ngắt ngay lập tức.
    assert CircuitBreaker(failure_threshold=0).failure_threshold == 1
    assert CircuitBreaker(failure_threshold=-5).failure_threshold == 1