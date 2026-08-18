"""Render simple, dependency-free PNG diagrams for the marketing report."""

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams"
FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
BOLD_PATH = Path("C:/Windows/Fonts/arialbd.ttf")
NAVY = "#1f4e79"
PURPLE = "#6841d8"
INK = "#172033"
MUTED = "#667085"
LINE = "#b7c9d6"
BLUE_FILL = "#eef4ff"
PURPLE_FILL = "#f4f3ff"
GREEN_FILL = "#ecfdf3"
ORANGE_FILL = "#fff7ed"


def font(size, bold=False):
    path = BOLD_PATH if bold and BOLD_PATH.exists() else FONT_PATH
    return ImageFont.truetype(str(path), size)


def wrapped(draw, text, width, size=24, bold=False):
    f = font(size, bold)
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines, f


def text_box(draw, box, text, fill, outline=LINE, title=False):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=3)
    lines, f = wrapped(draw, text, x2 - x1 - 36, size=26 if title else 22, bold=title)
    total = len(lines) * (34 if title else 29)
    y = y1 + (y2 - y1 - total) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=f)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) / 2, y), line, fill=INK, font=f)
        y += 34 if title else 29


def arrow(draw, start, end, label=None):
    draw.line([start, end], fill=PURPLE, width=5)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 >= x1 else -1
        head = [(x2, y2), (x2 - sign * 18, y2 - 10), (x2 - sign * 18, y2 + 10)]
    else:
        sign = 1 if y2 >= y1 else -1
        head = [(x2, y2), (x2 - 10, y2 - sign * 18), (x2 + 10, y2 - sign * 18)]
    draw.polygon(head, fill=PURPLE)
    if label:
        draw.text(((x1 + x2) / 2 - 40, (y1 + y2) / 2 - 32), label, fill=MUTED, font=font(20))


def save(image, name):
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / name, optimize=True)


def architecture():
    image = Image.new("RGB", (1800, 900), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 50), "Kiến trúc baseline — Marketing AI", fill=NAVY, font=font(38, True))
    text_box(draw, (80, 320, 340, 500), "Browser\nHTML/CSS", BLUE_FILL, title=True)
    text_box(draw, (470, 260, 820, 560), "Django\nAuth + Views + Forms", PURPLE_FILL, title=True)
    text_box(draw, (950, 260, 1300, 560), "Services\nValidation + Workflow", PURPLE_FILL, title=True)
    text_box(draw, (1440, 120, 1730, 340), "SQLite\nCampaign / Channel / Content / Metric", GREEN_FILL, title=True)
    text_box(draw, (1440, 500, 1730, 720), "AI adapter\nPrompt v1 + Provider / Fallback", ORANGE_FILL, title=True)
    arrow(draw, (340, 410), (470, 410))
    arrow(draw, (820, 410), (950, 410))
    arrow(draw, (1300, 350), (1440, 240), "CRUD")
    arrow(draw, (1300, 470), (1440, 610), "context")
    arrow(draw, (1440, 650), (1300, 500), "draft + warning")
    save(image, "architecture.png")


def usecase():
    image = Image.new("RGB", (1800, 1050), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 50), "Use case chính — Marketing AI", fill=NAVY, font=font(38, True))
    text_box(draw, (90, 220, 350, 360), "Marketing\nManager", BLUE_FILL, title=True)
    text_box(draw, (90, 690, 350, 830), "Marketing\nStaff", BLUE_FILL, title=True)
    cases = [
        ((650, 140, 1080, 250), "Quản lý chiến dịch"),
        ((650, 300, 1080, 410), "Quản lý nội dung / lịch đăng"),
        ((650, 460, 1080, 570), "Ghi nhận metric và thống kê"),
        ((650, 620, 1080, 730), "Duyệt nội dung trước khi đăng"),
        ((650, 780, 1080, 890), "Sinh ý tưởng / caption / email"),
    ]
    for box, label in cases:
        x1, y1, x2, y2 = box
        draw.ellipse(box, fill=PURPLE_FILL, outline=LINE, width=3)
        lines, f = wrapped(draw, label, x2 - x1 - 40, size=22, bold=True)
        y = (y1 + y2 - len(lines) * 28) / 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=f)
            draw.text(((x1 + x2 - (bbox[2] - bbox[0])) / 2, y), line, fill=INK, font=f)
            y += 28
    for end in [(650, 195), (650, 515), (650, 675)]:
        arrow(draw, (350, 290), end)
    for end in [(650, 355), (650, 515), (650, 835)]:
        arrow(draw, (350, 760), end)
    arrow(draw, (1080, 835), (1080, 675), "draft")
    save(image, "usecase.png")


def erd():
    image = Image.new("RGB", (1900, 1000), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "ERD baseline — Marketing AI", fill=NAVY, font=font(38, True))
    entities = [
        ((80, 190, 650, 470), "Campaign", ["id PK", "name / objective / audience", "product / start_date / end_date", "budget / status"] , BLUE_FILL),
        ((80, 620, 650, 860), "Channel", ["id PK", "name UNIQUE", "channel_type / is_active"], BLUE_FILL),
        ((1050, 130, 1770, 470), "Content", ["id PK", "campaign FK / channel FK", "title / body / content_type", "status / source / scheduled_at", "approved_by FK"], ORANGE_FILL),
        ((1050, 620, 1770, 920), "Metric", ["id PK", "campaign FK / channel FK", "metric_date", "impressions / clicks", "conversions / cost", "UNIQUE campaign+channel+date"], GREEN_FILL),
    ]
    for box, title, fields, fill in entities:
        x1, y1, x2, y2 = box
        draw.rounded_rectangle(box, radius=14, fill=fill, outline=LINE, width=3)
        draw.rectangle((x1, y1, x2, y1 + 58), fill=NAVY)
        draw.text((x1 + 20, y1 + 13), title, fill="white", font=font(28, True))
        y = y1 + 82
        for field in fields:
            draw.text((x1 + 24, y), field, fill=INK, font=font(22))
            y += 38
    arrow(draw, (650, 300), (1050, 280), "1:N")
    arrow(draw, (650, 350), (1050, 760), "1:N")
    arrow(draw, (650, 740), (1050, 370), "1:N")
    arrow(draw, (650, 790), (1050, 800), "1:N")
    save(image, "erd.png")


def main():
    architecture()
    usecase()
    erd()
    print("rendered marketing diagrams")


if __name__ == "__main__":
    main()
