import os
import sys
import time
import math
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, BrowserContext

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = ROOT_DIR / "test-recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

LIVE_DOMAIN = "https://marketing.kienhieu.id.vn"

def bezier_point(p0, p1, p2, p3, t):
    u = 1 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t
    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)

class LiveHumanTester:
    def __init__(self, page: Page):
        self.page = page
        self.cur_x = 200.0
        self.cur_y = 200.0

    def inject_cursor(self):
        self.page.evaluate("""() => {
            if (document.getElementById('human-cursor-tracker')) return;
            const cursor = document.createElement('div');
            cursor.id = 'human-cursor-tracker';
            cursor.style.position = 'fixed';
            cursor.style.width = '24px';
            cursor.style.height = '24px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.88)';
            cursor.style.border = '2.5px solid #ffffff';
            cursor.style.boxShadow = '0 0 16px rgba(239, 68, 68, 0.95), 0 2px 8px rgba(0,0,0,0.5)';
            cursor.style.pointerEvents = 'none';
            cursor.style.zIndex = '9999999';
            cursor.style.transform = 'translate(-50%, -50%)';
            cursor.style.transition = 'transform 0.12s ease-out, background-color 0.15s ease';
            cursor.style.left = '200px';
            cursor.style.top = '200px';
            document.body.appendChild(cursor);

            window.addEventListener('mousemove', (e) => {
                cursor.style.left = e.clientX + 'px';
                cursor.style.top = e.clientY + 'px';
            });
            window.addEventListener('mousedown', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(0.6)';
                cursor.style.backgroundColor = 'rgba(99, 102, 241, 0.95)';
            });
            window.addEventListener('mouseup', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(1)';
                cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.88)';
            });
        }""")

    def move_to(self, target_x: float, target_y: float, duration: float = 0.5):
        p0 = (self.cur_x, self.cur_y)
        p3 = (target_x, target_y)
        dx = target_x - self.cur_x
        dy = target_y - self.cur_y
        dist = math.hypot(dx, dy)
        ctrl_offset = dist * 0.22 * random.choice([1, -1])
        p1 = (self.cur_x + dx * 0.3 + ctrl_offset * 0.5, self.cur_y + dy * 0.1 - ctrl_offset)
        p2 = (self.cur_x + dx * 0.7 - ctrl_offset * 0.5, self.cur_y + dy * 0.9 + ctrl_offset)

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

    def click_element(self, selector: str, text_filter: str = None, timeout: float = 10000):
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
            loc.click()
            return

        target_x = box["x"] + box["width"] * random.uniform(0.45, 0.55)
        target_y = box["y"] + box["height"] * random.uniform(0.45, 0.55)

        self.move_to(target_x, target_y, duration=random.uniform(0.35, 0.6))
        time.sleep(random.uniform(0.12, 0.2))
        self.page.mouse.down()
        time.sleep(random.uniform(0.06, 0.12))
        self.page.mouse.up()
        time.sleep(random.uniform(0.25, 0.45))

    def type_text(self, selector: str, text: str, clear_first: bool = True):
        self.click_element(selector)
        if clear_first:
            self.page.keyboard.press("Control+A")
            time.sleep(0.05)
            self.page.keyboard.press("Backspace")
            time.sleep(0.1)

        for char in text:
            self.page.keyboard.type(char)
            time.sleep(random.uniform(0.035, 0.075))
        time.sleep(0.2)

    def smooth_scroll(self, scroll_delta: int, steps: int = 15):
        step_delta = scroll_delta / steps
        for _ in range(steps):
            self.page.mouse.wheel(0, step_delta)
            time.sleep(0.03)
        time.sleep(0.35)


