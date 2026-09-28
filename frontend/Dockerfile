# =============================================================================
# Frontend image - 2 stage: build Vite -> serve bang nginx non-root.
#
# BAO DAT BIEN (build time, khong phai runtime):
#   - VITE_API_URL               : URL cua FastAPI. Mac dinh `/api/v1` ->
#                                  frontend goi API qua chinh reverse proxy
#                                  nginx cua container nay, khong lo CORS.
#   - VITE_ENABLE_OFFLINE_DEMO   : co bat che "offline demo" hay khong. Xem canh
#                                  bao P0 ben duoi - TUYET DOI KHONG BAO GIO
#                                  BAT cho production.
# =============================================================================

# Stage 1: Build Frontend
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

# P0 SECURITY: build image khong bao gio duoc bat offline demo.
# Mac dinh false va phai override co y thuc; khi backend loi mang, co che offline
# cap phien dang nhap gia cho bat ky mat khau va suy doan quyen tu chuoi email.
#
# CANH BAO KHONG BO QUA: bien nay duoc `ENV` hoa luc BUILD nen no bi
# `npm run build` nung vao JS bundle nen KHONG THE tat bang bien moi o runtime,
# va KHONG THE go lai giup - chi can `docker compose build --build-arg
# VITE_ENABLE_OFFLINE_DEMO=true` mot lan la shell offline da nam trong
# frontend/dist/assets/*.js, dung cho moi request sau do. Backend co the
# dang nhap duoc bang BAT KY mat khau va co quyen tao/xoa/sua du lieu thay
# vi chay bang mat khau that.
#   -> KHONG BAO GIO build/deploy production voi co true.
#   -> CI/CD nen dat co hard (repo variable hoac pipeline policy) chan
#      `-b VITE_ENABLE_OFFLINE_DEMO=true` o moi pipeline deploy that.
#   -> Neu da build nham, KHONG sua JS bundle: doi hash cache bang cach xoa
#      frontend/dist va build lai, roi `docker compose build --no-cache`.
ARG VITE_ENABLE_OFFLINE_DEMO=false
ENV VITE_ENABLE_OFFLINE_DEMO=$VITE_ENABLE_OFFLINE_DEMO

RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Serve with nginx chay non-root.
#
# LUA CHON: `nginxinc/nginx-unprivileged:alpine` (CHON option dau tien).
#   - Docker chay container voi root mac dinh thi `USER nginx` chi la chu thich
#     tren process cha cua chinh image do - root van giu quyen. De THAT SU
#     non-root thi phai doi sang image mac dinh da chay user `nginx` (uid 101).
#   - Image nay listen san o port 8080 (nginx master process khong duoc uid
#     < 1010 nen khong bind duoc port < 1024) -> EXPOSE 80 -> 8080, va
#     `listen 80` -> `listen 8080` trong nginx.conf. Docker compose publish
#     `3000:8080` cho khop.
#   - Da kiem chung image ton tai tren Docker Hub (docker manifest inspect
#     nginxinc/nginx-unprivileged:alpine -> OCI image index, exit 0).
#   - Goc chu chay /etc/nginx/conf.d/ giong het image nginx:alpine, nen
#     `COPY nginx.conf /etc/nginx/conf.d/default.conf` va
#     `COPY security-headers.conf /etc/nginx/conf.d/security-headers.conf`
#     giong nhu cu. `CMD` giong het (nginx -g "daemon off;").
# -----------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# (2a/2b) File header dung chung: bat buoc COPY cung image vi no duoc `include`
# tu default.conf. THIEU FILE NAY => nginx fail khi start ("open() failed").
COPY security-headers.conf /etc/nginx/conf.d/security-headers.conf

# File html/doc static tren image la read-only, nen user nginx van doc duoc
# khong can `chown`. Neu sau nay them `client_body_temp_path` hay thu muc ghi
# nao, nho tro vao mot temp path ma user nginx ghi duoc.
EXPOSE 8080

# (3c) HEALTHCHECK. Image unprivileged co `wget` cua busybox nen khong can curl.
# `--spider` chi gui HEAD, khong tai body, nen probe nhanh. Neu container
# nginx da chay nhung route cha loi van bao "healthy" - day la canh bao som,
# frontend van chay duoc doc lap voi backend (SPA van load duoc, chi API loi).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider "http://127.0.0.1:8080/" || exit 1

CMD ["nginx", "-g", "daemon off;"]
