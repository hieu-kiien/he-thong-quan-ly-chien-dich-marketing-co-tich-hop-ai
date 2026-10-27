# MarketFlow v2 - ai-runner (chạy OpenCode CLI cho Trợ lý AI).
# Build context phải là THƯ MỤC GỐC của repo (cần cả deploy/opencode):
#   docker compose --profile runner build
FROM python:3.12-slim

# Node.js + OpenCode CLI
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
    && npm install -g opencode-ai \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r mfai && useradd -r -g mfai -m -d /home/mfai -s /usr/sbin/nologin mfai

WORKDIR /srv/ai-runner
COPY ai-runner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ai-runner/app ./app

# Sandbox: thư mục rỗng chỉ chứa agent đã khoá quyền + cấu hình MCP trỏ về dịch vụ backend trong compose
ARG MCP_URL=http://backend:8000/mcp/
COPY deploy/opencode/agent/marketflow.md /srv/sandbox/.opencode/agent/marketflow.md
COPY deploy/opencode/opencode.json /srv/sandbox/opencode.json
RUN sed -i "s#http://127.0.0.1:8000/mcp/#${MCP_URL}#" /srv/sandbox/opencode.json \
    && chown -R mfai:mfai /srv/sandbox /srv/ai-runner /home/mfai

USER mfai
ENV HOME=/home/mfai \
    RUNNER_SANDBOX_DIR=/srv/sandbox \
    OPENCODE_BIN=opencode \
    RUNNER_HOST=0.0.0.0 \
    RUNNER_PORT=8100
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]