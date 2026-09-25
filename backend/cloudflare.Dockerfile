FROM python:3.11-slim

RUN groupadd --system appgroup && useradd --system --gid appgroup --home-dir /app appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

ENV DATABASE_URL=sqlite:////app/data/marketing_campaigns.db
EXPOSE 8000 8001
USER appuser

CMD ["python", "cloudflare_runtime.py"]