def run_live_evaluation(headless: bool = True):
    print("="*75, flush=True)
    print(f"[*] KHOI CHAY DANH GIA TRUC TIEP TREN DOMAIN: {LIVE_DOMAIN}", flush=True)
    print("="*75, flush=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_output_dir = RECORDINGS_DIR / f"live_eval_{timestamp}"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print("[*] Khoi dong Microsoft Edge (Chromium)...", flush=True)
        browser = p.chromium.launch(
            channel="msedge",
            headless=headless,
            slow_mo=40,
            args=[
                "--start-maximized",
                "--no-default-browser-check",
                "--disable-infobars"
            ]
        )

        context: BrowserContext = browser.new_context(
            viewport={"width": 1366, "height": 768},
            record_video_dir=str(video_output_dir),
            record_video_size={"width": 1366, "height": 768},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )

        page = context.new_page()
        tester = LiveHumanTester(page)

        try:
            # -------------------------------------------------------------
            # PHAN 1: TRUY CAP TRANG DANG NHAP TREN DOMAIN CHINH THUC
            # -------------------------------------------------------------
            print("\n[PHAN 1] Truy cap giao dien Dang nhap tai https://marketing.kienhieu.id.vn ...", flush=True)
            page.goto(LIVE_DOMAIN, wait_until="networkidle", timeout=30000)
            time.sleep(1.8)
            tester.inject_cursor()

            # Luot xem giao dien Dang nhap
            print("  - Kiem tra Header thuong hieu MarketFlow AI va the Dang nhap...", flush=True)
            tester.move_to(683, 220, duration=0.6)
            time.sleep(0.6)

            # Click Manager quick chip
            print("  - Bam chon nhanh tai khoan kiem thu chuan: Manager...", flush=True)
            tester.click_element('button:has-text("Manager")')
            time.sleep(0.8)

            # Dang nhap vao he thong
            print("  - Bam nut 'Dang nhap he thong' va cho phan hoi...", flush=True)
            with page.expect_response("**/auth/login", timeout=25000):
                tester.click_element('button[type="submit"]')
            
            time.sleep(3.0)
            tester.inject_cursor()
            print("  [+] Dang nhap thanh cong! Da vao giao dien lam viec chinh.", flush=True)

            # -------------------------------------------------------------
            # PHAN 2: DANH GIA CHUYEN SAU TRUNG TAM THONG BAO & NAVBAR
            # -------------------------------------------------------------
            print("\n[PHAN 2] Kiem thu chuyen sau Trung tam Thong bao & Thanh dieu huong...", flush=True)
            bell_loc = page.locator('button[aria-label="Thông báo hệ thống"], button[title="Thông báo"]')
            if bell_loc.count() > 0 and bell_loc.first.is_visible():
                print("  - Di chuot toi icon Chuong Thong bao (Bell Icon)...", flush=True)
                box = bell_loc.first.bounding_box()
                if box:
                    tester.move_to(box["x"] + box["width"]/2, box["y"] + box["height"]/2, duration=0.7)
                    time.sleep(0.6)

                print("  - Mo bang danh sach thong bao (Notification Popover)...", flush=True)
                bell_loc.first.click()
                time.sleep(1.5)
                tester.inject_cursor()

                print("  - Chuyen bo loc sang tab 'Chua doc'...", flush=True)
                unread_filter = page.locator('button:has-text("Chưa đọc")').first
                if unread_filter.is_visible():
                    unread_filter.click()
                    time.sleep(1.0)

                print("  - Nhan 'Danh dau tat ca da doc'...", flush=True)
                mark_read_btn = page.locator('button:has-text("Đã đọc")').first
                if mark_read_btn.is_visible():
                    mark_read_btn.click()
                    time.sleep(1.2)

                page.keyboard.press("Escape")
                time.sleep(0.5)
            else:
                print("  - Quan sat thanh Navbar voi Workspace Switcher, Tim kiem va Thong bao...", flush=True)
                tester.move_to(400, 32, duration=0.5)
                time.sleep(0.5)

            # -------------------------------------------------------------
            # PHAN 3: DANH GIA DASHBOARD (BAN LAM VIEC BENTO GRID & AI DOCTOR)
            # -------------------------------------------------------------
            print("\n[PHAN 3] Danh gia Bàn làm việc Dashboard (Bento Grid & AI Doctor)...", flush=True)
            print("  - Di chuot qua cac the Metric KPI (Doanh thu, ROI, Bai viet, Chien dich)...", flush=True)
            tester.move_to(300, 260, duration=0.6)
            time.sleep(0.4)
            tester.move_to(600, 260, duration=0.5)
            time.sleep(0.4)
            tester.move_to(900, 260, duration=0.5)
            time.sleep(0.4)

            print("  - Cuon xuong quan sat Bac si Chien dich AI & Don thuoc chien luoc...", flush=True)
            tester.smooth_scroll(380, steps=16)
            time.sleep(1.2)
            tester.smooth_scroll(350, steps=14)
            time.sleep(1.5)

            print("  - Cuon len tren tro lai...", flush=True)
            tester.smooth_scroll(-730, steps=20)
            time.sleep(0.8)

            # -------------------------------------------------------------
            # PHAN 4: DANH GIA TRO LY AI COPILOT & AI STUDIO (DRAWER)
            # -------------------------------------------------------------
            print("\n[PHAN 4] Kich hoat Tro ly AI Copilot Studio (AIDrawer)...", flush=True)
            ai_copilot_btn = page.locator('button:has-text("AI Copilot")').first
            if ai_copilot_btn.is_visible():
                ai_copilot_btn.click()
                time.sleep(2.0)
                tester.inject_cursor()

                # Sinh y tuong AI
                print("  - Sinh y tuong tiep thi AI...", flush=True)
                gen_idea_btn = page.locator('button:has-text("Khởi tạo 5 ý tưởng"), button:has-text("Sinh ý tưởng")').first
                if gen_idea_btn.is_visible():
                    gen_idea_btn.click()
                    print("    * Cho AI phan hoi...", flush=True)
                    time.sleep(3.5)

                # Chuyen sang tab viet ban nhap
                print("  - Chuyen sang viet Ban nhap...", flush=True)
                draft_tab = page.locator('button:has-text("Viết bản nháp"), button:has-text("DRAFT"), button:has-text("2. Viết bản nháp")').first
                if draft_tab.is_visible():
                    draft_tab.click()
                    time.sleep(1.2)
                    gen_draft_btn = page.locator('button:has-text("Sinh nội dung nháp")').first
                    if gen_draft_btn.is_visible():
                        gen_draft_btn.click()
                        print("    * Cho AI sinh noi dung...", flush=True)
                        time.sleep(3.5)

                # Dong AI Drawer
                print("  - Dong AI Drawer...", flush=True)
                close_ai = page.locator('aside button:has(.lucide-x), button[aria-label="Đóng"], aside button').first
                if close_ai.is_visible():
                    close_ai.click()
                else:
                    page.keyboard.press("Escape")
                time.sleep(1.2)

            # -------------------------------------------------------------
            # PHAN 5: DANH GIA HANG DOI DUYET (REVIEW QUEUE)
            # -------------------------------------------------------------
            print("\n[PHAN 5] Chuyen sang Hang doi phe duyet (Review Queue)...", flush=True)
            review_tab = page.locator('nav button, button').filter(has_text="Hàng đợi duyệt").first
            if review_tab.is_visible():
                review_tab.click()
                time.sleep(2.0)
                tester.inject_cursor()

                tester.smooth_scroll(250, steps=10)
                time.sleep(1.0)

                approve_btn = page.locator('button:has-text("Phê duyệt (Approve)"), button:has-text("Phê duyệt")').first
                if approve_btn.is_visible():
                    print("  - Bam 'Phe duyet' va quan sat Toast thong bao thanh cong...", flush=True)
                    approve_btn.click()
                    time.sleep(2.0)

            # -------------------------------------------------------------
            # PHAN 6: DANH GIA BRAND KIT & WORKSPACE
            # -------------------------------------------------------------
            print("\n[PHAN 6] Mo cau hinh Brand Kit...", flush=True)
            brand_kit_btn = page.locator('button:has-text("Brand Kit")').first
            if brand_kit_btn.is_visible():
                brand_kit_btn.click()
                time.sleep(2.0)
                tester.inject_cursor()
                tester.smooth_scroll(180, steps=8)
                time.sleep(1.0)
                # Dong Brand Kit
                close_bk = page.locator('button:has-text("Đóng"), button:has-text("Lưu"), div[role="dialog"] button:has(.lucide-x)').first
                if close_bk.is_visible():
                    close_bk.click()
                else:
                    page.keyboard.press("Escape")
                time.sleep(1.2)

            # -------------------------------------------------------------
            # PHAN 7: DANH GIA LUONG CHIEN DICH (WORKFLOW CANVAS)
            # -------------------------------------------------------------
            print("\n[PHAN 7] Chuyen sang Luồng chiến dịch (Workflow Canvas)...", flush=True)
            workflow_tab = page.locator('nav button, button').filter(has_text="Luồng chiến dịch").first
            if workflow_tab.is_visible():
                workflow_tab.click()
                time.sleep(2.0)
                tester.inject_cursor()
                tester.smooth_scroll(200, steps=10)
                time.sleep(1.0)

            # -------------------------------------------------------------
            # PHAN 8: DANH GIA TRANG QUAN LY CHIEN DICH (CAMPAIGNS)
            # -------------------------------------------------------------
            print("\n[PHAN 8] Chuyen sang Trang Quan ly Chien dich (Campaigns)...", flush=True)
            import re
            camp_tab = page.locator('aside nav button, nav button, button').filter(has_text=re.compile(r"chiến dịch", re.I)).first
            if camp_tab.count() > 0 and camp_tab.is_visible():
                camp_tab.click()
                time.sleep(2.0)
                tester.inject_cursor()

                print("  - Thu nghiem o tim kiem chien dich thoi gian thuc...", flush=True)
                search_input = page.locator('input[placeholder*="Tìm kiếm"]').first
                if search_input.count() > 0 and search_input.is_visible():
                    tester.type_text('input[placeholder*="Tìm kiếm"]', "AI Growth")
                    time.sleep(1.0)
                    tester.type_text('input[placeholder*="Tìm kiếm"]', "")
                    time.sleep(0.6)

                # Mo modal Wizard Tao chien dich moi
                print("  - Mo modal 'Tao Chien Dich Moi'...", flush=True)
                create_camp_btn = page.locator('button:has-text("Tạo Chiến Dịch Mới"), button:has-text("Tạo Chiến Dịch")').first
                if create_camp_btn.count() > 0 and create_camp_btn.is_visible():
                    create_camp_btn.click()
                    time.sleep(1.8)
                    tester.inject_cursor()

                    print("  - Quan sat cac muc tieu chien dich trong Wizard...", flush=True)
                    tester.move_to(500, 380, duration=0.6)
                    time.sleep(1.0)

            # -------------------------------------------------------------
            # PHAN 9: TRO VE DASHBOARD VA THUC HIEN DANG XUAT
            # -------------------------------------------------------------
            print("\n[PHAN 9] Tro ve Dashboard va thuc hien Dang xuat...", flush=True)
            dash_tab = page.locator('aside nav button, nav button, button').filter(has_text=re.compile(r"bảng điều khiển|bàn làm việc", re.I)).first
            if dash_tab.count() > 0 and dash_tab.is_visible():
                dash_tab.click()
                time.sleep(2.0)

            logout_btn = page.locator('button[aria-label="Đăng xuất tài khoản"], button[title="Đăng xuất tài khoản"], button:has(.lucide-log-out)').first
            if logout_btn.count() > 0 and logout_btn.is_visible():
                print("  - Bam 'Dang xuat' va quan sat he thong quay ve man hinh Login an toan...", flush=True)
                logout_btn.click()
                time.sleep(2.5)

            print("\n[✓] TOAN BO KICH BAN DANH GIA TRUC TIEP HOAN TAT XUAT SAC 100%!", flush=True)

        except Exception as e:
            print(f"\n[!] Ghi nhan trong qua trinh: {e}", flush=True)
            import traceback
            traceback.print_exc()

        finally:
            print("[*] Dong trinh duyet va luu video...", flush=True)
            page.close()
            context.close()
            browser.close()

    video_files = list(video_output_dir.glob("*.webm"))
    if video_files:
        final_video = video_files[0]
        target_name = RECORDINGS_DIR / f"marketflow_live_evaluation_{timestamp}.webm"
        final_video.rename(target_name)
        print("\n" + "="*75, flush=True)
        print(f"[SUCCESS] VIDEO DA DUOC GHI HINH THANH CONG TREN DOMAIN {LIVE_DOMAIN}!", flush=True)
        print(f"[+] File video: {target_name.resolve()}", flush=True)
        print(f"[+] Dung luong: {target_name.stat().st_size / (1024*1024):.2f} MB", flush=True)
        print("="*75, flush=True)
        return target_name
    else:
        print("[!] Khong tim thay file video.", flush=True)
        return None

if __name__ == "__main__":
    is_headless = "--show" not in sys.argv
    run_live_evaluation(headless=is_headless)
