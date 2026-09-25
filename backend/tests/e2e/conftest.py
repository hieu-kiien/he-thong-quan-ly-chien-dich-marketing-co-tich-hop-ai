"""Pytest configuration and shared fixtures for the E2E test suite."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Re-export all fixtures and helpers from conftest_e2e
from tests.e2e.conftest_e2e import (
    get_auth_headers,
    manager_headers,
    marketer_headers,
    approver_headers,
    assert_endpoint_or_skip_milestone
)

__all__ = [
    "get_auth_headers",
    "manager_headers",
    "marketer_headers",
    "approver_headers",
    "assert_endpoint_or_skip_milestone"
]
