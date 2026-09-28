FROM python:3.11-slim

# Tạo non-root user 'appuser' để đảm bảo an toàn bảo mật
RUN groupadd -r appgroup && useradd -r -g appgroup -s /bin/bash appuser

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn
COPY . .

# Thư mục dữ liệu: tạo sẵn và chown cho appuser. Khi dùng named volume, Docker copy
# nội dung + quyền sở hữu từ đây sang volume nên appuser ghi được ngay.
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# Entrypoint chuẩn hoá quyền sở hữu volume rồi drop xuống appuser.
# Bắt buộc cho bind-mount ./backend/data trên host Linux — xem docker-entrypoint.sh.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

# ENTRYPOINT chạy với quyền root chỉ trong thời gian ngắn để chown /app/data, rồi
# drop xuống appuser (xem docker-entrypoint.sh). CMD chạy hoàn toàn non-root.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
