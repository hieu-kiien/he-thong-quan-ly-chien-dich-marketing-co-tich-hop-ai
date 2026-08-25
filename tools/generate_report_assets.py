"""Regenerate the small, deterministic PNG assets used by the project report."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams"
FONT = Path("C:/Windows/Fonts/arial.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")

# Print-safe palette. Neutral fills preserve grouping in grayscale; the dark
# slate accent keeps the color version restrained but recognisable.
INK = "#1f2933"
MUTED = "#5f6872"
ACCENT = "#34495e"
LINE = "#a8b0b7"
FILL_LIGHT = "#f8f9fa"
FILL_MID = "#e7ebee"
FILL_SOFT = "#f1f3f5"
FILL_DARK = "#d9e0e5"
BAR = "#b7c0c9"
SERIES = "#263746"


def font(size, bold=False):
    path = FONT_BOLD if bold else FONT
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def text_size(draw, value, size, bold=False):
    box = draw.textbbox((0, 0), value, font=font(size, bold))
    return box[2] - box[0], box[3] - box[1]


def center_text(draw, xy, value, size, fill=INK, bold=False):
    x, y = xy
    width, height = text_size(draw, value, size, bold)
    draw.text((x - width / 2, y - height / 2), value, font=font(size, bold), fill=fill)


def draw_card(draw, box, title, rows, fill, accent):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=LINE, width=2)
    draw.rounded_rectangle((x1, y1, x2, y1 + 50), radius=18, fill=accent)
    draw.rectangle((x1, y1 + 34, x2, y1 + 50), fill=accent)
    draw.text((x1 + 16, y1 + 13), title, font=font(22, True), fill="white")
    y = y1 + 70
    for row in rows:
        draw.text((x1 + 16, y), row, font=font(17), fill=INK)
        y += 28


def arrow(draw, start, end, label, color=ACCENT):
    draw.line([start, end], fill=color, width=3)
    x1, y1 = start
    x2, y2 = end
    length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    px, py = -uy, ux
    tip = (x2, y2)
    left = (x2 - ux * 16 + px * 7, y2 - uy * 16 + py * 7)
    right = (x2 - ux * 16 - px * 7, y2 - uy * 16 - py * 7)
    draw.polygon([tip, left, right], fill=color)
    center_text(draw, ((x1 + x2) / 2, (y1 + y2) / 2 - 14), label, 15, color, True)


def make_erd():
    image = Image.new("RGB", (1900, 1080), "white")
    draw = ImageDraw.Draw(image)
    center_text(draw, (950, 42), "ERD — Dữ liệu và quan hệ", 30, ACCENT, True)
    boxes = {
        "user": (70, 150, 440, 340),
        "campaign": (600, 120, 1070, 400),
        "channel": (1300, 120, 1810, 340),
        "content": (380, 640, 950, 1000),
        "metric": (1110, 640, 1720, 1000),
    }
    draw_card(draw, boxes["user"], "User", ["id PK", "username", "role"], FILL_SOFT, ACCENT)
    draw_card(draw, boxes["campaign"], "Campaign", ["id PK", "name · objective", "audience · product", "start_date · end_date", "budget · status", "created_by FK → User"], FILL_LIGHT, ACCENT)
    draw_card(draw, boxes["channel"], "Channel", ["id PK", "name UNIQUE", "channel_type", "is_active"], FILL_LIGHT, ACCENT)
    draw_card(draw, boxes["content"], "Content", ["id PK", "campaign FK · channel FK", "title · body · content_type", "status · source", "scheduled_at", "approved_by FK → User"], FILL_MID, ACCENT)
    draw_card(draw, boxes["metric"], "Metric", ["id PK", "campaign FK · channel FK", "metric_date", "impressions · clicks", "conversions · cost", "UNIQUE campaign/channel/date"], FILL_DARK, ACCENT)
    arrow(draw, (440, 230), (600, 230), "created_by 1:N")
    arrow(draw, (440, 285), (530, 640), "approved_by 1:N")
    arrow(draw, (820, 400), (680, 640), "1:N")
    arrow(draw, (960, 400), (1380, 640), "1:N")
    arrow(draw, (1430, 340), (780, 640), "1:N")
    arrow(draw, (1570, 340), (1450, 640), "1:N")
    draw.text((70, 1030), "Ràng buộc chính: budget ≥ 0; start_date ≤ end_date; clicks ≤ impressions; conversions ≤ clicks.", font=font(18), fill=MUTED)
    image.save(OUT / "erd.png")


def make_architecture():
    image = Image.new("RGB", (2100, 930), "white")
    draw = ImageDraw.Draw(image)
    center_text(draw, (1050, 42), "Kiến trúc và luồng dữ liệu chính", 30, ACCENT, True)
    boxes = {
        "browser": (70, 280, 370, 480),
        "django": (470, 210, 820, 550),
        "db": (940, 140, 1330, 390),
        "ai": (940, 510, 1430, 780),
        "rag": (1540, 140, 2010, 360),
        "approval": (1540, 520, 2010, 780),
    }
    draw_card(draw, boxes["browser"], "Browser", ["HTML/CSS", "Form + status", "Manager/Staff"], FILL_LIGHT, ACCENT)
    draw_card(draw, boxes["django"], "Django", ["Auth/RBAC", "URL/View/Form", "Service validation", "CSRF + messages"], FILL_SOFT, ACCENT)
    draw_card(draw, boxes["db"], "SQLite", ["Campaign", "Channel", "Content", "Metric", "User"], FILL_DARK, ACCENT)
    draw_card(draw, boxes["ai"], "AI adapter", ["Prompt AI-CAM-001-v1", "Provider / offline fallback", "JSON schema validation", "warning + human approval"], FILL_MID, ACCENT)
    draw_card(draw, boxes["rag"], "RAG tài liệu", ["Allowlist canonical", "Citation + line range", "Không truy hồi legacy", "Dùng cho yêu cầu / prompt"], FILL_LIGHT, ACCENT)
    draw_card(draw, boxes["approval"], "Approval gate", ["DRAFT / PENDING_REVIEW", "APPROVED", "PUBLISHED", "Manager quyết định"], FILL_MID, ACCENT)
    arrow(draw, (370, 380), (470, 380), "request")
    arrow(draw, (820, 280), (940, 260), "CRUD")
    arrow(draw, (820, 470), (940, 640), "context")
    arrow(draw, (1430, 650), (1540, 650), "draft + warning")
    arrow(draw, (1430, 600), (1540, 260), "requirements")
    arrow(draw, (1770, 520), (1770, 360), "citation")
    draw.text((70, 850), "Luồng AI: context đã lọc → prompt có version → provider/fallback → kiểm tra schema → draft → Manager duyệt → lưu trạng thái.", font=font(18), fill=MUTED)
    image.save(OUT / "architecture.png")


def make_metric_chart():
    image = Image.new("RGB", (1800, 950), "white")
    draw = ImageDraw.Draw(image)
    center_text(draw, (900, 45), "Biểu đồ minh họa hiệu quả chiến dịch", 30, ACCENT, True)
    draw.text((80, 88), "Dữ liệu demo phục vụ phân tích; không phải số liệu production.", font=font(18), fill=MUTED)
    left, top, right, bottom = 150, 180, 1660, 760
    draw.line((left, bottom, right, bottom), fill=INK, width=3)
    draw.line((left, top, left, bottom), fill=INK, width=3)
    impressions = [900, 1200, 1100, 1500, 1700, 1450, 1900]
    clicks = [55, 80, 72, 105, 120, 98, 140]
    max_imp = 2000
    bar_width = 120
    gap = 90
    for index, (imp, click) in enumerate(zip(impressions, clicks)):
        x = left + 80 + index * (bar_width + gap)
        height = int(imp / max_imp * (bottom - top - 30))
        draw.rounded_rectangle((x, bottom - height, x + bar_width, bottom), radius=10, fill=BAR)
        click_y = bottom - int(click / 150 * (bottom - top - 30))
        if index:
            prev_x = left + 80 + (index - 1) * (bar_width + gap) + bar_width // 2
            prev_y = bottom - int(clicks[index - 1] / 150 * (bottom - top - 30))
            draw.line((prev_x, prev_y, x + bar_width // 2, click_y), fill=SERIES, width=6)
        draw.ellipse((x + bar_width // 2 - 8, click_y - 8, x + bar_width // 2 + 8, click_y + 8), fill=SERIES)
        center_text(draw, (x + bar_width / 2, bottom + 32), f"D{index + 1}", 17, INK, True)
        center_text(draw, (x + bar_width / 2, bottom - height - 22), str(imp), 15, ACCENT, True)
    draw.line((1300, 110, 1360, 110), fill=BAR, width=16)
    draw.text((1375, 98), "Impressions", font=font(17), fill=INK)
    draw.line((1300, 145, 1360, 145), fill=SERIES, width=6)
    draw.ellipse((1322, 137, 1338, 153), fill=SERIES)
    draw.text((1375, 133), "Clicks", font=font(17), fill=INK)
    draw.text((150, 795), "Cách đọc: impressions là cột; clicks là đường. CTR = clicks / impressions × 100%.", font=font(18), fill=MUTED)
    image.save(OUT / "metric-chart.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_erd()
    make_architecture()
    make_metric_chart()
    print("Generated erd.png, architecture.png and metric-chart.png")
