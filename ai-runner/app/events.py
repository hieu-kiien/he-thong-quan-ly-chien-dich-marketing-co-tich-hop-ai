"""Translate `opencode run --format json` JSONL output into runner NDJSON events
and classify failures into the error codes of CONTRACT §6/§7."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

TOOL_PREFIX = "marketflow_"

AI_RATE_LIMITED = "AI_RATE_LIMITED"
AI_TIMEOUT = "AI_TIMEOUT"
AI_EMPTY_RESPONSE = "AI_EMPTY_RESPONSE"
AI_UNAVAILABLE = "AI_UNAVAILABLE"
AI_ABORTED = "AI_ABORTED"
AI_BUSY = "AI_BUSY"

MESSAGES = {
    AI_RATE_LIMITED: "Dịch vụ AI miễn phí đang bị giới hạn lượt dùng. Vui lòng thử lại sau ít phút.",
    AI_TIMEOUT: "Trợ lý AI phản hồi quá thời gian cho phép. Vui lòng thử lại.",
    AI_EMPTY_RESPONSE: "Trợ lý AI không trả về nội dung. Vui lòng thử lại hoặc diễn đạt lại yêu cầu.",
    AI_UNAVAILABLE: "Không kết nối được tới dịch vụ AI. Vui lòng thử lại sau.",
    AI_ABORTED: "Lượt trả lời đã được dừng theo yêu cầu.",
    AI_BUSY: "Hàng đợi AI đang đầy. Vui lòng thử lại sau ít phút.",
}

_RATE_LIMIT_MARKERS = (
    "freetiererror",
    "free usage limit",
    "free tier",
    "rate limit",
    "rate-limited",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "quota",
    "tokens per minute",
    "input tokens per minute",
    "request too large for model",
)
_MODEL_ERROR_MARKERS = (
    "model not found",
    "modelnotfound",
    "providermodelnotfounderror",
    "unknown model",
    "model is not available",
    "model is unavailable",
    "no longer available",
    "upstream request failed",
    "no such model",
    "model_not_found",
    # opencode 1.19 answers an unknown `-m provider/model` with a generic
    # `UnknownError: Unexpected server error` before producing any output.
    "unexpected server error",
)
_SESSION_MARKERS = ("session not found", "sessionnotfound", "notfounderror: session")


def error_event(code: str, message: str | None = None, detail: str | None = None) -> dict[str, Any]:
    event: dict[str, Any] = {"type": "error", "code": code, "message": message or MESSAGES[code]}
    if detail:
        event["detail"] = detail[:500]
    return event


def is_rate_limited(text: str) -> bool:
    low = text.lower()
    if any(marker in low for marker in _RATE_LIMIT_MARKERS):
        return True
    return '"statuscode": 429' in low or '"statuscode":429' in low or " 429" in low


def is_model_error(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _MODEL_ERROR_MARKERS)


def is_session_error(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _SESSION_MARKERS)


def _short_error(err: Any) -> str:
    """Human-oriented one-liner from an opencode `error` payload (without response headers)."""
    if not isinstance(err, dict):
        return str(err)[:300]
    data = err.get("data") if isinstance(err.get("data"), dict) else {}
    parts = [str(err.get("name") or "Error")]
    if data.get("statusCode"):
        parts.append(f"HTTP {data['statusCode']}")
    if data.get("message"):
        parts.append(str(data["message"]))
    body = data.get("responseBody")
    if isinstance(body, str) and "FreeTierError" in body and "FreeTierError" not in " ".join(parts):
        parts.append("FreeTierError")
    return " | ".join(parts)[:400]


@dataclass
class TurnState:
    """Accumulated state of one opencode process run."""

    session_id: str | None = None
    texts: list[str] = field(default_factory=list)
    part_deltas: dict[str, str] = field(default_factory=dict)
    tools: int = 0
    error_raw: str | None = None
    error_short: str | None = None
    tokens: dict[str, Any] = field(default_factory=dict)

    @property
    def emitted_output(self) -> bool:
        return bool(self.texts) or bool(self.part_deltas) or self.tools > 0

    @property
    def has_text(self) -> bool:
        return any(t.strip() for t in self.texts) or any(d.strip() for d in self.part_deltas.values())


def parse_line(line: str, state: TurnState) -> list[dict[str, Any]]:
    """Parse one stdout line. Returns runner events to forward (may be empty).

    Error events are NOT forwarded here; they are recorded in `state` and the caller
    decides (retry / fallback / final error) once the process has exited.
    """
    line = line.strip()
    if not line or not line.startswith("{"):
        return []
    try:
        event = json.loads(line)
    except ValueError:
        return []
    if not isinstance(event, dict):
        return []

    out: list[dict[str, Any]] = []
    sid = event.get("sessionID")
    if isinstance(sid, str) and sid and state.session_id is None:
        state.session_id = sid
        out.append({"type": "session", "id": sid})

    etype = event.get("type")
    part = event.get("part") if isinstance(event.get("part"), dict) else {}

    if etype == "step_start":
        out.append({"type": "step"})
    elif etype == "text_delta":
        delta = event.get("delta")
        part_id = str(event.get("partID") or "default")
        if isinstance(delta, str) and delta:
            state.part_deltas[part_id] = state.part_deltas.get(part_id, "") + delta
            out.append({"type": "text_delta", "part_id": part_id, "delta": delta})
    elif etype == "text":
        text = part.get("text")
        part_id = str(part.get("id") or "")
        if isinstance(text, str) and text.strip():
            state.texts.append(text)
            if part_id:
                state.part_deltas.pop(part_id, None)
            out.append({"type": "text", "text": text})
    elif etype == "tool_use":
        tool_state = part.get("state") if isinstance(part.get("state"), dict) else {}
        status = tool_state.get("status")
        name = str(part.get("tool") or "")
        name = name.removeprefix(TOOL_PREFIX)
        ok = status == "completed"
        if status in ("completed", "error"):
            state.tools += 1
            out.append(
                {
                    "type": "tool",
                    "id": part.get("callID") or part.get("id"),
                    "name": name,
                    "builtin": not str(part.get("tool") or "").startswith(TOOL_PREFIX),
                    "status": "done" if ok else "error",
                    "input": tool_state.get("input") or {},
                    "output": tool_state.get("output") if ok else tool_state.get("error"),
                }
            )
    elif etype == "step_finish":
        tokens = part.get("tokens")
        if isinstance(tokens, dict):
            for key in ("total", "input", "output", "reasoning"):
                value = tokens.get(key)
                if isinstance(value, (int, float)):
                    state.tokens[key] = state.tokens.get(key, 0) + value
    elif etype == "error":
        err = event.get("error")
        state.error_raw = json.dumps(err, ensure_ascii=False)
        state.error_short = _short_error(err)
    return out
