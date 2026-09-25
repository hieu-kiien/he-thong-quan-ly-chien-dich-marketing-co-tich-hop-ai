"""MarketFlow AI — E2E Test Suite Runner Script.
Executes the full 4-Tier Opaque-Box E2E Suite and prints structured summary reports.

Usage:
    python backend/tests/e2e/run_e2e.py
"""

import sys
import subprocess
import time
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def main():
    print("=" * 80)
    print("  MARKETFLOW AI — OFFICIAL RELEASE OPAQUE-BOX E2E TEST RUNNER")
    print("  Tiers: 1 (Coverage), 2 (Boundary/Corner), 3 (Cross-Feature), 4 (Real Scenarios)")
    print("=" * 80)

    start_time = time.time()
    cmd = [
        sys.executable,
        "-m", "pytest",
        "backend/tests/e2e/test_e2e_suite.py",
        "-v",
        "--tb=short"
    ]

    print(f"[*] Executing: {' '.join(cmd)}")
    print(f"[*] Working directory: {PROJECT_ROOT}\n")

    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    duration = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"  E2E Test Run Completed in {duration:.2f} seconds (Exit Code: {res.returncode})")
    print("=" * 80)

    return res.returncode

if __name__ == "__main__":
    sys.exit(main())
