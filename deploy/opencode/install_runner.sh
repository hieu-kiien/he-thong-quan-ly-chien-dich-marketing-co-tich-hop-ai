#!/usr/bin/env bash
# Idempotent installer for MarketFlow AI Runner on Ubuntu 24.04 VPS
set -euo pipefail

echo "==> [1/7] Ensuring mfai system user..."
if ! id mfai &>/dev/null; then
    useradd -r -s /usr/sbin/nologin -d /var/lib/mfai -m mfai
fi
mkdir -p /var/lib/mfai
chown -R mfai:mfai /var/lib/mfai
chmod 750 /var/lib/mfai

echo "==> [2/7] Checking OpenCode binary..."
if [ ! -x /opt/opencode/bin/opencode ]; then
    echo "ERROR: /opt/opencode/bin/opencode not found or not executable!" >&2
    exit 1
fi

echo "==> [3/7] Setting up directories..."
mkdir -p /etc/marketflow
mkdir -p /opt/marketflow/ai-runner/app
mkdir -p /opt/marketflow/ai-runner/sandbox/.opencode/agent

echo "==> [4/7] Ensuring environment file /etc/marketflow/ai-runner.env..."
if [ ! -f /etc/marketflow/ai-runner.env ]; then
    RANDOM_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(24))")
    cat > /etc/marketflow/ai-runner.env <<EOF
# MarketFlow AI Runner environment configuration
RUNNER_TOKEN=${RANDOM_TOKEN}
OPENCODE_BIN=/opt/opencode/bin/opencode
RUNNER_SANDBOX_DIR=/opt/marketflow/ai-runner/sandbox
OPENCODE_AGENT=marketflow
OPENCODE_MODEL=opencode/big-pickle
OPENCODE_FALLBACK_MODELS=opencode/glm-5.3-flash-free,opencode/deepseek-v4.1-flash-free
RUNNER_TIMEOUT_S=180.0
RUNNER_CONCURRENCY=1
RUNNER_MAX_QUEUE=8
RUNNER_HOST=127.0.0.1
RUNNER_PORT=8100
EOF
    chmod 600 /etc/marketflow/ai-runner.env
    echo "Created new /etc/marketflow/ai-runner.env with random token."
else
    echo "Existing /etc/marketflow/ai-runner.env preserved."
fi

echo "==> [5/7] Deploying sandbox agent & config..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Copy agent and opencode config to sandbox
cp "${REPO_DIR}/deploy/opencode/agent/marketflow.md" /opt/marketflow/ai-runner/sandbox/.opencode/agent/marketflow.md
cp "${REPO_DIR}/deploy/opencode/opencode.json" /opt/marketflow/ai-runner/sandbox/opencode.json

# Copy ai-runner application code if not already in destination
if [ "${REPO_DIR}/ai-runner/app" != "/opt/marketflow/ai-runner/app" ]; then
    cp -r "${REPO_DIR}/ai-runner/app/"* /opt/marketflow/ai-runner/app/
fi
chown -R root:root /opt/marketflow/ai-runner
chmod -R a+rX /opt/marketflow/ai-runner/sandbox
chmod -R a+rX /opt/marketflow/ai-runner/app

echo "==> [6/7] Setting up Python virtual environment..."
VENV_DIR="/opt/marketflow/ai-runner/.venv"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet -r "${REPO_DIR}/ai-runner/requirements.txt"

echo "==> [7/7] Configuring systemd service..."
cp "${REPO_DIR}/deploy/vps/marketflow-ai-runner.service" /etc/systemd/system/marketflow-ai-runner.service
systemctl daemon-reload
systemctl enable marketflow-ai-runner
systemctl restart marketflow-ai-runner

echo "==> Verifying service health..."
sleep 2
systemctl is-active --quiet marketflow-ai-runner && echo "marketflow-ai-runner is ACTIVE!" || {
    echo "ERROR: marketflow-ai-runner failed to start!"
    systemctl status marketflow-ai-runner --no-pager
    journalctl -u marketflow-ai-runner -n 30 --no-pager
    exit 1
}

curl -s -m 5 http://127.0.0.1:8100/health | python3 -m json.tool || true
echo "==> Installation complete successfully."
