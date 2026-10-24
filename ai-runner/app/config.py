"""Runner configuration, read from environment variables (see README.md)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

MODEL_PATTERN = r"^[A-Za-z0-9._-]+/[A-Za-z0-9._:-]+$"


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return max(minimum, int(raw))


def _float(name: str, default: float, minimum: float = 1.0) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return max(minimum, float(raw))


@dataclass
class Settings:
    runner_token: str = ""
    opencode_bin: str = "opencode"
    sandbox_dir: str = "."
    agent: str = "marketflow"
    model: str | None = None
    fallback_models: list[str] = field(default_factory=list)
    timeout_s: float = 180.0
    concurrency: int = 1
    max_queue: int = 8
    max_prompt_chars: int = 60_000
    kill_grace_s: float = 3.0
    pure: bool = True
    host: str = "127.0.0.1"
    port: int = 8100
    # Extra env passed through to opencode (besides PATH/HOME/LANG/XDG_*/MF_RUN_TOKEN).
    passthrough_env: list[str] = field(default_factory=list)

    @property
    def opencode_cmd(self) -> list[str]:
        """Command prefix used to start opencode. A `.py` path is run with the current
        interpreter (used by the test-suite's fake opencode)."""
        if self.opencode_bin.endswith(".py"):
            return [sys.executable, self.opencode_bin]
        return [self.opencode_bin]

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            runner_token=os.environ.get("RUNNER_TOKEN", ""),
            opencode_bin=os.environ.get("OPENCODE_BIN", "opencode"),
            sandbox_dir=os.environ.get("RUNNER_SANDBOX_DIR", "."),
            agent=os.environ.get("OPENCODE_AGENT", "marketflow"),
            model=(os.environ.get("OPENCODE_MODEL") or "").strip() or None,
            fallback_models=_split_csv(os.environ.get("OPENCODE_FALLBACK_MODELS")),
            timeout_s=_float("RUNNER_TIMEOUT_S", 180.0),
            concurrency=_int("RUNNER_CONCURRENCY", 1),
            max_queue=_int("RUNNER_MAX_QUEUE", 8, minimum=0),
            max_prompt_chars=_int("RUNNER_MAX_PROMPT_CHARS", 60_000),
            kill_grace_s=_float("RUNNER_KILL_GRACE_S", 3.0, minimum=0.1),
            pure=os.environ.get("OPENCODE_PURE", "1").strip() not in ("0", "false", "no"),
            host=os.environ.get("RUNNER_HOST", "127.0.0.1"),
            port=_int("RUNNER_PORT", 8100),
            passthrough_env=_split_csv(os.environ.get("RUNNER_PASSTHROUGH_ENV")),
        )
