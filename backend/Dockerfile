# MarketFlow v2 - backend FastAPI (Python 3.12, giống VPS production).
FROM python:3.12-slim

# Chạy bằng user không đặc quyền
RUN groupadd -r appgroup && useradd -r -g appgroup -s /usr/sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

USER appuser
EXPOSE 8000

# Migration chạy trong `command` của docker-compose (alembic upgrade head) trước khi khởi động uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]