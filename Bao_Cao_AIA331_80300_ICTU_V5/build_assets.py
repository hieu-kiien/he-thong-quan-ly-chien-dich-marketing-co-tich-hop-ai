from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parent
OUT = ROOT / "images"
OUT.mkdir(exist_ok=True)

NAVY = "#003B7A"
BLUE = "#00529B"
LIGHT_BLUE = "#EAF2FB"
LIGHT_GREEN = "#EAF7EA"
LIGHT_ORANGE = "#FFF2DE"
GRAY = "#F4F6F8"
TEXT = "#1F2933"


def font(size: int, bold: bool = False):
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


F_TITLE = font(40, True)
F_HEAD = font(28, True)
F_BODY = font(23)
F_SMALL = font(20)
F_TINY = font(17)
F_BOLD = font(21, True)
F_SCHEMA_TITLE = font(44, True)
F_SCHEMA_HEAD = font(31, True)
F_SCHEMA_BODY = font(27)
F_SCHEMA_SMALL = font(23)


def multiline(draw, box, text, fnt, fill=TEXT, align="center", spacing=5):
    x1, y1, x2, y2 = box
    max_width = x2 - x1 - 24
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + spacing * max(0, len(lines) - 1)
    y = y1 + max(0, (y2 - y1 - total) // 2)
    for line, h in zip(lines, heights):
        w = draw.textbbox((0, 0), line, font=fnt)[2]
        x = x1 + 12 if align == "left" else x1 + (x2 - x1 - w) // 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += h + spacing


def rounded(draw, box, fill, outline=BLUE, radius=22, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, start, end, fill=NAVY, width=4, head=14):
    draw.line([start, end], fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        if x2 >= x1:
            points = [(x2, y2), (x2 - head, y2 - head // 2), (x2 - head, y2 + head // 2)]
        else:
            points = [(x2, y2), (x2 + head, y2 - head // 2), (x2 + head, y2 + head // 2)]
    else:
        if y2 >= y1:
            points = [(x2, y2), (x2 - head // 2, y2 - head), (x2 + head // 2, y2 - head)]
        else:
            points = [(x2, y2), (x2 - head // 2, y2 + head), (x2 + head // 2, y2 + head)]
    draw.polygon(points, fill=fill)


def title(draw, text, width):
    draw.text(((width - draw.textbbox((0, 0), text, font=F_TITLE)[2]) // 2, 26), text, font=F_TITLE, fill=NAVY)


def make_bfd():
    w, h = 2100, 1370
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title(d, "SƠ ĐỒ BFD (PHÂN RÃ CHỨC NĂNG)", w)
    root = (600, 105, 1500, 220)
    rounded(d, root, NAVY, outline=NAVY, radius=25)
    multiline(d, root, "HỆ THỐNG QUẢN LÝ CHIẾN DỊCH MARKETING", F_HEAD, "white")
    cols = [
        ("1. TÀI KHOẢN\n& PHÂN QUYỀN", "Đăng nhập\nVai trò\nNgười dùng"),
        ("2. DANH MỤC\n& SẢN PHẨM", "Nhóm sản phẩm\nSản phẩm\nKênh"),
        ("3. CHIẾN DỊCH\n& NGÂN SÁCH", "Mục tiêu\nThời gian\nPhân công"),
        ("4. NỘI DUNG\n& LỊCH ĐĂNG", "Soạn thảo\nPhê duyệt\nLập lịch"),
        ("5. CHỈ SỐ\n& BÁO CÁO", "Nhập số liệu\nKPI\nTìm kiếm"),
        ("6. TRỢ LÝ AI", "Gợi ý ý tưởng\nTạo bản thảo\nTóm tắt"),
    ]
    x0, gap, bw, by, bh = 35, 18, 316, 300, 280
    centers = []
    for i, (head, body) in enumerate(cols):
        x = x0 + i * (bw + gap)
        box = (x, by, x + bw, by + bh)
        centers.append((x + bw // 2, by))
        fill = LIGHT_GREEN if i == 5 else LIGHT_BLUE
        rounded(d, box, fill, outline=BLUE)
        multiline(d, (x + 10, by + 16, x + bw - 10, by + 100), head.replace("\n", " "), F_BOLD, NAVY)
        d.line((x + 28, by + 112, x + bw - 28, by + 112), fill=BLUE, width=2)
        multiline(d, (x + 16, by + 126, x + bw - 16, by + bh - 14), body.replace("\n", "; "), F_BODY, TEXT)
        arrow(d, (root[0] + (root[2] - root[0]) * (i + 0.5) / 6, root[3]), (x + bw // 2, by), width=3, head=12)
    note = (285, 720, 1815, 850)
    rounded(d, note, LIGHT_ORANGE, outline="#C97B00", radius=18, width=3)
    multiline(d, note, "AI chỉ hỗ trợ gợi ý, soạn thảo và tóm tắt; không quyết định quyền, ngân sách, trạng thái duyệt hoặc xuất bản.", F_BODY, TEXT)
    # Detailed child functions make the hierarchy explicit.
    child = [
        ("Dữ liệu đầu vào", "Biểu mẫu, số liệu, quy tắc kênh"),
        ("Xử lý chính", "Python API, SQL, kiểm tra ràng buộc"),
        ("Đầu ra", "Danh sách, bản thảo, lịch và báo cáo"),
    ]
    cx, cy, cw, ch = 370, 955, 430, 180
    for i, (h1, b1) in enumerate(child):
        x = cx + i * 470
        box = (x, cy, x + cw, cy + ch)
        rounded(d, box, GRAY, outline="#7A8793", radius=15, width=2)
        d.text((x + 18, cy + 22), h1, font=F_BOLD, fill=NAVY)
        multiline(d, (x + 18, cy + 63, x + cw - 18, cy + ch - 12), b1, F_SMALL, TEXT, align="left")
    d.text((60, 1265), "BFD được suy ra từ danh mục yêu cầu và dùng làm khung trước khi thiết kế bảng SQL.", font=F_SMALL, fill="#59636E")
    im.save(OUT / "bfd.png")


def actor(d, center, label):
    x, y = center
    d.ellipse((x - 28, y - 70, x + 28, y - 14), outline=NAVY, width=4, fill=LIGHT_BLUE)
    d.line((x, y - 14, x, y + 60), fill=NAVY, width=4)
    d.line((x - 42, y + 6, x + 42, y + 6), fill=NAVY, width=4)
    d.line((x, y + 60, x - 34, y + 105), fill=NAVY, width=4)
    d.line((x, y + 60, x + 34, y + 105), fill=NAVY, width=4)
    tw = d.textbbox((0, 0), label, font=F_BOLD)[2]
    d.text((x - tw // 2, y + 120), label, font=F_BOLD, fill=NAVY)


def make_usecase():
    w, h = 1900, 1450
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title(d, "SƠ ĐỒ USE CASE VÀ PHÂN QUYỀN", w)
    boundary = (480, 125, 1810, 1280)
    rounded(d, boundary, "#FBFCFE", outline=NAVY, radius=25, width=4)
    d.text((1470, 150), "HỆ THỐNG QUẢN LÝ CHIẾN DỊCH", font=F_BOLD, fill=NAVY)
    actor(d, (210, 360), "MANAGER")
    actor(d, (210, 890), "MARKETER")
    usecases = [
        ("UC01", "Quản lý tài khoản và vai trò"),
        ("UC02", "Quản lý nhóm sản phẩm, sản phẩm, kênh"),
        ("UC03", "Tạo và điều chỉnh chiến dịch"),
        ("UC04", "Soạn thảo nội dung"),
        ("UC05", "Duyệt hoặc từ chối nội dung"),
        ("UC06", "Lập lịch và cập nhật trạng thái"),
        ("UC07", "Nhập chỉ số, xem KPI và báo cáo"),
        ("UC08", "Gọi AI: gợi ý, soạn thảo, tóm tắt"),
    ]
    boxes = []
    x, y, bw, bh, gap = 700, 210, 900, 105, 28
    for i, (code, text) in enumerate(usecases):
        yy = y + i * (bh + gap)
        box = (x, yy, x + bw, yy + bh)
        boxes.append(box)
        fill = LIGHT_GREEN if code == "UC08" else LIGHT_BLUE
        rounded(d, box, fill, outline=BLUE, radius=18, width=3)
        multiline(d, (x + 18, yy + 12, x + bw - 18, yy + bh - 12), f"{code}  {text}", F_BODY, TEXT)
    manager_links = [0, 1, 2, 4, 6, 7]
    marketer_links = [1, 2, 3, 5, 6, 7]
    for i in manager_links:
        box = boxes[i]
        arrow(d, (315, 390), (box[0], (box[1] + box[3]) // 2), fill=NAVY, width=3, head=12)
    for i in marketer_links:
        box = boxes[i]
        arrow(d, (315, 920), (box[0], (box[1] + box[3]) // 2), fill="#8A4B00", width=3, head=12)
    d.text((55, 1285), "Manager: quản lý dữ liệu nền, ngân sách và phê duyệt.  Marketer: vận hành nội dung, lịch và số liệu theo chiến dịch được phân công.", font=F_SMALL, fill="#59636E")
    im.save(OUT / "usecase.png")


def entity(d, box, name, lines, fill=LIGHT_BLUE):
    rounded(d, box, fill, outline=BLUE, radius=16, width=3)
    x1, y1, x2, y2 = box
    d.text((x1 + 18, y1 + 12), name, font=F_BOLD, fill=NAVY)
    d.line((x1 + 16, y1 + 55, x2 - 16, y1 + 55), fill=BLUE, width=2)
    yy = y1 + 70
    for line in lines:
        d.text((x1 + 18, yy), line, font=F_TINY, fill=TEXT)
        yy += 26


def schema_card_height(rows, row_height=58, header_height=78, column_header_height=52):
    return header_height + column_header_height + row_height * len(rows) + 8


def schema_cell(d, box, text, fnt=F_SCHEMA_BODY, fill=TEXT, align="left"):
    x1, y1, x2, y2 = box
    multiline(d, (x1 + 10, y1 + 5, x2 - 10, y2 - 5), str(text), fnt, fill, align=align, spacing=2)


def schema_card(d, x, y, width, name, rows, fill=LIGHT_BLUE, row_height=58):
    """Draw a readable SQL table card: key marker, column, type, and rule."""
    header_height = 78
    column_header_height = 52
    height = schema_card_height(rows, row_height, header_height, column_header_height)
    x2 = x + width
    y2 = y + height
    rounded(d, (x, y, x2, y2), "white", outline=BLUE, radius=14, width=3)
    d.rounded_rectangle((x, y, x2, y + header_height), radius=14, fill=NAVY, outline=NAVY, width=3)
    d.rectangle((x, y + header_height - 14, x2, y + header_height), fill=NAVY)
    d.text((x + 20, y + 17), name, font=F_SCHEMA_HEAD, fill="white")

    y_head = y + header_height
    d.rectangle((x, y_head, x2, y_head + column_header_height), fill=fill, outline=BLUE, width=2)
    col1 = x + 390
    col2 = col1 + 230
    for xx in (col1, col2):
        d.line((xx, y_head, xx, y2), fill="#9BB7D3", width=2)
    d.line((x, y_head + column_header_height, x2, y_head + column_header_height), fill=BLUE, width=2)
    schema_cell(d, (x, y_head, col1, y_head + column_header_height), "Khóa / cột", F_SCHEMA_SMALL, NAVY)
    schema_cell(d, (col1, y_head, col2, y_head + column_header_height), "Kiểu", F_SCHEMA_SMALL, NAVY)
    schema_cell(d, (col2, y_head, x2, y_head + column_header_height), "Ràng buộc", F_SCHEMA_SMALL, NAVY)

    y_row = y_head + column_header_height
    for idx, (marker, column, ctype, rule) in enumerate(rows):
        row_fill = "#F8FBFE" if idx % 2 == 0 else "white"
        d.rectangle((x, y_row, x2, y_row + row_height), fill=row_fill)
        d.line((x, y_row, x2, y_row), fill="#C9D7E5", width=1)
        key_text = f"{marker}  {column}" if marker else column
        key_fill = "#7B3F00" if marker == "FK" else NAVY if marker == "PK" else TEXT
        schema_cell(d, (x, y_row, col1, y_row + row_height), key_text, F_SCHEMA_BODY, key_fill)
        schema_cell(d, (col1, y_row, col2, y_row + row_height), ctype, F_SCHEMA_BODY, TEXT)
        schema_cell(d, (col2, y_row, x2, y_row + row_height), rule, F_SCHEMA_SMALL, TEXT)
        y_row += row_height
    d.line((x, y_row, x2, y_row), fill=BLUE, width=2)
    return height


def schema_title(d, text, width):
    tw = d.textbbox((0, 0), text, font=F_SCHEMA_TITLE)[2]
    d.text(((width - tw) // 2, 24), text, font=F_SCHEMA_TITLE, fill=NAVY)


def schema_note(d, box, text):
    rounded(d, box, "#F8FAFC", outline="#7A8793", radius=12, width=2)
    multiline(d, (box[0] + 14, box[1] + 8, box[2] - 14, box[3] - 8), text, F_SCHEMA_SMALL, TEXT, align="left", spacing=3)


def make_sql_product_tables():
    """Create a proper visual representation of the two tables required by the brief."""
    w, h = 2500, 1120
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    schema_title(d, "BẢNG SQL: NHÓM SẢN PHẨM VÀ SẢN PHẨM", w)
    categories = [
        ("PK", "id", "INTEGER", "định danh nhóm"),
        ("", "name", "TEXT", "NN · UQ · tên nhóm"),
        ("", "description", "TEXT", "mô tả nhóm"),
    ]
    products = [
        ("PK", "id", "INTEGER", "định danh sản phẩm"),
        ("FK", "category_id", "INTEGER", "NN · → product_categories.id"),
        ("", "name", "TEXT", "NN · tên sản phẩm"),
        ("", "usp", "TEXT", "NN · điểm khác biệt"),
        ("", "audience", "TEXT", "NN · đối tượng khách hàng"),
        ("", "price", "REAL", "NN · CK ≥ 0"),
        ("", "status", "TEXT", "NN · DEF ACTIVE · CK list"),
    ]
    left_x, right_x, top, card_w = 100, 1320, 165, 1060
    left_h = schema_card(d, left_x, top, card_w, "product_categories", categories, LIGHT_BLUE)
    right_h = schema_card(d, right_x, top, card_w, "products", products, LIGHT_GREEN)
    arrow(d, (left_x + card_w + 24, top + 220), (right_x - 24, top + 220), fill="#2D5F9A", width=5, head=18)
    d.text((left_x + card_w + 45, top + 175), "1 --- N", font=F_SCHEMA_SMALL, fill=NAVY)
    schema_note(d, (150, 850, 2350, 1020), "Quan hệ: products.category_id → product_categories.id. Ràng buộc ON DELETE RESTRICT chặn xóa nhóm khi còn sản phẩm; UNIQUE chặn trùng tên nhóm; CHECK chặn giá âm và trạng thái sai.")
    im.save(OUT / "sql_product_tables.png")


def make_sql_schema_core():
    """Create detailed table cards for the account, catalog, campaign, and content domain."""
    w = 2700
    im = Image.new("RGB", (w, 3000), "white")
    d = ImageDraw.Draw(im)
    schema_title(d, "CÁC BẢNG SQL NGHIỆP VỤ: TÀI KHOẢN, DỮ LIỆU NỀN VÀ NỘI DUNG", w)
    card_w, gap, top = 1220, 160, 150
    x1, x2 = 100, 100 + card_w + gap
    users = [
        ("PK", "id", "INTEGER", "định danh"),
        ("", "email", "TEXT", "NN · UQ · đăng nhập"),
        ("", "password_hash", "TEXT", "NN · mật khẩu băm"),
        ("", "full_name", "TEXT", "NN · họ tên"),
        ("", "role", "TEXT", "NN · CK MANAGER/MARKETER"),
        ("", "is_active", "INTEGER", "NN · DEF 1 · CK 0/1"),
        ("", "created_at", "TEXT", "NN · DEF CURRENT_TIMESTAMP"),
    ]
    categories = [
        ("PK", "id", "INTEGER", "định danh nhóm"),
        ("", "name", "TEXT", "NN · UQ · tên nhóm"),
        ("", "description", "TEXT", "mô tả nhóm"),
    ]
    channels = [
        ("PK", "id", "INTEGER", "định danh kênh"),
        ("", "name", "TEXT", "NN · UQ · tên kênh"),
        ("", "format_rules", "TEXT", "NN · quy tắc định dạng"),
    ]
    campaigns = [
        ("PK", "id", "INTEGER", "định danh chiến dịch"),
        ("FK", "product_id", "INTEGER", "NN · → products.id"),
        ("FK", "owner_id", "INTEGER", "NN · → users.id"),
        ("", "name", "TEXT", "NN · tên chiến dịch"),
        ("", "objective", "TEXT", "NN · mục tiêu"),
        ("", "start_date", "TEXT", "NN · ngày bắt đầu"),
        ("", "end_date", "TEXT", "NN · ≥ start_date"),
        ("", "budget", "REAL", "NN · CK ≥ 0"),
        ("", "status", "TEXT", "NN · DEF DRAFT · CK list"),
    ]
    products = [
        ("PK", "id", "INTEGER", "định danh sản phẩm"),
        ("FK", "category_id", "INTEGER", "NN · → product_categories.id"),
        ("", "name", "TEXT", "NN · tên sản phẩm"),
        ("", "usp", "TEXT", "NN · điểm khác biệt"),
        ("", "audience", "TEXT", "NN · đối tượng"),
        ("", "price", "REAL", "NN · CK ≥ 0"),
        ("", "status", "TEXT", "NN · DEF ACTIVE · CK list"),
    ]
    contents = [
        ("PK", "id", "INTEGER", "định danh nội dung"),
        ("FK", "campaign_id", "INTEGER", "NN · → campaigns.id"),
        ("FK", "channel_id", "INTEGER", "NN · → marketing_channels.id"),
        ("FK", "created_by", "INTEGER", "NN · → users.id"),
        ("", "title", "TEXT", "NN · tiêu đề"),
        ("", "body", "TEXT", "NN · nội dung"),
        ("", "cta", "TEXT", "lời kêu gọi"),
        ("", "status", "TEXT", "NN · DRAFT/AI_DRAFT/..."),
        ("", "ai_provider", "TEXT", "nhà cung cấp AI"),
        ("", "prompt_version", "TEXT", "phiên bản prompt"),
        ("", "source_ids", "TEXT", "nguồn context"),
        ("", "rejection_reason", "TEXT", "lý do từ chối"),
        ("", "created_at", "TEXT", "NN · thời điểm tạo"),
        ("", "updated_at", "TEXT", "NN · thời điểm sửa"),
    ]
    y1 = top
    for name, rows, fill in [("users", users, LIGHT_BLUE), ("marketing_channels", channels, LIGHT_BLUE), ("campaigns", campaigns, LIGHT_ORANGE)]:
        height = schema_card(d, x1, y1, card_w, name, rows, fill, row_height=55)
        y1 += height + 48
    y2 = top
    for name, rows, fill in [("product_categories", categories, LIGHT_BLUE), ("products", products, LIGHT_GREEN), ("marketing_contents", contents, LIGHT_GREEN)]:
        height = schema_card(d, x2, y2, card_w, name, rows, fill, row_height=55)
        y2 += height + 48
    bottom = max(y1, y2)
    schema_note(d, (100, bottom + 8, 2600, bottom + 142), "Khóa ngoại chính: products.category_id → product_categories.id; campaigns.product_id → products.id; campaigns.owner_id → users.id; marketing_contents nối campaigns, marketing_channels và users. Các trạng thái được CHECK để Python xử lý đúng luồng nghiệp vụ.")
    im = im.crop((0, 0, w, bottom + 165))
    im.save(OUT / "sql_schema_core.png")


def make_sql_schema_ops():
    """Create detailed table cards for scheduling, metrics, and AI audit logs."""
    w = 2700
    im = Image.new("RGB", (w, 2450), "white")
    d = ImageDraw.Draw(im)
    schema_title(d, "CÁC BẢNG SQL NGHIỆP VỤ: LỊCH, KPI VÀ NHẬT KÝ AI", w)
    card_w, gap, top = 1220, 160, 150
    x1, x2 = 100, 100 + card_w + gap
    schedules = [
        ("PK", "id", "INTEGER", "định danh lịch"),
        ("FK", "content_id", "INTEGER", "NN · → marketing_contents.id"),
        ("", "scheduled_at", "TEXT", "NN · thời điểm đăng"),
        ("", "timezone", "TEXT", "NN · DEF Asia/Ho_Chi_Minh"),
        ("", "status", "TEXT", "NN · PLANNED/CANCELLED/EXECUTED"),
    ]
    metrics = [
        ("PK", "id", "INTEGER", "định danh chỉ số"),
        ("FK", "campaign_id", "INTEGER", "NN · → campaigns.id"),
        ("FK", "channel_id", "INTEGER", "NN · → marketing_channels.id"),
        ("", "metric_date", "TEXT", "NN · ngày đo"),
        ("", "views", "INTEGER", "NN · DEF 0 · CK ≥ 0"),
        ("", "clicks", "INTEGER", "NN · DEF 0 · CK ≥ 0"),
        ("", "conversions", "INTEGER", "NN · DEF 0 · CK ≥ 0"),
        ("", "cost", "REAL", "NN · DEF 0 · CK ≥ 0"),
        ("", "revenue", "REAL", "NN · DEF 0 · CK ≥ 0"),
    ]
    logs = [
        ("PK", "id", "INTEGER", "định danh log"),
        ("FK", "user_id", "INTEGER", "→ users.id · có thể rỗng"),
        ("FK", "campaign_id", "INTEGER", "→ campaigns.id · có thể rỗng"),
        ("", "function_name", "TEXT", "NN · chức năng AI"),
        ("", "provider", "TEXT", "NN · nhà cung cấp"),
        ("", "model", "TEXT", "tên model"),
        ("", "prompt_version", "TEXT", "NN · phiên bản prompt"),
        ("", "input_tokens", "INTEGER", "số token vào"),
        ("", "output_tokens", "INTEGER", "số token ra"),
        ("", "latency_ms", "INTEGER", "độ trễ"),
        ("", "result_status", "TEXT", "NN · SUCCESS/FAILED/..."),
        ("", "error_code", "TEXT", "mã lỗi nếu có"),
        ("", "source_ids", "TEXT", "nguồn context"),
        ("", "created_at", "TEXT", "NN · thời điểm gọi"),
    ]
    schedule_h = schema_card(d, x1, top, card_w, "marketing_schedules", schedules, LIGHT_ORANGE, row_height=55)
    metrics_h = schema_card(d, x1, top + schedule_h + 60, card_w, "campaign_metrics", metrics, LIGHT_ORANGE, row_height=55)
    logs_h = schema_card(d, x2, top, card_w, "ai_logs", logs, LIGHT_GREEN, row_height=55)
    schema_note(d, (x2, top + logs_h + 60, x2 + card_w, top + logs_h + 200), "UNIQUE(campaign_id, channel_id, metric_date) bảo đảm mỗi chiến dịch/kênh/ngày chỉ có một dòng KPI.")
    bottom = max(top + schedule_h + 60 + metrics_h, top + logs_h + 220)
    schema_note(d, (100, bottom + 8, 2600, bottom + 142), "AI chỉ tạo gợi ý/bản nháp/tóm tắt. Python kiểm tra quyền và trạng thái; ai_logs lưu người gọi, chiến dịch, prompt, nguồn, kết quả và lỗi để truy vết.")
    im = im.crop((0, 0, w, bottom + 165))
    im.save(OUT / "sql_schema_ops.png")


def make_erd():
    w, h = 2200, 1540
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title(d, "ERD TỪ CÁC BẢNG SQL, KHÓA CHÍNH VÀ KHÓA NGOẠI", w)
    bw, bh = 380, 150
    coords = {
        "categories": (80, 180),
        "products": (650, 180),
        "campaigns": (1220, 180),
        "users": (80, 550),
        "channels": (650, 550),
        "contents": (1220, 550),
        "schedules": (80, 920),
        "metrics": (650, 920),
        "logs": (1220, 920),
    }
    data = {
        "categories": ("product_categories", ["PK id", "name UNIQUE", "description"]),
        "products": ("products", ["PK id", "FK category_id", "name, usp", "audience, price"]),
        "campaigns": ("campaigns", ["PK id", "FK product_id, owner_id", "name, objective", "dates, budget, status"]),
        "users": ("users", ["PK id", "email UNIQUE", "role, is_active"]),
        "channels": ("marketing_channels", ["PK id", "name UNIQUE", "format_rules"]),
        "contents": ("marketing_contents", ["PK id", "FK campaign_id, channel_id", "title, body, cta", "status, source_ids"]),
        "schedules": ("marketing_schedules", ["PK id", "FK content_id", "scheduled_at, status"]),
        "metrics": ("campaign_metrics", ["PK id", "FK campaign_id, channel_id", "metric_date", "views, clicks, cost, revenue"]),
        "logs": ("ai_logs", ["PK id", "FK user_id, campaign_id", "function_name, provider", "prompt_version, result_status"]),
    }
    for key, (name, lines) in data.items():
        entity(d, (*coords[key], coords[key][0] + bw, coords[key][1] + bh), name, lines, LIGHT_GREEN if key == "logs" else LIGHT_BLUE)

    def c(key, side):
        x, y = coords[key]
        if side == "left":
            return x, y + bh // 2
        if side == "right":
            return x + bw, y + bh // 2
        if side == "top":
            return x + bw // 2, y
        return x + bw // 2, y + bh

    for a, b, s1, s2 in [
        ("categories", "products", "right", "left"),
        ("products", "campaigns", "right", "left"),
        ("users", "campaigns", "top", "bottom"),
        ("campaigns", "contents", "right", "left"),
        ("channels", "contents", "right", "left"),
        ("contents", "schedules", "left", "right"),
        ("campaigns", "metrics", "bottom", "top"),
        ("channels", "metrics", "bottom", "top"),
        ("users", "logs", "right", "left"),
        ("campaigns", "logs", "bottom", "top"),
    ]:
        arrow(d, c(a, s1), c(b, s2), fill="#2D5F9A", width=3, head=12)
    d.text((80, 1260), "Mũi tên đi từ bảng cha đến bảng con; mọi quan hệ trong hình đều phải có FOREIGN KEY tương ứng trong DDL.", font=F_SMALL, fill="#59636E")
    im.crop((0, 0, w, 1360)).save(OUT / "erd.png")


def make_architecture():
    w, h = 2050, 1200
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title(d, "KIẾN TRÚC PYTHON VÀ VỊ TRÍ CỦA AI", w)
    layers = [
        ("TẦNG GIAO DIỆN", "Frontend web: biểu mẫu, danh sách, dashboard", LIGHT_BLUE),
        ("TẦNG API PYTHON", "FastAPI, router, JWT/RBAC, Pydantic", LIGHT_BLUE),
        ("TẦNG NGHIỆP VỤ", "CampaignService, ContentService, MetricsService", LIGHT_BLUE),
        ("TẦNG DỮ LIỆU", "SQLite/SQLAlchemy, transaction, FK/CHECK, seed", GRAY),
    ]
    x, y, bw, bh, gap = 240, 190, 1190, 150, 55
    for i, (head, body, fill) in enumerate(layers):
        yy = y + i * (bh + gap)
        box = (x, yy, x + bw, yy + bh)
        rounded(d, box, fill, outline=BLUE, radius=20, width=3)
        d.text((x + 25, yy + 25), head, font=F_HEAD, fill=NAVY)
        d.text((x + 25, yy + 88), body, font=F_BODY, fill=TEXT)
        if i:
            arrow(d, (x + bw // 2, yy - gap + 8), (x + bw // 2, yy - 6), width=4, head=14)
    ai = (1500, 480, 1950, 820)
    rounded(d, ai, LIGHT_GREEN, outline="#2E8B57", radius=20, width=4)
    multiline(d, (ai[0] + 20, ai[1] + 20, ai[2] - 20, ai[1] + 90), "AI SERVICE", F_HEAD, "#1D6B3B")
    multiline(d, (ai[0] + 24, ai[1] + 110, ai[2] - 24, ai[3] - 20), "adapter provider\ncontext từ SQL\nprompt có cấu trúc\nJSON validation\nretry, timeout, mock", F_BODY, TEXT)
    arrow(d, (x + bw, y + 1 * (bh + gap) + bh // 2), (ai[0], ai[1] + 65), fill="#2E8B57", width=4, head=14)
    arrow(d, (ai[0], ai[3] - 60), (x + bw, y + 2 * (bh + gap) + bh // 2), fill="#2E8B57", width=4, head=14)
    d.text((80, 1080), "AI nằm sau lớp nghiệp vụ Python: chỉ nhận context được chọn, trả bản nháp/kết quả phân tích và không tự ghi lịch hay xuất bản.", font=F_SMALL, fill="#59636E")
    im.save(OUT / "architecture.png")


def make_ai_flow():
    w, h = 2150, 1250
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title(d, "VỊ TRÍ AI TRONG QUY TRÌNH MARKETING", w)
    steps = [
        ("1. DỮ LIỆU SQL", "sản phẩm\nmục tiêu\nkênh\nchỉ số", LIGHT_BLUE),
        ("2. PYTHON BACKEND", "kiểm tra quyền\nlấy context\nchọn prompt", LIGHT_BLUE),
        ("3. AI SERVICE", "gọi model/mock\nparse JSON\nghi ai_logs", LIGHT_GREEN),
        ("4. BẢN NHÁP", "AI_DRAFT\nsource_ids\nhiển thị kết quả", LIGHT_ORANGE),
        ("5. CON NGƯỜI", "Marketer sửa\nManager duyệt\nmới được lập lịch", "#EDE7F6"),
    ]
    x, y, bw, bh, gap = 75, 250, 360, 330, 35
    for i, (head, body, fill) in enumerate(steps):
        xx = x + i * (bw + gap)
        box = (xx, y, xx + bw, y + bh)
        rounded(d, box, fill, outline=BLUE if i != 2 else "#2E8B57", radius=24, width=4)
        multiline(d, (xx + 18, y + 22, xx + bw - 18, y + 110), head, F_BOLD, NAVY)
        d.line((xx + 25, y + 128, xx + bw - 25, y + 128), fill=BLUE, width=2)
        multiline(d, (xx + 25, y + 150, xx + bw - 25, y + bh - 20), body.replace("\n", "; "), F_BODY, TEXT)
        if i < len(steps) - 1:
            arrow(d, (xx + bw + 5, y + bh // 2), (xx + bw + gap - 5, y + bh // 2), width=4, head=14)
    tasks = [
        ("Gợi ý ý tưởng", "sản phẩm + USP + đối tượng"),
        ("Tạo bản thảo", "kênh + mục tiêu + format_rules"),
        ("Tóm tắt chỉ số", "Views, Clicks, Cost, Revenue"),
    ]
    for i, (head, body) in enumerate(tasks):
        xx = 210 + i * 600
        box = (xx, 780, xx + 520, 950)
        rounded(d, box, GRAY, outline="#7A8793", radius=16, width=2)
        d.text((xx + 20, 805), head, font=F_BOLD, fill=NAVY)
        multiline(d, (xx + 20, 850, xx + 500, 930), body, F_SMALL, TEXT, align="left")
    note = (290, 1030, 1860, 1155)
    rounded(d, note, "#F8F8F8", outline="#7A8793", radius=14, width=2)
    multiline(d, note, "AI không làm: xuất bản nội dung, thay đổi ngân sách, cấp quyền, sửa công thức KPI hoặc tự phê duyệt nội dung.", F_BODY, TEXT)
    im.save(OUT / "ai_flow.png")


if __name__ == "__main__":
    make_bfd()
    make_usecase()
    make_sql_product_tables()
    make_sql_schema_core()
    make_sql_schema_ops()
    make_erd()
    make_architecture()
    make_ai_flow()
    print("Created diagram assets")
