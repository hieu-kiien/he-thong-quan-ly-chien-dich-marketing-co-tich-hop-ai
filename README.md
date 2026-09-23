# Hệ thống Quản lý Chiến dịch Marketing tích hợp AI (MarketFlow AI)
### Học phần: Ứng dụng trí tuệ nhân tạo (AIA331) — Mã đề tài: 80300 — ICTU

Hệ thống được thiết kế và xây dựng theo chuẩn phần mềm doanh nghiệp, đáp ứng trọn vẹn 40 tiêu chí đánh giá môn học (KT1, KT2, KT3, Cuối kỳ) và khớp 100% với tài liệu Báo cáo kỹ thuật V8 (`Bao_Cao_AIA331_80300_ICTU_V8`).

---

## 1. Cấu trúc Dự án

```text
├── backend/                        # API lõi viết bằng Python FastAPI
│   ├── app/
│   │   ├── api/v1/                 # Endpoints: auth, campaigns, contents, reviews, metrics, ai
│   │   ├── core/                   # Cấu hình, bảo mật JWT, database session
│   │   ├── models/                 # 11 bảng SQLAlchemy ORM khớp 100% design/schema.sql
│   │   ├── schemas/                # Pydantic Schemas (Data Contracts & AI Output)
│   │   └── services/               # Nghiệp vụ & AI Service Adapter
│   ├── prompts/                    # Prompts tách khỏi code (V1, V2, V3 cho 3 bài toán AI)
│   ├── seed/                       # Script nạp CSDL & dữ liệu mẫu (seed_data.py)
│   ├── tests/                      # Bộ kiểm thử tự động chuẩn IEEE 829 (11/11 ca PASS)
│   ├── requirements.txt            # Thư viện Python
│   └── .env.example                # Cấu hình biến môi trường
├── frontend/                       # Giao diện Web Client (React 18 + Vite + Tailwind CSS)
│   ├── src/
│   │   ├── components/             # Sidebar, Navbar, MetricCard, CampaignTable, WorkflowCanvas, AIDrawer
│   │   ├── pages/                  # Dashboard (Bento Grid), ReviewQueue (Human-in-the-loop)
│   │   ├── services/               # Axios API client gọi tới Backend
│   │   └── types/                  # TypeScript interfaces
├── docker-compose.yml              # Đóng gói container theo chuẩn Phụ lục C Báo cáo V8
├── Bao_Cao_AIA331_80300_ICTU_V8/   # Hồ sơ Báo cáo kỹ thuật LaTeX và PDF chính thức
├── đề tài của tôi.png              # Ảnh đặc tả đề tài 80300
└── yêu cầu của môn học.png         # Ảnh 40 tiêu chí chấm điểm
```

---

## 2. Hướng dẫn Khởi chạy Ứng dụng

### Bước 1: Khởi động Backend Python (FastAPI)
Mở cửa sổ dòng lệnh PowerShell thứ nhất:
```powershell
cd backend

# Khởi tạo CSDL SQLite và nạp dữ liệu mẫu
python seed/seed_data.py

# Khởi chạy server FastAPI
python -m uvicorn app.main:app --reload --port 8000
```
* **Swagger API Docs**: Truy cập `http://localhost:8000/docs`

### Bước 2: Khởi động Frontend Web (React + Vite)
Mở cửa sổ dòng lệnh PowerShell thứ hai:
```powershell
cd frontend

# Cài đặt thư viện (nếu chưa cài)
npm install

# Khởi chạy giao diện
npm run dev
```
* **Giao diện Web**: Truy cập `http://localhost:5173`

---

## 3. Tài khoản Kiểm thử Demo

Hệ thống tích hợp nút **Chuyển đổi vai trò nhanh (Fast Demo Role Switcher)** ngay trên thanh Navbar, hoặc bạn có thể đăng nhập bằng các tài khoản mẫu:

| Vai trò | Email | Mật khẩu | Quyền hạn đặc trưng |
| :--- | :--- | :--- | :--- |
| **Quản lý (Manager)** | `manager@ictu.edu.vn` | `Manager@123` | Toàn quyền, phê duyệt / từ chối nội dung, xem báo cáo, xóa chiến dịch. |
| **Nhân viên (Marketer)** | `marketer@ictu.edu.vn` | `Marketer@123` | Tạo chiến dịch, soạn nội dung, gọi AI sinh ý tưởng & bài nháp, nộp duyệt. |

---

## 4. Chạy Bộ Kiểm thử Tự động Chuẩn IEEE 829
```powershell
cd backend
pytest -v
```
*Kết quả:* Vượt qua toàn bộ **11/11 ca kiểm thử** (`TC_POS_01` $\rightarrow$ `TC_POS_05`, `TC_NEG_01` $\rightarrow$ `TC_NEG_03`, `TC_BND_01` $\rightarrow$ `TC_BND_03`) với tỷ lệ đạt 100%.
