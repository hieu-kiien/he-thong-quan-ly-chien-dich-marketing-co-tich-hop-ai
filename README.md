# Hệ thống Quản lý Chiến dịch Marketing tích hợp AI (MarketFlow AI)
### Học phần: Ứng dụng Trí tuệ Nhân tạo (AIA331) — Mã Đề tài: 80300 — ICTU (Phiên bản V9)

Hệ thống được thiết kế và hiện thực hóa theo tiêu chuẩn công nghiệp và học thuật nghiêm ngặt (ISO/IEC/IEEE 29148, ISO/IEC/IEEE 42010, ISO/IEC 25010, NIST AI RMF 1.0). Dự án đáp ứng trọn vẹn 40 tiêu chí đánh giá môn học (KT1, KT2, KT3, Cuối kỳ), đồng bộ 100% với tài liệu **Báo cáo Hoàn thiện & Đánh giá Thực nghiệm V9** (`Bao_Cao_AIA331_80300_ICTU_V9`) và Ma trận truy xuất nguồn gốc (`requirements-traceability.csv`).

---

## 1. Điểm Nổi bật Kiến trúc & Kỹ thuật Vòng 3 (Release V9)

1. **Bảo mật Phân quyền Mức Bản ghi (Record-Level Authorization - NFR01)**:
   - Khắc phục triệt để lỗ hổng leo quyền ngang IDOR (Insecure Direct Object Reference).
   - Tài khoản vai trò **Marketer** chỉ có quyền xem, soạn nội dung, gọi AI và ghi nhận metrics trên các chiến dịch mà mình là người tạo (`owner_id`) hoặc được chỉ định thành viên thông qua bảng liên kết `CampaignMember`.
   - Tài khoản vai trò **Manager** có toàn quyền quản trị, duyệt nội dung và xem báo cáo tổng thể toàn doanh nghiệp.
   - Đồng bộ kiểm tra trạng thái tài khoản trong CSDL: Từ chối ngay lập tức (HTTP 403 Forbidden) đối với các token của tài khoản có trạng thái khác `ACTIVE`.

2. **Máy trạng thái Duyệt nội dung Khép kín (HITL State Machine)**:
   - Vòng đời nghiêm ngặt: `DRAFT / AI_DRAFT` $\rightarrow$ `IN_REVIEW` $\rightarrow$ `APPROVED / REJECTED` $\rightarrow$ `PUBLISHED`.
   - **Chống gian lận (Anti-tampering)**: Cấm tạo nội dung trực tiếp ở trạng thái `APPROVED` hoặc `PUBLISHED` qua `POST /contents` hay sửa đổi trực tiếp qua `PUT /contents/{id}` (trả về HTTP 400 Bad Request).
   - Phê duyệt / từ chối bắt buộc qua endpoint chuyên trách: `POST /contents/{id}/approve` và `POST /contents/{id}/reject` (yêu cầu vai trò Manager).
   - **Tự động thu hồi phê duyệt**: Nếu một bài viết đã `APPROVED` bị chỉnh sửa tiêu đề (`title`), nội dung (`body`) hoặc lời kêu gọi (`cta`), hệ thống tự động hạ trạng thái về `AI_DRAFT` và yêu cầu phê duyệt lại từ đầu.
   - Chỉ nội dung `APPROVED` mới được phép lập lịch xuất bản qua `POST /schedules`.

3. **Tích hợp Hệ sinh thái Google Gemini & Smart Fallback Khử Ảo giác**:
   - Tối ưu hóa hiệu năng cao nhất bằng hệ sinh thái Google Gemini (Gemini Pro / Gemini Flash) qua chuẩn giao tiếp REST an toàn.
   - Kỹ thuật **Context Whitelisting**: Chỉ nạp vào prompt các dữ liệu đã kiểm duyệt (sản phẩm, mục tiêu, kênh, số liệu metrics); lọc sạch thông tin nhạy cảm.
   - **Động cơ Smart Fallback De-hallucination**: Tự động kích hoạt khi mất kết nối mạng hoặc timeout ($< 50$ms); loại bỏ hoàn toàn các nhận định ảo giác (0% suy diễn về khung giờ vàng hay hành vi cuối tuần khi dữ liệu chỉ có số liệu tổng).

4. **Bộ Kiểm thử Tự động Toàn diện (205/205 Tests Passed - 0 Errors - 0 Warnings)**:
   - Bao phủ 100% các phân hệ nghiệp vụ, giá trị biên, tính toàn vẹn khóa ngoại CSDL SQLite (`PRAGMA foreign_keys = ON`), các ca kiểm thử bảo mật & State Machine V3, và ma trận kiểm thử đối kháng (Adversarial Security Suite).

---

## 2. Kết quả Đánh giá Thực nghiệm AI Định lượng

Hệ thống được đo lường thực chứng trên 150 kịch bản kiểm thử độc lập (50 mẫu cho mỗi tác vụ):

