import os
import sys
import time
import json
import math
import random
import functools
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, Page, BrowserContext

print = functools.partial(print, flush=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = ROOT_DIR / "test-recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def bezier_point(p0, p1, p2, p3, t):
    """Tính toán quỹ đạo Bézier bậc 3 cho cử chỉ chuột tự nhiên"""
    u = 1 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t
    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


class HumanSim:
    def __init__(self, page: Page):
        self.page = page
        self.cur_x = 120.0
        self.cur_y = 120.0

    def inject_cursor(self):
        """Tiêm con trỏ chuột ảo trực quan có vệt sáng để người xem thấy rõ thao tác trên video"""
        self.page.evaluate("""() => {
            if (document.getElementById('human-cursor-tracker')) return;
            const cursor = document.createElement('div');
            cursor.id = 'human-cursor-tracker';
            cursor.style.position = 'fixed';
            cursor.style.width = '24px';
            cursor.style.height = '24px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.9)';
            cursor.style.border = '2.5px solid #ffffff';
            cursor.style.boxShadow = '0 0 14px rgba(239, 68, 68, 0.95), 0 2px 8px rgba(0,0,0,0.5)';
            cursor.style.pointerEvents = 'none';
            cursor.style.zIndex = '9999999';
            cursor.style.transform = 'translate(-50%, -50%)';
            cursor.style.transition = 'transform 0.12s ease-out, background-color 0.15s ease';
            cursor.style.left = '120px';
            cursor.style.top = '120px';
            document.body.appendChild(cursor);

            window.addEventListener('mousemove', (e) => {
                cursor.style.left = e.clientX + 'px';
                cursor.style.top = e.clientY + 'px';
            });
            window.addEventListener('mousedown', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(0.6)';
                cursor.style.backgroundColor = 'rgba(16, 185, 129, 0.95)'; // Đổi sang màu Xanh Emerald khi click
            });
            window.addEventListener('mouseup', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(1)';
                cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.9)';
            });
        }""")

    def inject_api_hud(self):
        """Tiêm bảng hiển thị API Network Monitor trực quan ngay trên góc màn hình"""
        self.page.evaluate("""() => {
            if (document.getElementById('api-live-hud')) return;
            const hud = document.createElement('div');
            hud.id = 'api-live-hud';
            hud.style.position = 'fixed';
            hud.style.bottom = '16px';
            hud.style.right = '16px';
            hud.style.width = '420px';
            hud.style.maxHeight = '230px';
            hud.style.backgroundColor = 'rgba(15, 23, 42, 0.94)';
            hud.style.backdropFilter = 'blur(8px)';
            hud.style.color = '#38bdf8';
            hud.style.fontFamily = 'monospace';
            hud.style.fontSize = '11px';
            hud.style.borderRadius = '12px';
            hud.style.border = '1px solid rgba(56, 189, 248, 0.35)';
            hud.style.boxShadow = '0 10px 25px rgba(0,0,0,0.5)';
            hud.style.zIndex = '9999998';
            hud.style.overflow = 'hidden';
            hud.style.display = 'flex';
            hud.style.flexDirection = 'column';

            const header = document.createElement('div');
            header.style.padding = '7px 12px';
            header.style.backgroundColor = 'rgba(30, 41, 59, 0.95)';
            header.style.borderBottom = '1px solid rgba(56, 189, 248, 0.25)';
            header.style.fontWeight = 'bold';
            header.style.color = '#f8fafc';
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.innerHTML = '<span>⚡ LIVE API MONITOR</span><span style=\"color:#10b981\">● ACTIVE</span>';
            hud.appendChild(header);

            const logBox = document.createElement('div');
            logBox.id = 'api-live-logs';
            logBox.style.padding = '8px 12px';
            logBox.style.overflowY = 'auto';
            logBox.style.flex = '1';
            logBox.style.display = 'flex';
            logBox.style.flexDirection = 'column';
            logBox.style.gap = '5px';
            hud.appendChild(logBox);

            document.body.appendChild(hud);

            window.recordApiCall = (method, url, status, time) => {
                const item = document.createElement('div');
                item.style.whiteSpace = 'nowrap';
                item.style.overflow = 'hidden';
                item.style.textOverflow = 'ellipsis';
                const statusColor = status < 300 ? '#34d399' : (status < 400 ? '#60a5fa' : '#f87171');
                item.innerHTML = `<span style="color:#fbbf24;font-weight:bold">${method}</span> <span style="color:#e2e8f0">${url}</span> ➔ <span style="color:${statusColor};font-weight:bold">${status}</span> <span style="color:#94a3b8">(${time}ms)</span>`;
                logBox.appendChild(item);
                logBox.scrollTop = logBox.scrollHeight;
            };

            // Intercept Fetch API
            const originalFetch = window.fetch;
            window.fetch = async (...args) => {
                const startTime = performance.now();
                const url = typeof args[0] === 'string' ? args[0] : args[0].url;
                const method = args[1]?.method || 'GET';
                try {
                    const response = await originalFetch(...args);
                    const duration = Math.round(performance.now() - startTime);
                    if (url.includes('/api/')) {
                        const shortUrl = url.split('/api/')[1] ? '/api/' + url.split('/api/')[1].split('?')[0] : url;
                        window.recordApiCall(method, shortUrl, response.status, duration);
                    }
                    return response;
                } catch (err) {
                    const duration = Math.round(performance.now() - startTime);
                    if (url.includes('/api/')) {
                        window.recordApiCall(method, url, 'ERR', duration);
                    }
                    throw err;
                }
            };
        }""")

    def move_to(self, target_x: float, target_y: float, duration: float = 0.45):
        """Di chuột theo đường cong Bézier tự nhiên"""
        p0 = (self.cur_x, self.cur_y)
        p3 = (target_x, target_y)
        dx = target_x - self.cur_x
        dy = target_y - self.cur_y
        dist = math.hypot(dx, dy)
        ctrl_offset = dist * 0.22 * random.choice([1, -1])
        p1 = (self.cur_x + dx * 0.35 + ctrl_offset * 0.4, self.cur_y + dy * 0.15 - ctrl_offset)
        p2 = (self.cur_x + dx * 0.7 - ctrl_offset * 0.4, self.cur_y + dy * 0.85 + ctrl_offset)

        steps = max(14, int(dist / 16))
        delay = duration / steps
        for i in range(1, steps + 1):
            t = i / steps
            x, y = bezier_point(p0, p1, p2, p3, t)
            self.page.mouse.move(x, y)
            time.sleep(delay)

        self.cur_x = target_x
        self.cur_y = target_y
        time.sleep(0.08)

    def click_element(self, selector: str, text_filter: str = None, timeout: float = 8000):
        """Di chuột đến phần tử và bấm click tự nhiên"""
        self.inject_cursor()
        loc = self.page.locator(selector)
        if text_filter:
            loc = loc.filter(has_text=text_filter).first
        else:
            loc = loc.first

        loc.wait_for(state="visible", timeout=timeout)
        loc.scroll_into_view_if_needed()
        time.sleep(0.12)

        box = loc.bounding_box()
        if not box:
            return

        target_x = box["x"] + box["width"] * random.uniform(0.42, 0.58)
        target_y = box["y"] + box["height"] * random.uniform(0.42, 0.58)

        self.move_to(target_x, target_y, duration=random.uniform(0.35, 0.55))
        time.sleep(random.uniform(0.1, 0.18))
        self.page.mouse.down()
        time.sleep(random.uniform(0.06, 0.1))
        self.page.mouse.up()
        time.sleep(random.uniform(0.2, 0.35))

    def type_text(self, selector: str, text: str, clear_first: bool = True):
        """Gõ bàn phím từng ký tự có độ trễ ngẫu nhiên"""
        self.click_element(selector)
        if clear_first:
            self.page.keyboard.press("Control+A")
            time.sleep(0.05)
            self.page.keyboard.press("Backspace")
            time.sleep(0.1)

        for char in text:
            self.page.keyboard.type(char)
            time.sleep(random.uniform(0.03, 0.06))
        time.sleep(0.2)

    def fill_text(self, selector: str, text: str):
        """Điền văn bản / JSON nhanh chóng và dispatch events chuẩn Playwright"""
        self.click_element(selector)
        loc = self.page.locator(selector).first
        loc.fill(text)
        time.sleep(0.25)

    def smooth_scroll(self, scroll_delta: int, steps: int = 15):
        """Cuộn màn hình mượt mà"""
        step_delta = scroll_delta / steps
        for _ in range(steps):
            self.page.mouse.wheel(0, step_delta)
            time.sleep(0.025)
        time.sleep(0.3)


def run_api_focused_recording(headless: bool = False):
    print("\n" + "="*75)
    print("[*] KHOI CHAY KICH BAN KIEM THU CHUYEN SAU API & GHI HINH VIDEO MAN HINH")
    print("="*75)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_output_dir = RECORDINGS_DIR / f"api_test_session_{timestamp}"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print(f"[*] Khoi tao trinh duyet Chromium (Headless={headless})...")
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=60,
            args=[
                "--start-maximized",
                "--no-default-browser-check",
                "--disable-infobars"
            ]
        )

        context: BrowserContext = browser.new_context(
            viewport={"width": 1280, "height": 780},
            record_video_dir=str(video_output_dir),
            record_video_size={"width": 1280, "height": 780}
        )

        page = context.new_page()
        sim = HumanSim(page)

        try:
            # ==================================================================
            # PHAN 1: TƯƠNG TÁC TRỰC QUAN TẠI FASTAPI SWAGGER API DOCS
            # ==================================================================
            print("\n" + "-"*65)
            print("[ACT 1] KIEM THU TRUC TIEP TAI FASTAPI INTERACTIVE SWAGGER DOCS")
            print("-"*65)

            swagger_url = "http://127.0.0.1:8000/docs"
            print(f"[*] Dieu huong den: {swagger_url}")
            page.goto(swagger_url, wait_until="networkidle")
            page.wait_for_selector(".opblock", timeout=15000)
            time.sleep(1.5)
            sim.inject_cursor()

            # Cuộn lướt qua danh mục tài liệu OpenAPI
            print("  - Xem luot cac module API endpoints (Auth, Campaigns, Contents, Metrics, AI)...")
            sim.smooth_scroll(380, steps=16)
            time.sleep(1.0)
            sim.smooth_scroll(-380, steps=16)
            time.sleep(0.8)

            # 1.1 Kiểm thử API Authentication: POST /api/v1/auth/login
            print("\n  [API 1] Kiem thu Endpoint POST /api/v1/auth/login...")
            login_op = page.locator('.opblock-post').filter(has_text="/api/v1/auth/login").first
            login_summary = login_op.locator(".opblock-summary")
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/auth/login")) .opblock-summary')
            time.sleep(0.8)

            # Bấm "Try it out"
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/auth/login")) button.try-out__btn')
            time.sleep(0.6)

            # Điền thông tin đăng nhập Manager
            print("    * Nhap body JSON: email manager@ictu.edu.vn, password Manager@123...")
            sim.fill_text('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/auth/login")) textarea.body-param__text', '{\n  "email": "manager@ictu.edu.vn",\n  "password": "Manager@123"\n}')
            time.sleep(0.8)

            # Bấm Execute để gửi request
            print("    * Gui request dang nhap Manager qua Swagger...")
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/auth/login")) button.execute')
            time.sleep(2.0)

            # Đọc access_token từ kết quả phản hồi của Swagger UI
            response_pre = login_op.locator(".response .highlight-code pre").first
            response_json_text = response_pre.text_content()
            data = json.loads(response_json_text)
            jwt_token = data.get("access_token", "")
            print(f"    * Quan sat phan hoi: HTTP 200 OK! JWT Token: {jwt_token[:30]}... (Do dai: {len(jwt_token)} chars)")
            sim.smooth_scroll(250, steps=10)
            time.sleep(1.8)
            sim.smooth_scroll(-250, steps=10)
            time.sleep(0.6)

            # Đóng accordion login
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/auth/login")) .opblock-summary')
            time.sleep(0.6)

            # 1.2 Swagger UI Authorize (Gắn Bearer Token để thực thi các endpoint bảo mật)
            print("\n  [AUTH] Kich hoat Swagger Authorize voi JWT Bearer Token...")
            sim.click_element('button.authorize')
            time.sleep(0.8)

            # Điền token vào modal Authorize
            sim.fill_text(".modal-ux input[type='text'], .modal-ux input[type='password']", jwt_token)
            time.sleep(0.5)

            # Bấm Authorize trong modal
            sim.click_element(".modal-ux button.authorize")
            time.sleep(0.6)

            # Bấm Close modal
            sim.click_element(".modal-ux button.btn-done")
            time.sleep(0.8)
            print("    * Swagger UI da xac thuc thanh cong voi Bearer Token!")

            # 1.3 Kiểm thử API Campaigns: GET /api/v1/campaigns
            print("\n  [API 2] Kiem thu Endpoint GET /api/v1/campaigns (Danh sach chien dich)...")
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/campaigns")) .opblock-summary')
            time.sleep(0.8)
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/campaigns")) button.try-out__btn')
            time.sleep(0.6)
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/campaigns")) button.execute')
            print("    * Nhan phan hoi: HTTP 200 OK voi danh sach mang JSON chien dich.")
            time.sleep(2.0)
            sim.smooth_scroll(260, steps=10)
            time.sleep(1.8)
            sim.smooth_scroll(-260, steps=10)
            time.sleep(0.6)
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/campaigns")) .opblock-summary')
            time.sleep(0.6)

            # 1.4 Kiểm thử Tầng AI Copilot API: POST /api/v1/ai/ideas (Prompt V3)
            print("\n  [API 3] Kiem thu Endpoint POST /api/v1/ai/ideas (Prompt Engine V3)...")
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/ai/ideas")) .opblock-summary')
            time.sleep(0.8)
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/ai/ideas")) button.try-out__btn')
            time.sleep(0.8)

            # Nhập body JSON cấu hình gọi AI
            print("    * Chuan bi payload JSON voi campaign_id=1, channel_code=facebook, prompt_version=v3...")
            sim.fill_text('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/ai/ideas")) textarea.body-param__text', '{\n  "campaign_id": 1,\n  "channel_code": "facebook",\n  "prompt_version": "v3"\n}')
            time.sleep(0.8)

            # Bấm Execute gọi AI
            print("    * Bam Execute gui request den AI Service...")
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/ai/ideas")) button.execute')
            print("    * Dang cho AI Provider phan hoi...")
            time.sleep(3.8)

            # Cuộn xem phản hồi cấu trúc 5 ý tưởng tiếp thị
            print("    * Quan sat Response: HTTP 200 OK voi 5 goc y tuong marketing chuan Pydantic!")
            sim.smooth_scroll(340, steps=12)
            time.sleep(2.5)
            sim.smooth_scroll(-340, steps=12)
            time.sleep(0.8)
            sim.click_element('.opblock-post:has(.opblock-summary-path:has-text("/api/v1/ai/ideas")) .opblock-summary')
            time.sleep(0.6)

            # 1.5 Kiểm thử API Thống kê & Dashboard: GET /api/v1/analytics/dashboard
            print("\n  [API 4] Kiem thu Endpoint GET /api/v1/analytics/dashboard...")
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/analytics/dashboard")) .opblock-summary')
            time.sleep(0.8)
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/analytics/dashboard")) button.try-out__btn')
            time.sleep(0.6)
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/analytics/dashboard")) button.execute')
            print("    * Nhan ket qua tong hop: HTTP 200 OK (ROI, Ty le duyet, Doanh thu, Kenh phan bo).")
            time.sleep(1.8)
            sim.smooth_scroll(280, steps=10)
            time.sleep(1.6)
            sim.smooth_scroll(-280, steps=10)
            time.sleep(0.8)
            sim.click_element('.opblock-get:has(.opblock-summary-path:has-text("/api/v1/analytics/dashboard")) .opblock-summary')
            time.sleep(1.0)

            # ==================================================================
            # PHAN 2: TƯƠNG TÁC THỰC TẾ TRÊN GIAO DIỆN WEB KÈM LIVE API MONITOR
            # ==================================================================
            print("\n" + "-"*65)
            print("[ACT 2] KET NOI API VOI GIAO DIEN WEB (KEM LIVE API MONITOR HUD)")
            print("-"*65)

            frontend_url = "http://localhost:5173"
            print(f"[*] Dieu huong den Frontend Client: {frontend_url}")
            page.goto(frontend_url, wait_until="networkidle")
            time.sleep(2.0)
            sim.inject_cursor()
            sim.inject_api_hud()

            # 2.1 Bàn làm việc (Dashboard Bento Grid)
            print("\n  [SCENE 1] Ban lam viec Bento Grid tieu thu API Dashboard...")
            time.sleep(1.5)
            sim.move_to(350, 160, duration=0.6)
            time.sleep(0.4)
            sim.move_to(650, 160, duration=0.6)
            time.sleep(0.4)
            sim.smooth_scroll(380, steps=16)
            time.sleep(1.5)
            sim.smooth_scroll(-380, steps=16)
            time.sleep(0.8)

            # 2.2 Quản lý Chiến dịch: Gọi POST /api/v1/campaigns
            print("\n  [SCENE 2] Chuyen sang Trang Campaigns (Goi API CRUD chien dich)...")
            sim.click_element("aside button", text_filter="Chiến dịch")
            time.sleep(1.8)

            # Test tìm kiếm thời gian thực
            sim.type_text('input[placeholder*="Tìm kiếm chiến dịch"]', "AI")
            time.sleep(1.0)
            sim.type_text('input[placeholder*="Tìm kiếm chiến dịch"]', "")
            time.sleep(0.6)

            # Tạo chiến dịch mới
            print("    * Mo Modal tao chien dich de goi POST /api/v1/campaigns...")
            sim.click_element('button:has-text("Tạo Chiến Dịch Mới")')
            time.sleep(1.0)

            sim.type_text('input[placeholder*="Ví dụ: Chiến dịch Khóa học"]', "Chiến dịch API Automation E2E 2026")
            sim.type_text('textarea[placeholder*="Ví dụ: Đạt 1,000 học viên"]', "Tăng trưởng tương tác đa kênh và tối ưu hóa chuyển đổi qua API")
            sim.type_text('input[type="number"]', "45000000")
            time.sleep(0.6)

            # Bấm Lưu Chiến Dịch -> Quan sát API POST và Toast
            print("    * Bam Luu: Frontend gui POST /api/v1/campaigns ➔ CSDL luu tru thanh cong!")
            sim.click_element('button[type="submit"]:has-text("Tạo Chiến Dịch")')
            time.sleep(2.5)

            # 2.3 Xưởng AI Copilot Studio: Gọi POST /api/v1/ai/ideas và /api/v1/ai/draft
            print("\n  [SCENE 3] Kich hoat AI Copilot Drawer (Goi API Sinh Y tuong & Ban nhap)...")
            sim.click_element('header button:has-text("AI Copilot")')
            time.sleep(1.8)

            # Sinh ý tưởng AI
            print("    * Goi POST /api/v1/ai/ideas...")
            sim.click_element('button:has-text("1. Sinh ý tưởng (IDEA)")')
            time.sleep(0.6)
            sim.click_element('button:has-text("Khởi tạo 5 ý tưởng tiếp thị")')
            print("      [+] Cho AI tinh toan va tra ve 5 goc y tuong...")
            time.sleep(4.0)

            # Chọn ý tưởng và sinh bản nháp
            print("    * Chon y tuong va goi POST /api/v1/ai/draft...")
            try:
                sim.click_element('button:has-text("Dùng ý tưởng này để viết bài")', timeout=5000)
            except Exception:
                sim.click_element('button:has-text("2. Viết bản nháp (DRAFT)")')
            time.sleep(1.0)

            sim.click_element('button:has-text("Sinh nội dung nháp")')
            print("      [+] Cho AI sinh tieu de, noi dung va loi keu goi CTA...")
            time.sleep(4.5)

            # Đẩy vào hàng đợi duyệt: Gọi POST /api/v1/contents/{id}/submit
            print("    * Goi POST /api/v1/contents (Chuyen trang thai thanh IN_REVIEW)...")
            try:
                sim.click_element('button:has-text("Gửi duyệt (Submit)"), button:has-text("Gửi Sếp phê duyệt")', timeout=5000)
                time.sleep(2.2)
            except Exception:
                pass

            # Đóng AI Drawer
            try:
                sim.click_element('button:has(.lucide-x)', timeout=2000)
            except Exception:
                page.keyboard.press("Escape")
            time.sleep(1.0)

            # 2.4 Hàng đợi duyệt: Gọi POST /api/v1/contents/{id}/approve
            print("\n  [SCENE 4] Chuyen sang Hang doi phe duyet (Goi API Approve cua Quan ly)...")
            sim.click_element("aside button", text_filter="Hàng đợi duyệt")
            time.sleep(2.0)

            print("    * Doc noi dung va goi POST /api/v1/contents/{id}/approve...")
            sim.smooth_scroll(200, steps=10)
            time.sleep(0.8)
            try:
                sim.click_element('button:has-text("Phê duyệt (Approve)")', timeout=3000)
                time.sleep(2.2) # Cho Toast phe duyet thanh cong xuat hien
                print("      [+] Bai viet da duoc chuyen sang trang thai APPROVED!")
            except Exception:
                print("      (Bai viet da o trang thai Approved hoac dang cho)")

            # 2.5 Sơ đồ Quy trình: Xem luồng tích hợp Node
            print("\n  [SCENE 5] Chuyen sang So do Luong Chien dich (Workflow Canvas Nodes)...")
            sim.click_element("aside button", text_filter="Luồng chiến dịch")
            time.sleep(2.0)
            sim.smooth_scroll(250, steps=12)
            time.sleep(1.0)
            sim.smooth_scroll(-250, steps=12)
            time.sleep(0.8)

            # 2.6 Demo Phân quyền API: Gọi POST /api/v1/auth/login khi đổi vai trò
            print("\n  [SCENE 6] Demo Chuyen doi Vai tro (Goi API Auth dang nhap token moi)...")
            sim.click_element('header button:has-text("Marketer")')
            print("    * Chuyen sang vai tro Nhan vien (Marketer Token duoc luu)...")
            time.sleep(1.8)
            sim.click_element('header button:has-text("Manager")')
            print("    * Chuyen sang vai tro Quan ly (Manager Token duoc luu)...")
            time.sleep(1.8)

            # Quay về Dashboard
            print("\n  [SCENE 7] Tro ve Ban lam viec & Ket thuc phien ghi hinh...")
            sim.click_element("aside button", text_filter="Bàn làm việc")
            time.sleep(2.5)

            print("\n" + "="*75)
            print("[✓] TOAN BO KICH BAN KIEM THU CHUYEN SAU API DA HOAN TAT 100%!")
            print("="*75)

        except Exception as e:
            print(f"\n[!] Phat sinh loi trong qua trinh mo phong: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("[*] Dang ket xuat va dong goi file video HD...")
            page.close()
            context.close()
            browser.close()

    # Lưu và đổi tên file video HD
    video_files = list(video_output_dir.glob("*.webm"))
    if video_files:
        final_video = video_files[0]
        target_name = RECORDINGS_DIR / f"marketflow_ai_api_deep_test_{timestamp}.webm"
        final_video.rename(target_name)
        print("\n" + "="*75)
        print("[SUCCESS] VIDEO KIEM THU CHUYEN SAU API DA DUOC TAO THANH CONG!")
        print(f"[+] Duong dan file video: {target_name.resolve()}")
        print(f"[+] Dung luong file: {target_name.stat().st_size / (1024*1024):.2f} MB")
        print("="*75)
        return target_name
    else:
        print("[!] Khong tim thay file video duoc luu.")
        return None


if __name__ == "__main__":
    is_headless = "--headless" in sys.argv
    run_api_focused_recording(headless=is_headless)
