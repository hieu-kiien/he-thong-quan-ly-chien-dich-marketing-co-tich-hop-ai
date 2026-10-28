# MarketFlow — Hệ Thống Quản Lý Chiến Dịch Marketing Có Tích Hợp AI

> **Dự án môn học**: Ứng dụng trí tuệ nhân tạo (AIA331) — Mã số đề tài: 80300  
> **Trường**: Trường Đại học Công nghệ Thông tin & Truyền thông — Đại học Thái Nguyên  
> **Trạng thái kiểm thử**: **151 ca kiểm thử tự động** (104 Backend Pytest + 18 AI-Runner Pytest + 29 Playwright E2E) — **100% Pass**  
> **Hạ tầng Production**: [https://marketing.kienhieu.id.vn/](https://marketing.kienhieu.id.vn/) (Cloudflare Tunnel → VPS Ubuntu 24.04 LTS)  

---

## 1. Giới thiệu Hệ thống 

MarketFlow là giải pháp quản lý chiến dịch tiếp thị số tinh gọn, trung thực và an toàn dành riêng cho các doanh nghiệp vừa và nhỏ (SME) tại Việt Nam. Hệ thống kết hợp chặt chẽ giữa các nghiệp vụ quản trị tiếp thị cốt lõi và Trợ lý AI hội thoại hiện đại:

- **Quản lý Chiến dịch & Đa kênh**: Quản lý mục tiêu, tiến độ, ngân sách tổng và phân bổ ngân sách cho 7 kênh tiếp thị chuẩn: Facebook, TikTok, Instagram, Zalo OA, Email, Google Ads, Website.
- **Quy trình Kiểm duyệt Nội dung Chặt chẽ**: Áp dụng máy trạng thái (`DRAFT` → `PENDING_REVIEW` → `APPROVED` / `REJECTED` → `PUBLISHED`). Tách bạch quyền hạn giữa người tạo và người duyệt; người quản lý không được tự duyệt bài viết của chính mình (`CANNOT_REVIEW_OWN`).
- **Ghi nhận & Phân tích Chỉ số Thực tế**: Nhập số liệu hàng ngày bằng tay hoặc import file CSV (hỗ trợ xem trước và kiểm tra tính logic). Tính toán tự động các chỉ số hiệu suất: CTR, CVR, CPC, CPA, CPM.
- **Trợ lý AI Hội thoại (OpenCode Zen)**: Không gian làm việc riêng (`/assistant`) giúp lên ý tưởng nội dung, viết nháp bài viết theo quy chuẩn từng kênh và tóm tắt hiệu quả chiến dịch.
- **Nguyên tắc Chống Tính năng Ảo (Rule 0)**: Toàn bộ số liệu hiển thị dựa trên dữ liệu người dùng thật hoặc dữ liệu mẫu có nhãn `SEED`. AI chỉ tạo đề xuất (`ai_action = PROPOSED`); người dùng phải xác nhận trên giao diện thì hành động mới được thực thi.

---

## 2. Kiến trúc Hệ thống

```mermaid
flowchart TD
    Browser["Trình duyệt (React 18 + Vite SPA)"]
    
    subgraph VPS["Máy chủ VPS Ubuntu 24.04 LTS (2 vCPU / 2GB RAM)"]
        Nginx["Nginx Reverse Proxy (:8080)"]
        
        subgraph Backend["FastAPI Backend (marketflow-api :8000)"]
            REST["RESTful Routers (/api/v1/*)"]
            Service["Service Layer (Nghiệp vụ & Phân quyền)"]
            MCP["MCP Streamable-HTTP Server (/mcp)"]
        end

        DB[(PostgreSQL 16 / SQLite)]

        subgraph Runner["ai-runner Service (:8100, user: mfai)"]
            RunnerAPI["FastAPI Runner (/run, /health)"]
            Queue["Hàng đợi tuần tự (Concurrency = 1)"]
            OpenCode["OpenCode CLI Subprocess"]
        end
    end

    ZenCloud["OpenCode Zen Cloud (Model miễn phí)"]

    Browser -->|HTTPS / SSE| Nginx
    Nginx --> REST
    REST --> Service --> DB
    Service --> MCP

    REST -->|POST /run (NDJSON Stream)| RunnerAPI
    RunnerAPI --> Queue --> OpenCode
    OpenCode -->|Gọi model| ZenCloud
    OpenCode -->|Gọi MCP Tools (/mcp + Bearer Run-Token)| MCP
```

---

## 3. Tài khoản Mẫu Demo (Seed Accounts)

Dữ liệu mẫu chuẩn tiếp thị cho chuỗi cà phê đặc sản Việt Nam (**Cà phê Rang xay An Nam**) được tạo sẵn trong hệ thống:

| Vai trò | Email đăng nhập | Mật khẩu | Quyền hạn chính |
|---|---|---|---|
| **Người quản lý (`MANAGER`)** | `manager@marketflow.vn` | `Manager@123` | Quản trị người dùng, kênh, hồ sơ thương hiệu; phê duyệt hoặc từ chối bài viết của nhân viên. |
| **Nhân viên marketing (`MARKETER`)** | `marketer@marketflow.vn` | `Marketer@123` | Tạo và quản lý chiến dịch của mình; soạn thảo bài viết; gửi duyệt; lập lịch đăng; nhập số liệu. |
| **Nhân viên marketing 2 (`MARKETER`)** | `marketer2@marketflow.vn` | `Marketer@123` | Phụ trách chiến dịch "Mùa Thu Cầu Đất"; phối hợp làm việc theo nhóm. |

---

## 4. Hướng dẫn Cài đặt & Chạy Cục bộ (Local Quick Start)

### Yêu cầu môi trường
- Python 3.12 hoặc 3.13
- Node.js 20+ và npm
- Git

### 4.1. Khởi chạy Backend (FastAPI)
Mở cửa sổ dòng lệnh (PowerShell):
```powershell
# 1. Di chuyển vào thư mục backend
cd backend

# 2. Tạo và kích hoạt môi trường ảo Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Cài đặt các thư viện phụ thuộc
pip install --upgrade pip
pip install -r requirements.txt

# 4. Chạy migration tạo cấu trúc cơ sở dữ liệu (SQLite mặc định)
python -m alembic upgrade head

# 5. Nạp dữ liệu mẫu demo
python seed/seed_demo.py --reset

# 6. Khởi động máy chủ backend tại cổng 8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Docs Swagger UI có sẵn tại: `http://127.0.0.1:8000/docs`.

### 4.2. Khởi chạy AI Runner (Tuỳ chọn — nếu sử dụng Trợ lý AI thật)
```powershell
# Mở một cửa sổ terminal mới
cd ai-runner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Khởi chạy dịch vụ runner tại cổng 8100
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100
```
*(Ghi chú: Nếu không bật runner, các chức năng quản lý chiến dịch, nội dung, lịch và số liệu vẫn hoạt động bình thường. Bạn cũng có thể bật chế độ giả lập UI offline bằng cách đặt `VITE_ASSISTANT_SIMULATOR=true` trong `frontend/.env`).*

### 4.3. Khởi chạy Frontend (React + Vite)
```powershell
# Mở một cửa sổ terminal mới
cd frontend

# 1. Cài đặt thư viện phụ thuộc
npm ci

# 2. Khởi động giao diện dev server tại cổng 5173
npm run dev
```
Truy cập giao diện ứng dụng tại: `http://localhost:5173`.

---

## 5. Chạy bằng Docker Compose

Hệ thống đã được đóng gói đầy đủ gồm PostgreSQL 16, Backend FastAPI tự động chạy migration, và Frontend phục vụ bởi Nginx:

```bash
# Khởi động toàn bộ cụm dịch vụ (Postgres + Backend + Frontend)
docker compose up -d

# Xem log khởi động
docker compose logs -f backend
```
Truy cập ứng dụng qua cổng `http://localhost:8080`.

---

## 6. Cách thức Hoạt động của Trợ lý AI (OpenCode Zen Integration)

1. **Điều phối Đa Mô hình & Không lộ API Key**: Hệ thống kết nối qua **OpenCode CLI** với **13 mô hình từ 5 nền tảng** (`OpenCode Zen Free`, `Groq LPU`, `NVIDIA NIM`, `OpenRouter`, `Google Gemini`). Không lưu trữ bất kỳ API key nào trong CSDL và không gửi key về trình duyệt.
2. **Giao tiếp hai chiều an toàn qua MCP (Model Context Protocol)**:
   - Backend sinh một mã **Run-Token** JWT ngắn hạn (10 phút) cấp cho tiến trình OpenCode.
   - OpenCode gọi ngược lại Backend qua endpoint `/mcp` (Stateless-HTTP) để đọc số liệu chiến dịch hoặc tạo đề xuất.
3. **Cơ chế Chỉ Đề Xuất (Proposal-Only)**:
   - Khi AI gọi các công cụ ghi dữ liệu (ví dụ: `propose_content_drafts`, `propose_schedule`), hệ thống chỉ tạo bản ghi `ai_action` ở trạng thái `PROPOSED`.
   - Một thẻ đề xuất trực quan xuất hiện tại panel bên phải của giao diện.
   - Người dùng có thể chỉnh sửa lại tiêu đề, nội dung và bấm **Xác nhận**; khi đó hành động mới thực sự được tạo trong CSDL dưới danh tính của người dùng đó.
4. **Phòng thủ Tấn công Prompt Injection**:
   - Cấu hình agent khóa hoàn toàn lệnh shell (`bash: deny`), ngăn chặn đọc file hệ thống (`read: deny` chuyển hướng tới `/__mf_never__/x`), bảo vệ an toàn cho máy chủ VPS.

---

## 7. Các Hạn chế Thực tế (Honest Limitations)

1. **Hạn mức Tần suất Gọi AI (Free Tier Rate Limits)**: Khi một nhà cung cấp mô hình miễn phí chạm giới hạn tốc độ (HTTP 429) vào khung giờ cao điểm, dịch vụ `ai-runner` tự động chuyển đổi sang chuỗi 12 mô hình dự phòng đa nền tảng (`glm-5.3-flash-free`, `mimo-v2.6-flash-free`, `groq/openai/gpt-oss-120b`, `groq/qwen/qwen3.8-27b`, `nemotron-3.5-super-vl:free`, `gemini-3.5-flash-lite`...) và báo lỗi trung thực nếu tất cả đều bận.
2. **Không Tự Động Đăng Bài Lên Mạng Xã Hội**: Hệ thống không tích hợp API tự động xuất bản (để tránh rủi ro khoá tài khoản mạng xã hội của doanh nghiệp). Lịch đăng bài đóng vai trò lập kế hoạch; nhân viên tự đăng bài ra kênh ngoài và cập nhật liên kết xác nhận.
3. **Giới hạn Đồng thời trên Máy chủ Đơn (Concurrency = 1)**: Do mỗi tiến trình OpenCode tiêu thụ ~490 MB RAM RSS, máy chủ VPS giới hạn xử lý tuần tự từng yêu cầu một để đảm bảo không bị cạn kiệt RAM. Các yêu cầu gửi đồng thời sẽ được xếp vào hàng đợi chờ ngắn (tối đa 8 vị trí).

---

## 8. Mục lục Tài liệu Kỹ thuật Chi tiết

Toàn bộ tài liệu chi tiết của dự án được lưu trữ trong thư mục `docs/`:

- [Tài liệu Phân tích Yêu cầu & Thiết kế Hệ thống (KT1)](docs/REQUIREMENTS_AND_DESIGN.md): Bối cảnh SME, 2 vai trò người dùng, bảng Input/Process/Output, yêu cầu phi chức năng, sơ đồ Use Case, ERD 14 bảng CSDL và luồng dữ liệu.
- [Đặc tả Phân hệ Trợ lý AI (KT3)](docs/AI_ASSISTANT.md): Kiến trúc AI Runner, danh mục 14 công cụ MCP, bộ chọn 13 mô hình đa nền tảng, giao thức sự kiện SSE, tối ưu prompt qua 4 giai đoạn cải tiến, xử lý lỗi và quy trình con người duyệt đề xuất.
- [Đạo đức AI & Quyền Riêng tư Dữ liệu](docs/AI_ETHICS_AND_PRIVACY.md): Bảo vệ khoá xác thực, phạm vi dữ liệu gửi cho mô hình, điều khoản huấn luyện của mô hình miễn phí, các biện pháp chống ảo giác và minh chứng phòng thủ Prompt Injection.
- [Kế hoạch & Danh mục Ca Kiểm thử (Testing)](docs/TESTING.md): Hướng dẫn chạy từng bộ test, số liệu đo lường thực tế, danh mục 151 ca kiểm thử tự động (104 Backend Pytest + 18 AI-Runner Pytest + 29 Playwright E2E) và 8 ca đánh giá Prompt.
- [Minh chứng Ứng dụng AI Trong SDLC](docs/AI_IN_SDLC.md): Nhật ký sử dụng AI xuyên suốt các giai đoạn KT1 (phân tích yêu cầu & kiểm định rủi ro kiến trúc), KT2 (lập trình đa tác nhân), KT3 (thực nghiệm P0 Spike trên VPS) và đánh giá chất lượng tự động.
- [Hướng dẫn Triển khai Máy chủ VPS](docs/DEPLOYMENT-VPS.md): Hướng dẫn cấu hình systemd, Nginx, PostgreSQL và Cloudflare Tunnel trên máy chủ sản xuất thực tế.
