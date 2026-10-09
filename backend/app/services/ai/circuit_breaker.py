"""Circuit breaker cho lớp gọi AI provider.

Bài học lấy từ sự cố triển khai thật: khi provider chậm hoặc lỗi, `_call_provider_with_retry`
cứ thử lại `AI_MAX_RETRIES` lần với `AI_TIMEOUT_SECONDS` mỗi lần. Với provider thật
(OpenCode Zen) một lần gọi mất 100 giây, nên một job hỏng có thể giữ slot AI trong
hàng đợi hàng phút rồi mới rơi xuống fallback. Người dùng khác xếp sau chịu giật
theo, trong khi thực ra provider đã chết.

Circuit breaker cắt ngắn điều đó: sau N lần liên tiếp thất bại, breaker `OPEN`
và mọi lệnh gọi tiếp theo trả về ngay lỗi mà không chạm mạng. Sau thời gian nghỉ
(`COOLDOWN_SECONDS`) breaker chuyển sang `HALF_OPEN`, cho đúng một lần thử để dò
xem provider đã phục hồi chưa.

Ba trạng thái:
- CLOSED    — bình thường, đo lỗi và độ trễ.
- OPEN      — đã ngắt, mọi lệnh gọi bị từ chối ngay lập tức (fail fast).
- HALF_OPEN — đang dò; chỉ cho một lần thử đi qua. Thành công thì đóng lại,
              thất bại thì mở lại và đặt lại mốc nghỉ.

KHÔNG dùng thư viện ngoài, giống `core/security.py`. Trạng thái nằm trong bộ nhớ
tiến trình: đây là lớp phòng thủ bổ sung. Với nhiều worker Uvicorn thì mỗi worker
một bộ đếm — chấp nhận được, vì mục tiêu là bảo vệ một worker khỏi kẹt.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Deque, Dict, Optional

logger = logging.getLogger(__name__)

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"

# Ngưỡng đóng breaker: số lỗi liên tiếp cho một provider trước khi ngắt.
DEFAULT_FAILURE_THRESHOLD = 3
# Sau khi ngắt, chờ bao lâu mới cho phép một lần thử dò lại.
DEFAULT_COOLDOWN_SECONDS = 60.0
# Giữ bao nhiêu mẫu độ trễ gần nhất để báo cáo.
LATENCY_SAMPLES = 20


class CircuitOpenError(RuntimeError):
    """Ném ra khi breaker đang OPEN: gọi lại sẽ không giúp ích.

    Loại riêng để caller phân biệt "provider đang chết, đừng thử lại" với lỗi
    xác thực hay lỗi cấu hình — hai loại sau cần người vận hành xem ngay.
    """


class _BreakerState:
    """Trạng thái của một provider. Chỉ được đụng tới qua `CircuitBreaker`."""

    __slots__ = ("state", "failures", "opened_at", "probe_in_flight", "latencies", "total_ok", "total_fail")

    def __init__(self) -> None:
        self.state = STATE_CLOSED
        self.failures = 0
        self.opened_at = 0.0
        # Cờ cho biết một lần dò HALF_OPEN đang bay; chặn lệnh thứ hai để
        # tránh dồn request vào provider đang hồi phục.
        self.probe_in_flight = False
        self.latencies: Deque[float] = deque(maxlen=LATENCY_SAMPLES)
        self.total_ok = 0
        self.total_fail = 0


class CircuitBreaker:
    """Theo dõi độ khoẻ từng provider và ngắt khi chúng hỏng."""

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_seconds = max(1.0, float(cooldown_seconds))
        self._breakers: Dict[str, _BreakerState] = {}
        self._lock = threading.Lock()

    def _get(self, provider: str) -> _BreakerState:
        state = self._breakers.get(provider)
        if state is None:
            state = _BreakerState()
            self._breakers[provider] = state
        return state

    def _maybe_half_open(self, state: _BreakerState, now: float) -> None:
        """Chuyển OPEN -> HALF_OPEN khi đã qua thời gian nghỉ."""
        if state.state == STATE_OPEN and (now - state.opened_at) >= self.cooldown_seconds:
            state.state = STATE_HALF_OPEN
            state.probe_in_flight = False
            logger.info("AI circuit breaker: thu provider, cho phep mot lan do lai.")

    def allow(self, provider: str) -> None:
        """Nếu lệnh gọi tới `provider` không được phép thì ném `CircuitOpenError`."""
        if not provider:
            return
        now = time.monotonic()
        with self._lock:
            state = self._get(provider)
            self._maybe_half_open(state, now)
            if state.state == STATE_OPEN:
                wait = max(0.0, self.cooldown_seconds - (now - state.opened_at))
                raise CircuitOpenError(
                    f"Nhà cung cấp AI '{provider}' đang tạm ngắt sau nhiều lỗi. "
                    f"Thử lại sau {wait:.0f} giây."
                )
            if state.state == STATE_HALF_OPEN:
                if state.probe_in_flight:
                    raise CircuitOpenError(
                        f"Nhà cung cấp AI '{provider}' đang được thử lại, vui lòng chờ."
                    )
                state.probe_in_flight = True

    def record_success(self, provider: str, latency_seconds: float = 0.0) -> None:
        """Ghi nhận lệnh gọi thành công; đóng lại breaker nếu đang mở."""
        if not provider:
            return
        with self._lock:
            state = self._get(provider)
            state.total_ok += 1
            state.failures = 0
            if latency_seconds > 0:
                state.latencies.append(latency_seconds)
            if state.state != STATE_CLOSED:
                logger.info("AI circuit breaker: provider '%s' đã phục hồi.", provider)
            state.state = STATE_CLOSED
            state.probe_in_flight = False

    def record_failure(self, provider: str, error: Optional[str] = None) -> None:
        """Ghi nhận lỗi; ngắt breaker khi đạt ngưỡng."""
        if not provider:
            return
        with self._lock:
            state = self._get(provider)
            state.total_fail += 1
            state.failures += 1
            state.probe_in_flight = False
            if state.failures >= self.failure_threshold:
                if state.state != STATE_OPEN:
                    logger.warning(
                        "AI circuit breaker: ngắt provider '%s' sau %d lỗi liên tiếp. Lý do cuối: %s",
                        provider, state.failures, error or "không rõ",
                    )
                state.state = STATE_OPEN
                state.opened_at = time.monotonic()
            elif state.state == STATE_HALF_OPEN:
                # Lần dò thất bại: quay lại OPEN, đặt lại mốc nghỉ.
                state.state = STATE_OPEN
                state.opened_at = time.monotonic()

    def reset(self, provider: Optional[str] = None) -> None:
        """Xoá trạng thái để thử lại ngay (dùng khi đổi cấu hình provider)."""
        with self._lock:
            if provider:
                self._breakers.pop(provider, None)
            else:
                self._breakers.clear()

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        """Báo cáo trạng thái cho endpoint quản trị."""
        now = time.monotonic()
        out: Dict[str, Dict[str, object]] = {}
        with self._lock:
            for provider, state in self._breakers.items():
                self._maybe_half_open(state, now)
                avg = (sum(state.latencies) / len(state.latencies)) if state.latencies else None
                out[provider] = {
                    "state": state.state,
                    "consecutive_failures": state.failures,
                    "total_ok": state.total_ok,
                    "total_fail": state.total_fail,
                    "avg_latency_seconds": round(avg, 2) if avg is not None else None,
                    "retry_after_seconds": (
                        round(max(0.0, self.cooldown_seconds - (now - state.opened_at)), 1)
                        if state.state == STATE_OPEN
                        else None
                    ),
                }
        return out


# Một breaker dùng chung cho cả tiến trình.
breaker = CircuitBreaker()