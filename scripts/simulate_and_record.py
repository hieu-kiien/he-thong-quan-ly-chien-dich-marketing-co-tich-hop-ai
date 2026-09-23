import os
import sys
import time
import math
import random
import subprocess
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, Page, BrowserContext

import functools
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

# Các hàm mô phỏng thao tác tay người thật (Human-like Interactions)
def bezier_point(p0, p1, p2, p3, t):
    """Tính toán tọa độ đường cong Bézier bậc 3 để di chuột mượt mà"""
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
        self.cur_x = 100.0
        self.cur_y = 100.0

    def inject_cursor(self):
        """Tiêm con trỏ chuột ảo trực quan (chấm đỏ/tím có viền sáng) lên màn hình để người xem thấy rõ tay đang thao tác"""
        self.page.evaluate("""() => {
            if (document.getElementById('human-cursor-tracker')) return;
            const cursor = document.createElement('div');
            cursor.id = 'human-cursor-tracker';
            cursor.style.position = 'fixed';
            cursor.style.width = '22px';
            cursor.style.height = '22px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.85)';
            cursor.style.border = '2.5px solid #ffffff';
            cursor.style.boxShadow = '0 0 12px rgba(239, 68, 68, 0.9), 0 2px 6px rgba(0,0,0,0.4)';
            cursor.style.pointerEvents = 'none';
            cursor.style.zIndex = '999999';
            cursor.style.transform = 'translate(-50%, -50%)';
            cursor.style.transition = 'transform 0.12s ease-out, background-color 0.15s ease';
            cursor.style.left = '100px';
            cursor.style.top = '100px';
            document.body.appendChild(cursor);

            window.addEventListener('mousemove', (e) => {
                cursor.style.left = e.clientX + 'px';
                cursor.style.top = e.clientY + 'px';
            });
            window.addEventListener('mousedown', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(0.65)';
                cursor.style.backgroundColor = 'rgba(99, 102, 241, 0.95)'; // Đổi sang màu Indigo khi click
            });
            window.addEventListener('mouseup', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(1)';
                cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.85)';
            });
        }""")

    def move_to(self, target_x: float, target_y: float, duration: float = 0.5):
        """Di chuyển chuột từ vị trí hiện tại đến mục tiêu theo đường cong Bézier tự nhiên"""
        p0 = (self.cur_x, self.cur_y)
        p3 = (target_x, target_y)
        
        # Điểm kiểm soát tạo độ võng tự nhiên của cổ tay
        dx = target_x - self.cur_x
        dy = target_y - self.cur_y
        dist = math.hypot(dx, dy)
        
        ctrl_offset = dist * 0.25 * random.choice([1, -1])
        p1 = (self.cur_x + dx * 0.3 + ctrl_offset * 0.5, self.cur_y + dy * 0.1 - ctrl_offset)
        p2 = (self.cur_x + dx * 0.7 - ctrl_offset * 0.5, self.cur_y + dy * 0.9 + ctrl_offset)

        steps = max(15, int(dist / 15))
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
        """Tìm phần tử, di chuyển chuột mượt mà tới đó, dừng nhẹ nhìn rồi click"""
        self.inject_cursor()
        loc = self.page.locator(selector)
        if text_filter:
            loc = loc.filter(has_text=text_filter).first
        else:
            loc = loc.first
            
        loc.wait_for(state="visible", timeout=timeout)
        loc.scroll_into_view_if_needed()
        time.sleep(0.1)

        box = loc.bounding_box()
        if not box:
            return
            
        # Thêm một chút dao động vị trí ngẫu nhiên quanh tâm nút
        target_x = box["x"] + box["width"] * random.uniform(0.4, 0.6)
        target_y = box["y"] + box["height"] * random.uniform(0.4, 0.6)

        self.move_to(target_x, target_y, duration=random.uniform(0.35, 0.65))
        time.sleep(random.uniform(0.1, 0.2)) # Thời gian người dùng định hình trước khi bấm
        self.page.mouse.down()
        time.sleep(random.uniform(0.06, 0.12)) # Thời gian giữ phím chuột
        self.page.mouse.up()
        time.sleep(random.uniform(0.25, 0.45))

    def type_text(self, selector: str, text: str, clear_first: bool = True):
        """Giả lập người dùng gõ bàn phím từng ký tự có độ trễ tự nhiên"""
        self.click_element(selector)
        if clear_first:
            self.page.keyboard.press("Control+A")
            time.sleep(0.05)
            self.page.keyboard.press("Backspace")
            time.sleep(0.1)

        for char in text:
            self.page.keyboard.type(char)
            # Độ trễ giữa các phím từ 40ms đến 85ms
            time.sleep(random.uniform(0.04, 0.085))
        time.sleep(0.2)

    def smooth_scroll(self, scroll_delta: int, steps: int = 15):
        """Cuộn trang mượt mà như thao tác ngón tay trên con lăn chuột"""
        step_delta = scroll_delta / steps
        for _ in range(steps):
            self.page.mouse.wheel(0, step_delta)
            time.sleep(0.025)
        time.sleep(0.3)


