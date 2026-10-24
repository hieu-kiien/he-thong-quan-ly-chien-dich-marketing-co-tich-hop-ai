#!/usr/bin/env python3
"""Fake OpenCode executable for ai-runner pytest test-suite.

Replays recorded JSONL fixtures or simulates hangs/errors based on CLI args,
prompt keywords, or environment variables.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def main() -> int:
    args = sys.argv[1:]

    # Handle --version probe
    if "--version" in args:
        print("opencode 1.19.0")
        return 0

    # Read prompt from arguments or stdin
    prompt = ""
    if "--" in args:
        idx = args.index("--")
        prompt = " ".join(args[idx + 1:])
    elif args and not args[-1].startswith("-"):
        prompt = args[-1]
    elif not sys.stdin.isatty():
        try:
            prompt = sys.stdin.read()
        except Exception:  # noqa: BLE001
            prompt = ""

    mode = os.environ.get("FAKE_OPENCODE_MODE", "").lower()
    prompt_low = prompt.lower()

    # Check for invalid model
    model = None
    if "-m" in args:
        idx = args.index("-m")
        if idx + 1 < len(args):
            model = args[idx + 1]

    if model == "opencode/bad-model":
        with open(FIXTURES_DIR / "model_not_found.jsonl", encoding="utf-8") as f:
            print(f.read(), end="")
        sys.stderr.write("Error: Unexpected server error\n")
        return 1

    # Check for stale session error
    session = None
    if "-s" in args:
        idx = args.index("-s")
        if idx + 1 < len(args):
            session = args[idx + 1]

    if session == "ses_stale_123":
        sys.stderr.write("Error: Session not found\n")
        return 1

    # Hang / timeout simulation
    if mode == "hang" or "hang" in prompt_low:
        time.sleep(60.0)
        return 0

    # Real-world free tier exhaustion (observed on the VPS with opencode 1.19.4): the error only
    # appears in the log stream (stderr with --print-logs) and opencode keeps retrying forever.
    if mode == "usagelimit" or "usagelimit" in prompt_low:
        sys.stderr.write(
            'timestamp=2026-10-24T16:00:51.647Z level=ERROR message="stream error" providerID=opencode '
            'modelID=big-pickle error.error="AI_APICallError: Free usage limit reached. '
            'Subscribe to OpenCode Go to keep going: https://opencode.ai/go"\n'
        )
        sys.stderr.flush()
        time.sleep(60.0)
        return 0

    # Rate limit / FreeTierError simulation
    if mode == "freetier" or "freetier" in prompt_low:
        with open(FIXTURES_DIR / "freetier_403.jsonl", encoding="utf-8") as f:
            print(f.read(), end="")
        return 0

    # Tool calling simulation
    if mode == "tool" or "tool" in prompt_low:
        with open(FIXTURES_DIR / "tool_success.jsonl", encoding="utf-8") as f:
            for line in f:
                print(line, end="")
                sys.stdout.flush()
                time.sleep(0.01)
        return 0

    # Empty response simulation
    if mode == "empty" or "empty" in prompt_low:
        with open(FIXTURES_DIR / "empty.jsonl", encoding="utf-8") as f:
            print(f.read(), end="")
        return 0

    # Slow execution simulation (for queue ordering / abort tests)
    if mode == "slow" or "slow" in prompt_low:
        time.sleep(0.4)
        with open(FIXTURES_DIR / "simple_success.jsonl", encoding="utf-8") as f:
            print(f.read(), end="")
        return 0

    # Default: simple success
    with open(FIXTURES_DIR / "simple_success.jsonl", encoding="utf-8") as f:
        print(f.read(), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
