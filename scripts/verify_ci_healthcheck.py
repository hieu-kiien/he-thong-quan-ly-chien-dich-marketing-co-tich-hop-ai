import os
import sys
import subprocess
import tempfile

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASH_PATH = r"C:\Program Files\Git\bin\bash.exe"
if not os.path.exists(BASH_PATH):
    import shutil
    BASH_PATH = shutil.which("bash") or "bash"

print("=====================================================================")
print(f" CI CONTAINER HEALTHCHECK SHELL LOGIC VERIFICATION")
print(f" Using bash executable: {BASH_PATH}")
print("=====================================================================")

def run_healthcheck_test(mock_curl_mode: str, use_legacy_code: bool = False):
    script = f"""#!/usr/bin/env bash
set -e

# Mock docker command
docker() {{
  echo "[MOCK DOCKER] command: docker $*"
}}

# Mock sleep for fast test execution
sleep() {{
  :
}}

# Mock curl command
curl() {{
  URL="$@"
  case "{mock_curl_mode}" in
    all_fail)
      return 1
      ;;
    backend_fail)
      return 1
      ;;
    frontend_fail)
      if echo "$URL" | grep -q "localhost:8000/health"; then
        echo '{{"status": "healthy"}}'
        return 0
      else
        return 1
      fi
      ;;
    all_pass)
      if echo "$URL" | grep -q "localhost:8000/health"; then
        echo '{{"status": "healthy"}}'
        return 0
      else
        echo '<html><body>React App</body></html>'
        return 0
      fi
      ;;
  esac
}}
export -f docker
export -f sleep
export -f curl
"""

    if use_legacy_code:
        # Legacy flawed code (no readiness flags, loop exhausts and returns exit code 0)
        script += """
echo "=== EXECUTING LEGACY CI SCRIPT (FLAWED) ==="
for i in $(seq 1 5); do
  if curl -sf http://localhost:8000/health | grep -q "healthy"; then
    echo "Backend health check passed on attempt $i."
    break
  fi
  echo "Waiting for backend ($i/5)..."
  sleep 1
done

for i in $(seq 1 5); do
  if curl -sf http://localhost:3000/ > /dev/null; then
    echo "Frontend HTTP check passed on attempt $i."
    break
  fi
  echo "Waiting for frontend ($i/5)..."
  sleep 1
done

docker compose ps
exit 0
"""
    else:
        # Hardened code from .github/workflows/ci.yml
        script += """
echo "=== EXECUTING HARDENED CI SCRIPT (.github/workflows/ci.yml) ==="
echo "Awaiting backend service health (60s timeout)..."
BACKEND_READY=0
for i in $(seq 1 5); do
  if curl -sf http://localhost:8000/health | grep -q "healthy"; then
    echo "Backend health check passed on attempt $i."
    BACKEND_READY=1
    break
  fi
  echo "Waiting for backend ($i/5)..."
  sleep 1
done

if [ "$BACKEND_READY" -ne 1 ]; then
  echo "::error::Backend health check failed after 60 seconds!"
  echo "=== DUMPING BACKEND CONTAINER LOGS ==="
  docker compose logs backend
  docker compose ps
  exit 1
fi

echo "Awaiting frontend service readiness (30s timeout)..."
FRONTEND_READY=0
for i in $(seq 1 5); do
  if curl -sf http://localhost:3000/ > /dev/null; then
    echo "Frontend HTTP check passed on attempt $i."
    FRONTEND_READY=1
    break
  fi
  echo "Waiting for frontend ($i/5)..."
  sleep 1
done

if [ "$FRONTEND_READY" -ne 1 ]; then
  echo "::error::Frontend service check failed after 30 seconds!"
  echo "=== DUMPING FRONTEND CONTAINER LOGS ==="
  docker compose logs frontend
  docker compose ps
  exit 1
fi

echo "=== DOCKER COMPOSE PROCESS SUMMARY ==="
docker compose ps
exit 0
"""

    with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False, encoding='utf-8') as f:
        f.write(script)
        temp_sh = f.name

    try:
        proc = subprocess.run(
            [BASH_PATH, temp_sh],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        if os.path.exists(temp_sh):
            os.remove(temp_sh)

tests = [
    {
        "name": "TEST 1: Backend Timeout Condition (Hardened Script)",
        "mode": "backend_fail",
        "legacy": False,
        "expected_code": 1,
        "expected_in_output": [
            "::error::Backend health check failed after 60 seconds!",
            "=== DUMPING BACKEND CONTAINER LOGS ===",
            "[MOCK DOCKER] command: docker compose logs backend"
        ]
    },
    {
        "name": "TEST 2: Frontend Timeout Condition (Hardened Script)",
        "mode": "frontend_fail",
        "legacy": False,
        "expected_code": 1,
        "expected_in_output": [
            "Backend health check passed on attempt 1.",
            "::error::Frontend service check failed after 30 seconds!",
            "=== DUMPING FRONTEND CONTAINER LOGS ===",
            "[MOCK DOCKER] command: docker compose logs frontend"
        ]
    },
    {
        "name": "TEST 3: All Services Healthy (Hardened Script)",
        "mode": "all_pass",
        "legacy": False,
        "expected_code": 0,
        "expected_in_output": [
            "Backend health check passed on attempt 1.",
            "Frontend HTTP check passed on attempt 1.",
            "=== DOCKER COMPOSE PROCESS SUMMARY ==="
        ]
    },
    {
        "name": "TEST 4: Flaw Reproduction (Mutation Test on Legacy Script)",
        "mode": "backend_fail",
        "legacy": True,
        "expected_code": 0, # Legacy script had false-positive exit 0 bug
        "expected_in_output": [
            "=== EXECUTING LEGACY CI SCRIPT (FLAWED) ===",
            "[MOCK DOCKER] command: docker compose ps"
        ]
    }
]

passed_all = True

for t in tests:
    print(f"\n--- Running {t['name']} ---")
    code, stdout, stderr = run_healthcheck_test(t['mode'], t['legacy'])
    print(f"Exit Code: {code} (Expected: {t['expected_code']})")
    
    code_match = (code == t['expected_code'])
    output_match = all(exp in stdout for exp in t['expected_in_output'])
    
    if code_match and output_match:
        print(f"[+] PASS: {t['name']}")
    else:
        passed_all = False
        print(f"[-] FAIL: {t['name']}")
        if not code_match:
            print(f"    Expected exit code {t['expected_code']}, got {code}")
        for exp in t['expected_in_output']:
            if exp not in stdout:
                print(f"    Missing expected string in stdout: '{exp}'")
        print("Stdout:\n", stdout)
        print("Stderr:\n", stderr)

print("\n=====================================================================")
print(" CI HEALTHCHECK VERIFICATION SUMMARY")
print("=====================================================================")
if passed_all:
    print("ALL TESTS PASSED: Hardened CI script correctly exits with code 1 on timeouts,")
    print("dumps container logs for diagnostics, and prevents silent false-positives.")
    sys.exit(0)
else:
    print("FAILURES DETECTED IN CI HEALTHCHECK LOGIC.")
    sys.exit(1)