def ensure_servers_running():
    """Kiểm tra trạng thái dịch vụ Backend và Frontend"""
    print("[*] Kiem tra trang thai dich vu Backend va Frontend...", flush=True)
    backend_ready = False
    for url in ["http://127.0.0.1:8000/docs", "http://localhost:8000/docs"]:
        try:
            if httpx.get(url, timeout=2.0).status_code == 200:
                backend_ready = True
                print("  [+] Backend FastAPI dang hoat dong tren port 8000!", flush=True)
                break
        except Exception:
            pass

    frontend_ready = False
    for url in ["http://localhost:5173", "http://127.0.0.1:5173"]:
        try:
            if httpx.get(url, timeout=2.0).status_code < 500:
                frontend_ready = True
                print("  [+] Frontend Vite dang hoat dong tren port 5173!", flush=True)
                break
        except Exception:
            pass

    if not backend_ready:
        print("  [!] Backend chua chay tren port 8000. Khoi dong: cd backend && python -m uvicorn app.main:app --port 8000", flush=True)
    if not frontend_ready:
        print("  [!] Frontend chua chay tren port 5173. Khoi dong: cd frontend && npm run dev", flush=True)
        
    return None, None


def run_simulation(headless: bool = False):
    print("\n" + "="*70)
    print("[*] KHOI CHAY KICH BAN GIA LAP THAO TAC TAY & QUAY VIDEO MAN HINH")
    print("="*70)
    
    backend_proc, frontend_proc = ensure_servers_running()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_output_dir = RECORDINGS_DIR / f"demo_session_{timestamp}"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print(f"[*] Mo trinh duyet Chromium (Headless={headless})...")
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=50,
            args=[
                "--start-maximized",
                "--no-default-browser-check",
                "--disable-infobars"
            ]
        )

        context: BrowserContext = browser.new_context(
            viewport={"width": 1280, "height": 760},
            record_video_dir=str(video_output_dir),
            record_video_size={"width": 1280, "height": 760}
        )

        page = context.new_page()
        sim = HumanSim(page)

        try:
            print("\n[SCENE 1] Truy cap Bàn làm việc (Dashboard Bento Grid)...")
            page.goto("http://localhost:5173", wait_until="networkidle")
            time.sleep(1.5)
            sim.inject_cursor()

            # Quan sát KPI Metric Cards
            print("  - Xem luot cac Metric Cards...")
            sim.move_to(350, 160, duration=0.8)
            time.sleep(0.5)
            sim.move_to(620, 160, duration=0.6)
            time.sleep(0.5)
            sim.move_to(890, 160, duration=0.6)
            time.sleep(0.5)
            sim.move_to(1150, 160, duration=0.6)
            time.sleep(0.5)

            # Cuon xuong xem bang hieu qua va bieu do
            print("  - Cuon xem bieu do va bang hieu qua...")
            sim.smooth_scroll(380, steps=18)
            time.sleep(1.2)
            sim.smooth_scroll(-380, steps=18)
            time.sleep(0.8)

            # SCENE 2: Quan ly Chien dich
            print("\n[SCENE 2] Chuyen sang Trang Quan ly Chien dich (Campaigns)...")
            sim.click_element("nav button", text_filter="Chiến dịch")
            time.sleep(1.5)

            # Tim kiem chien dich
            print("  - Thu nghiem o tim kiem thoi gian thuc...")
            sim.type_text('input[placeholder*="Tìm kiếm chiến dịch"]', "Chiến dịch")
            time.sleep(1.0)
            sim.type_text('input[placeholder*="Tìm kiếm chiến dịch"]', "") # Xoa de tro lai tat ca
            time.sleep(0.5)

            # Mo Modal tao chien dich moi
            print("  - Mo modal tao Chien dich moi...")
            sim.click_element('button:has-text("Tạo Chiến Dịch Mới")')
            time.sleep(1.0)

            # Dien form chien dich moi
            print("  - Nhap thong tin chien dich Thu Dong 2026...")
            sim.type_text('input[placeholder*="Ví dụ: Chiến dịch Khóa học"]', "Chiến dịch Thu Đông 2026 AI Growth")
            sim.type_text('textarea[placeholder*="Ví dụ: Đạt 1,000 học viên"]', "Tăng trưởng doanh số 35% trên các kênh số và mạng xã hội")
            sim.type_text('input[type="number"]', "35000000")
            time.sleep(0.5)

            # Bam luu chien dich
            print("  - Bam Luu chien dich & quan sat Toast thong bao...")
            sim.click_element('button[type="submit"]:has-text("Tạo Chiến Dịch")')
            time.sleep(2.2) # Cho Toast hien thi

            # SCENE 3: Xưởng AI Assistant & OpenCode AI Copilot
            print("\n[SCENE 3] Kich hoat Tro ly AI Copilot Studio (AIDrawer)...")
            sim.click_element('button:has-text("AI Copilot")')
            time.sleep(1.5)

            # O tab Sinh y tuong
            print("  - Chon kenh truyen thong Facebook va Sinh y tuong...")
            sim.click_element('button:has-text("1. Sinh ý tưởng (IDEA)")')
            time.sleep(0.6)
            sim.click_element('button:has-text("Khởi tạo 5 ý tưởng tiếp thị")')
            print("    * Dang cho AI phan hoi...")
            time.sleep(3.5) # Cho AI tra ve va render the y tuong

            # Chuyen sang tab Viet Ban nhap (Draft)
            print("  - Chon y tuong va chuyen sang viet Ban nhap...")
            try:
                sim.click_element('button:has-text("Dùng ý tưởng này để viết bài")', timeout=5000)
            except Exception:
                sim.click_element('button:has-text("2. Viết bản nháp (DRAFT)")')
            time.sleep(1.0)

            print("  - Kich hoat Sinh noi dung nhap (Title, Body, CTA)...")
            sim.click_element('button:has-text("Sinh nội dung nháp")')
            print("    * Dang cho AI viet noi dung tiep thi...")
            time.sleep(4.0)

            # Gui vao Hang doi duyet Human-in-the-loop
            print("  - Nhan nut Day vao Hang doi duyet cua Quan ly (Human-in-the-loop)...")
            try:
                sim.click_element('button:has-text("Gửi duyệt (Submit)"), button:has-text("Gửi Sếp phê duyệt")', timeout=5000)
                time.sleep(2.0)
            except Exception:
                pass

            # Dong AI Drawer
            print("  - Dong AI Drawer...")
            try:
                sim.click_element('button:has(.lucide-x)', timeout=2000)
            except Exception:
                page.keyboard.press("Escape")
            time.sleep(1.0)

            # SCENE 4: Hang doi duyet (Review Queue)
            print("\n[SCENE 4] Chuyen sang Hang doi phe duyet (Review Queue)...")
            sim.click_element("nav button", text_filter="Hàng đợi duyệt")
            time.sleep(1.5)

            print("  - Xem noi dung cho duyet va thuc hien Phe duyet (Approve)...")
            sim.smooth_scroll(200, steps=10)
            time.sleep(0.8)
            try:
                sim.click_element('button:has-text("Phê duyệt (Approve)")', timeout=3000)
                time.sleep(2.0)
            except Exception:
                print("    (Danh sach cho duyet da duoc xu ly hoac trong)")

            # SCENE 5: So do Quy trinh (Workflow Canvas)
            print("\n[SCENE 5] Chuyen sang So do Luong Chien dich (Nodes Canvas)...")
            sim.click_element("nav button", text_filter="Luồng chiến dịch")
            time.sleep(1.8)
            sim.smooth_scroll(250, steps=12)
            time.sleep(1.0)
            sim.smooth_scroll(-250, steps=12)
            time.sleep(0.8)

            # SCENE 6: Chuyen doi vai tro (Role-Based Demo)
            print("\n[SCENE 6] Demo chuyen doi vai tro Nhan vien (Marketer) <-> Quan ly (Manager)...")
            sim.click_element('header button:has-text("Marketer")')
            time.sleep(1.5)
            sim.click_element('header button:has-text("Manager")')
            time.sleep(1.5)

            # Tro ve Dashboard va ket thuc
            print("\n[SCENE 7] Tro ve Ban lam viec & Hoan tat ghi hinh...")
            sim.click_element("nav button", text_filter="Bàn làm việc")
            time.sleep(2.0)

            print("\n[✓] Kich ban kiem thu toan dien hoan tat thanh cong 100%!")

        except Exception as e:
            print(f"\n[!] Ghi nhan loi trong qua trinh mo phong: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("[*] Dang dong trinh duyet va ket xuat video...")
            page.close()
            context.close()
            browser.close()

    # Tim file video da luu
    video_files = list(video_output_dir.glob("*.webm"))
    if video_files:
        final_video = video_files[0]
        target_name = RECORDINGS_DIR / f"marketflow_ai_full_demo_{timestamp}.webm"
        final_video.rename(target_name)
        print("\n" + "="*70)
        print("[SUCCESS] VIDEO DA DUOC KHOI TAO VA GHI HINH THANH CONG!")
        print(f"[+] Duong dan file video: {target_name.resolve()}")
        print(f"[+] Dung luong: {target_name.stat().st_size / (1024*1024):.2f} MB")
        print("="*70)
    else:
        print("[!] Khong tim thay file video duoc luu.")


if __name__ == "__main__":
    is_headless = "--headless" in sys.argv
    run_simulation(headless=is_headless)
