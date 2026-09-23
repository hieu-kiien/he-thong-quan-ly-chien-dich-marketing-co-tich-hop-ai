FROM python:3.11-slim

# Tạo non-root user 'appuser' để đảm bảo an toàn bảo mật
RUN groupadd -r appgroup && useradd -r -g appgroup -s /bin/bash appuser

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn
COPY . .

# Phân quyền thư mục cho appuser
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