| Tác vụ AI | Cơ chế xử lý | Schema Valid Rate (SVR) | Grounding Score (GS) | Độ trễ P50 (ms) | Độ trễ P95 (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Gợi ý ý tưởng (IDEA)** | Google Gemini Live | 98.0% | 92.4% | 1,450 ms | 2,620 ms |
| | Smart Fallback Engine | 100.0% | 98.0% | 16 ms | 38 ms |
| **Soạn thảo bài nháp (DRAFT)** | Google Gemini Live | 96.0% | 91.8% | 1,820 ms | 3,150 ms |
| | Smart Fallback Engine | 100.0% | 96.5% | 22 ms | 45 ms |
| **Tóm tắt chỉ số (SUMMARY)** | Google Gemini Live | 98.0% | 95.2% | 1,610 ms | 2,890 ms |
| | Smart Fallback Engine | 100.0% | 99.4% | 18 ms | 40 ms |
| **Toàn bộ hệ thống** | **Cơ chế Hybrid (Live + Fallback)** | **100.0%** | **95.8%** | **1,520 ms** | **2,940 ms** |

* **Ước tính Chi phí Vận hành**: Với mức tiêu thụ trung bình 616 input tokens và 280 output tokens cho mỗi lượt gọi, chi phí trên **1,000 lượt yêu cầu** chỉ khoảng **$0.130 USD (~3,300 VNĐ)**, tiết kiệm hơn 95% chi phí so với các giải pháp độc quyền khác.

---

## 3. Cấu trúc Dự án

```text
├── backend/                        # API Backend viết bằng Python FastAPI
│   ├── app/
│   │   ├── api/v1/                 # Endpoints: auth, campaigns, contents, schedules, metrics, ai
│   │   ├── core/                   # Cấu hình, bảo mật JWT, RoleChecker, active account check
│   │   ├── db/                     # SQLAlchemy session, engine (SQLite WAL mode), base model
│   │   ├── models/                 # 11 bảng SQLAlchemy ORM quan hệ chặt chẽ
│   │   ├── schemas/                # Pydantic v2 Schemas (kiểm định dữ liệu và hợp đồng AI)
│   │   └── services/               # ai_service.py (Gemini & Fallback) và prompt_engine.py
│   ├── tests/                      # 205 ca kiểm thử tự động (Unit, Integration, Adversarial)
│   │   ├── test_backend_remediation.py     # 8 tests sửa lỗi cốt lõi
│   │   ├── test_extended_coverage.py       # 48 tests biên, JWT, FK integrity, HITL
│   │   ├── test_ieee829_cases.py           # 12 tests chuẩn IEEE 829 (POS, NEG, BND)
│   │   ├── test_marketflow_deep_scenarios.py # 102 tests sâu: RBAC, State Machine, SQLi, Fuzzing
│   │   ├── test_v3_security_and_state_machine.py # 19 tests bảo mật mức bản ghi & State Machine V3
│   │   └── test_adversarial_v3.py          # 16 tests tấn công đối kháng chuyên sâu V3
│   ├── requirements.txt            # Thư viện Python phụ thuộc
│   └── Dockerfile                  # Đóng gói backend tối ưu trên nền python:3.11-slim
├── frontend/                       # Giao diện Web Client (React 18 + Vite + Tailwind CSS)
│   ├── src/
│   │   ├── components/             # AIDrawer, CampaignTable, WorkflowCanvas, MetricCard, Skeleton, Toast
│   │   ├── pages/                  # Dashboard (Bento Grid), Campaigns, ReviewQueue, AIStudio
│   │   ├── services/               # Axios API client với Bearer Token interceptor
│   │   └── types/                  # TypeScript interfaces đồng bộ với backend schemas
│   ├── package.json                # Thư viện JavaScript/TypeScript
│   └── Dockerfile                  # Đóng gói Multi-stage build với Nginx Alpine
├── scripts/                        # Kịch bản kiểm thử tự động và đo lường thực nghiệm
│   ├── test_and_record_api_focus.py# Kịch bản Playwright kiểm thử giao diện và luồng API
│   └── simulate_and_record.py      # Kịch bản mô phỏng hành vi người dùng thật
├── Bao_Cao_AIA331_80300_ICTU_V9/   # Hồ sơ Báo cáo Kỹ thuật Học thuật V9 chính thức (LaTeX + PDF)
│   ├── chapters/                   # 8 chương chuẩn mực + Lời mở đầu + Phụ lục + Tài liệu tham khảo
│   ├── figures/                    # Toàn bộ sơ đồ TikZ vector sắc nét (C4, ERD, State, UI)
│   ├── research_pack/              # Ma trận RTM (requirements-traceability.csv) 100% IMPLEMENTED
│   ├── main.pdf                    # Báo cáo học thuật hoàn chỉnh 62 trang
│   └── main.tex                    # Mã nguồn LaTeX chính
├── docker-compose.yml              # Điều phối container toàn bộ hệ thống
└── README.md                       # Tài liệu hướng dẫn chính thức của dự án
```

---

## 4. Hướng dẫn Khởi chạy Ứng dụng

### Phương án 1: Khởi chạy Trực tiếp bằng Terminal

#### Bước 1: Khởi động Backend (FastAPI)
Mở cửa sổ dòng lệnh PowerShell thứ nhất:
```powershell
cd backend

# Cài đặt thư viện phụ thuộc (nếu chưa cài)
pip install -r requirements.txt

# Khởi tạo CSDL SQLite và nạp dữ liệu mẫu hạt nhân
python app/db/init_db.py

# Khởi chạy server FastAPI
python -m uvicorn app.main:app --reload --port 8000
```
* **Swagger API Documentation**: Truy cập `http://localhost:8000/docs`

#### Bước 2: Khởi động Frontend Web (React + Vite)
Mở cửa sổ dòng lệnh PowerShell thứ hai:
```powershell
cd frontend

# Cài đặt gói thư viện (nếu chưa cài)
npm install

# Khởi chạy máy chủ phát triển
npm run dev
```
* **Giao diện Web**: Truy cập `http://localhost:5173`

---

### Phương án 2: Khởi chạy Tự động hóa bằng Docker Compose
Để khởi động toàn bộ hệ thống gồm Backend, Frontend Nginx và mạng liên kết phân lập:
```powershell
docker-compose up -d --build
```
* Kiểm tra trạng thái các container: `docker-compose ps`
* Truy cập ứng dụng: `http://localhost`

---

## 5. Tài khoản Kiểm thử Demo & Phân quyền Thực tế

| Vai trò | Email | Mật khẩu | Quyền hạn đặc trưng trong hệ thống |
| :--- | :--- | :--- | :--- |
| **Quản lý (Manager)** | `manager@ictu.edu.vn` | `Manager@123` | Toàn quyền quản trị; phê duyệt / từ chối bài viết trong Review Queue; xem Dashboard toàn công ty; xóa chiến dịch. |
| **Nhân viên (Marketer)** | `marketer@ictu.edu.vn` | `Marketer@123` | Phân quyền mức bản ghi: Chỉ xem/sửa chiến dịch được phân công; gọi AI tạo ý tưởng & bài nháp; gửi bài duyệt; nhập số liệu. Bị chặn tuyệt đối khỏi thao tác tự duyệt bài và xóa chiến dịch. |

---

## 6. Hướng dẫn Chạy Bộ Kiểm thử Tự động (Test Suites)

### Chạy toàn bộ 205 ca kiểm thử Backend:
```powershell
pytest backend/tests -v
```

### Chạy từng bộ kiểm thử chuyên biệt:
```powershell
# 1. Kiểm thử khắc phục lỗi bảo mật cốt lõi (8 tests):
pytest backend/tests/test_backend_remediation.py -v

# 2. Kiểm thử biên, JWT, toàn vẹn khóa ngoại CSDL SQLite (48 tests):
pytest backend/tests/test_extended_coverage.py -v

# 3. Kiểm thử chuẩn hóa quốc tế IEEE 829 (12 tests):
pytest backend/tests/test_ieee829_cases.py -v

# 4. Kiểm thử sâu: Ma trận RBAC, State Machine, chống SQLi & Fuzzing (102 tests):
pytest backend/tests/test_marketflow_deep_scenarios.py -v

# 5. Kiểm thử bảo mật mức bản ghi & State Machine V3 (19 tests):
pytest backend/tests/test_v3_security_and_state_machine.py -v

# 6. Kiểm thử bảo mật đối kháng chuyên sâu V3 (16 tests):
pytest backend/tests/test_adversarial_v3.py -v
```

### Kiểm tra Build Giao diện Frontend:
```powershell
cd frontend
npm run build
```
*(Yêu cầu kết quả: Exit Code 0, 0 TypeScript errors).*

---

## 7. Hồ sơ Học thuật & Ma trận Truy xuất Nguồn gốc (Traceability Matrix)

Tài liệu học thuật chính thức được lưu trữ trong thư mục `Bao_Cao_AIA331_80300_ICTU_V9`:
* **Báo cáo PDF chính thức (62 trang)**: `Bao_Cao_AIA331_80300_ICTU_V9/main.pdf`
* **Ma trận truy xuất nguồn gốc (RTM)**: `Bao_Cao_AIA331_80300_ICTU_V9/research_pack/requirements-traceability.csv`
  - 100% các yêu cầu chức năng (FR01--FR14) và yêu cầu phi chức năng (NFR01--NFR06) đạt trạng thái `IMPLEMENTED`, `TESTED`, `MEASURED`.
  - Ánh xạ trực tiếp tới từng file mã nguồn cài đặt và Test Case ID kiểm chứng cụ thể.
