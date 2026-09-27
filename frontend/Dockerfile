# Stage 1: Build Frontend (offline demo LUON TAT - xem ARG VITE_ENABLE_OFFLINE_DEMO duoi day)
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

# P0 SECURITY: build image khong bao gio duoc bật offline demo.
# Mac dinh false va phai override co y thuc; khi backend loi mang, co che offline
# cap phien dang nhap gia cho bat ky mat khau va suy doan quyen tu chuoi email.
ARG VITE_ENABLE_OFFLINE_DEMO=false
ENV VITE_ENABLE_OFFLINE_DEMO=$VITE_ENABLE_OFFLINE_DEMO

RUN npm run build

# Stage 2: Serve with Nginx Alpine
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
