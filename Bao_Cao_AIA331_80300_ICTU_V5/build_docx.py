from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).parent
OUT = ROOT / "BAO_CAO_DU_AN_AIA331_80300_ICTU_V5.docx"
NAVY = "003B7A"
LIGHT = "EEF3FB"
TABLE_COUNTER = 0


def set_run_font(run, name="Times New Roman", size=12, bold=False, italic=False, color=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=70, start=80, bottom=70, end=80):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    node = OxmlElement("w:cantSplit")
    node.set(qn("w:val"), "true")
    tr_pr.append(node)


def style_document(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(4)
    for style_name, size in (("Heading 1", 14), ("Heading 2", 13), ("Heading 3", 12)):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(NAVY)
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True


def setup_sections(doc):
    for section in doc.sections:
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(3.5)
        section.right_margin = Cm(2)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run()
        set_run_font(run, size=10)
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        text = OxmlElement("w:t")
        text.text = "1"
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run._r.extend([fld_begin, instr, fld_sep, text, fld_end])


def page_break(doc):
    doc.add_page_break()


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    return p


def add_para(doc, text, indent=True, align=None, bold=False, italic=False, size=12):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(4)
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.27)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run(text), size=11.5)
    return p


def add_number(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run(text), size=11.5)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    set_run_font(p.add_run(text), size=10.5, italic=True)
    return p


def add_table(doc, headers, rows, caption=None, font_size=9.5, header_fill=LIGHT):
    global TABLE_COUNTER
    if caption:
        TABLE_COUNTER += 1
        add_caption(doc, f"Bảng {TABLE_COUNTER}. {caption}")
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    hdr = table.rows[0]
    repeat_header(hdr)
    cant_split(hdr)
    for cell, value in zip(hdr.cells, headers):
        set_cell_shading(cell, header_fill)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(str(value))
        set_run_font(run, size=font_size, bold=True)
    for row_values in rows:
        row = table.add_row()
        cant_split(row)
        cells = row.cells
        for cell, value in zip(cells, row_values):
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(str(value))
            set_run_font(run, size=font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_code(doc, code, caption=None, size=8.3):
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F7F7F8")
    set_cell_margins(cell, top=80, start=110, bottom=80, end=110)
    p = cell.paragraphs[0]
    p.paragraph_format.left_indent = Cm(0)
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    lines = code.strip("\n").splitlines()
    for idx, line in enumerate(lines):
        run = p.add_run(line)
        set_run_font(run, name="Consolas", size=size, color="1B1B1B")
        if idx != len(lines) - 1:
            run.add_break()
    if caption:
        add_caption(doc, caption)
    return table


def add_figure(doc, filename, caption, width=15.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(ROOT / "images" / filename), width=Cm(width))
    add_caption(doc, caption)


def add_url(doc, label, url):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    p.paragraph_format.space_after = Pt(5)
    set_run_font(p.add_run(label + ": " + url), size=11)
    return p


def numbered(doc, items):
    for index, item in enumerate(items, start=1):
        add_para(doc, f"{index}. {item}", indent=False, size=11.5)


def compact_numbered(doc, items):
    for index, item in enumerate(items, start=1):
        p = add_para(doc, f"{index}. {item}", indent=False, size=11)
        p.paragraph_format.line_spacing = 1.05
        p.paragraph_format.space_after = Pt(1)


def build_cover(doc):
    add_para(doc, "ĐẠI HỌC THÁI NGUYÊN", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14)
    add_para(doc, "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=13)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    if (ROOT / "images" / "logo_ictu.png").exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(ROOT / "images" / "logo_ictu.png"), width=Cm(3.8))
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    add_para(doc, "BÁO CÁO DỰ ÁN HỌC PHẦN", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=15)
    add_para(doc, "HỌC PHẦN: ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AIA331)", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=13)
    add_para(doc, "HÌNH THỨC: DỰ ÁN  |  MÃ SỐ: 80300", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_para(doc, "HỆ THỐNG QUẢN LÝ CHIẾN DỊCH MARKETING\nCÓ TÍCH HỢP TRÍ TUỆ NHÂN TẠO", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=18)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    add_table(doc, ["Thông tin", "Nội dung"], [
        ("Giảng viên hướng dẫn", "TS. Nguyễn Tuấn Anh"),
        ("Nhóm thực hiện", "Nhóm 25"),
        ("Sinh viên 1", "Vũ Hiếu Kiên - DTC245200244"),
        ("Sinh viên 2", "Nguyễn Hải Đăng - DTC245120051"),
        ("Năm học", "2025 - 2026"),
    ], font_size=10.5)
    add_para(doc, "Thái Nguyên, tháng 09 năm 2026", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, size=11.5)
    page_break(doc)


def build_rubric(doc):
    add_heading(doc, "PHIẾU ĐÁNH GIÁ VÀ NHẬN XÉT CỦA GIẢNG VIÊN HƯỚNG DẪN", 1)
    add_para(doc, "Trường: Trường Đại học Công nghệ Thông tin và Truyền thông | Khoa: Khoa Công nghệ Thông tin", indent=False, size=10.5)
    add_para(doc, "Học phần: Ứng dụng trí tuệ nhân tạo (AIA331) | Hình thức: Dự án | Mã số: 80300 | Nhóm: 25", indent=False, size=11)
    add_para(doc, "Giảng viên hướng dẫn: TS. Nguyễn Tuấn Anh", indent=False, size=11)
    rows = [
        ("01", "Khảo sát bối cảnh, người dùng, người quản lý, dữ liệu, yêu cầu và quy trình nghiệp vụ", "Chương 1", ""),
        ("02", "Xác định chức năng, yêu cầu phi chức năng, actor và Use Case", "Chương 1", ""),
        ("03", "Thiết kế CSDL, ERD, PK/FK, ràng buộc và lệnh SQL tạo bảng", "Chương 2", ""),
        ("04", "Thiết kế kiến trúc, cấu trúc dự án và xây dựng hệ thống bằng Python", "Chương 3", ""),
        ("05", "Đăng nhập, phân quyền, CRUD, tìm kiếm, dashboard và xử lý lỗi", "Chương 3", ""),
        ("06", "Xác định vị trí AI, API/model, dữ liệu vào/ra và nhiệm vụ nghiệp vụ", "Chương 4", ""),
        ("07", "Prompt, schema, ba vòng thử nghiệm, grounding, kiểm duyệt và giới hạn AI", "Chương 4", ""),
        ("08", "Kiểm thử quản lý và AI; minh chứng AI hỗ trợ rà soát mã nguồn", "Chương 3 - 4", ""),
        ("09", "Bảo mật, cấu hình, README, đóng gói, sao lưu và khôi phục", "Chương 1, Phụ lục", ""),
        ("10", "Hình thức báo cáo, tài liệu tham khảo, minh chứng và kịch bản demo", "Toàn bộ báo cáo", ""),
    ]
    add_table(doc, ["Tiêu chí", "Nội dung nhận xét", "Vị trí minh chứng", "Điểm / nhận xét"], rows, caption="Bảng nhận xét dành cho giảng viên", font_size=8.7)
    add_para(doc, "Nhận xét của giảng viên:", indent=False, bold=True, size=11.5)
    for _ in range(5):
        add_para(doc, "________________________________________________________________________________", indent=False, size=10.5)
    add_para(doc, "Điểm: ....................   Chữ ký giảng viên: ........................................", indent=False, size=11)
    page_break(doc)


def build_acknowledgment(doc):
    add_heading(doc, "LỜI CẢM ƠN", 1)
    add_para(doc, "Nhóm 25 xin trân trọng cảm ơn TS. Nguyễn Tuấn Anh đã hướng dẫn nhóm trong quá trình khảo sát, phân tích nghiệp vụ, thiết kế cơ sở dữ liệu và xây dựng hệ thống cho học phần Ứng dụng trí tuệ nhân tạo.")
    add_para(doc, "Các góp ý về việc trình bày theo chương, sử dụng SQL làm cơ sở cho sơ đồ, phân biệt người dùng với người quản lý và xác định đúng phạm vi AI đã được nhóm dùng để hoàn thiện báo cáo này.")
    add_para(doc, "Do thời gian và kinh nghiệm còn hạn chế, báo cáo có thể vẫn còn điểm cần chỉnh sửa. Nhóm mong nhận được nhận xét để tiếp tục hoàn thiện sản phẩm và tài liệu.")
    page_break(doc)


def build_commitment(doc):
    add_heading(doc, "LỜI CAM ĐOAN", 1)
    add_para(doc, "Nhóm cam kết báo cáo được thực hiện cho học phần AIA331, nội dung phân tích và thiết kế được nhóm tự tổng hợp từ yêu cầu của dự án. Các đoạn mã SQL, Python và sơ đồ trong báo cáo được dùng để minh họa cho hệ thống; thông tin chưa có số liệu triển khai thực tế được ghi rõ là mẫu hoặc thử nghiệm nội bộ.")
    add_para(doc, "Nhóm chịu trách nhiệm giải thích các quyết định về dữ liệu, quy trình, phân quyền và vị trí của AI. AI chỉ tạo gợi ý hoặc bản nháp có kiểm duyệt; người có quyền vẫn chịu trách nhiệm về nội dung, ngân sách, KPI, phê duyệt và xuất bản.")
    add_para(doc, "Đại diện nhóm: Vũ Hiếu Kiên                         Nguyễn Hải Đăng", indent=False, size=11)
    page_break(doc)


def build_contents(doc):
    add_heading(doc, "MỤC LỤC", 1)
    add_para(doc, "Các chương được tách rõ và bắt đầu ở trang mới. Báo cáo đi từ yêu cầu nghiệp vụ đến SQL, sơ đồ, hệ thống Python, AI, kiểm thử và hồ sơ triển khai.", indent=False, italic=True, size=11)
    contents = [
        "LỜI MỞ ĐẦU",
        "CHƯƠNG 1. PHÂN TÍCH BÀI TOÁN VÀ YÊU CẦU",
        "  1.1. Bối cảnh và mục tiêu khảo sát",
        "  1.2. Đối tượng sử dụng và trách nhiệm",
        "  1.3. Danh mục yêu cầu nghiệp vụ và quy tắc P01 - P26",
        "  1.4. Quy trình nghiệp vụ tổng thể",
        "  1.5. Yêu cầu chức năng và phi chức năng",
        "  1.6. Phân quyền người dùng và người quản lý",
        "  1.7. Use Case, đầu vào, đầu ra và điều kiện",
        "CHƯƠNG 2. THIẾT KẾ CƠ SỞ DỮ LIỆU BẰNG SQL",
        "  2.1. Liên kết giữa yêu cầu và thiết kế dữ liệu",
        "  2.2. Sơ đồ BFD phân rã chức năng",
        "  2.3. Bảng SQL nhóm sản phẩm và sản phẩm",
        "  2.4. Mô hình các bảng nghiệp vụ",
        "  2.5. ERD được suy ra từ khóa chính và khóa ngoại",
        "  2.6. Truy vấn nghiệp vụ, KPI và kiểm tra toàn vẹn",
        "CHƯƠNG 3. THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG PYTHON",
        "  3.1. Kiến trúc và cấu trúc mã nguồn",
        "  3.2. Đăng nhập và phân quyền",
        "  3.3. CRUD nhóm sản phẩm và sản phẩm",
        "  3.4. Quy trình chiến dịch, nội dung, lịch và chỉ số",
        "  3.5. Tìm kiếm, KPI, giao diện và xử lý lỗi",
        "  3.6. Kiểm thử và minh chứng",
        "CHƯƠNG 4. XÁC ĐỊNH VÀ TÍCH HỢP AI ĐÚNG PHẠM VI",
        "  4.1. AI nằm ở đâu trong hệ thống",
        "  4.2. Ba nhiệm vụ AI được phép thực hiện",
        "  4.3. Prompt, dữ liệu nền và kiểm duyệt",
        "  4.4. Lỗi, nhật ký và thử nghiệm mẫu",
        "CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN",
        "  5.1. Kết quả đạt được",
        "  5.2. Hạn chế",
        "  5.3. Hướng phát triển",
        "  5.4. Kịch bản demo và bàn giao",
        "TÀI LIỆU THAM KHẢO",
        "PHỤ LỤC A. DDL, TRẠNG THÁI VÀ CHECKLIST MINH CHỨNG",
        "  A.1. Ma trận đối chiếu tiêu chí môn học và minh chứng",
        "  A.2. Cách chạy DDL và dữ liệu mẫu",
        "  A.3. DDL đầy đủ",
        "  A.4. Quy tắc trạng thái",
        "  A.5. Checklist trước khi nộp",
        "PHIẾU ĐÁNH GIÁ VÀ NHẬN XÉT CỦA GIẢNG VIÊN HƯỚNG DẪN",
        "LỜI CẢM ƠN",
        "LỜI CAM ĐOAN",
        "DANH MỤC THUẬT NGỮ VÀ TỪ VIẾT TẮT",
    ]
    for item in contents:
        p = add_para(doc, item, indent=False, size=10.3 if item.startswith("  ") else 10.7)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(1)
    page_break(doc)
    add_heading(doc, "DANH MỤC BẢNG VÀ HÌNH", 1)
    add_para(doc, "Danh mục bảng", indent=False, bold=True, size=11.5)
    for item in [
        "Bảng 1. Cấu trúc báo cáo và điểm bắt đầu của từng chương",
        "Bảng 2. Đối tượng sử dụng và trách nhiệm trong hệ thống",
        "Bảng 3. Danh mục yêu cầu nghiệp vụ và quy tắc cần giải quyết",
        "Bảng 4. Yêu cầu chức năng của hệ thống",
        "Bảng 5. Yêu cầu phi chức năng",
        "Bảng 6. Ma trận phân quyền Manager và Marketer",
        "Bảng 7. Đầu vào, đầu ra và điều kiện của các Use Case chính",
        "Bảng 8. Đối chiếu yêu cầu và thiết kế dữ liệu",
        "Bảng 9. Phân rã chức năng theo BFD",
        "Bảng 10. Ý nghĩa các thành phần SQL trong thiết kế bảng",
        "Bảng 11. Các quan hệ được kiểm chứng từ DDL",
        "Bảng 12. Kiểm tra toàn vẹn và quy tắc SQL",
        "Bảng 13. Phân lớp của hệ thống Python",
        "Bảng 14. Ý nghĩa các dòng mã Python trong luồng đăng nhập và phân quyền",
        "Bảng 15. API CRUD nhóm sản phẩm và sản phẩm",
        "Bảng 16. Quy tắc trạng thái nghiệp vụ",
        "Bảng 17. Giao diện theo vai trò",
        "Bảng 18. Mã lỗi và cách phản hồi",
        "Bảng 19. Danh sách ca kiểm thử từ nghiệp vụ đến AI",
        "Bảng 20. Luồng xử lý AI trong hệ thống",
        "Bảng 21. Phạm vi nhiệm vụ AI",
        "Bảng 22. Ranh giới trách nhiệm của AI",
        "Bảng 23. Ma trận lỗi AI",
        "Bảng 24. Thử nghiệm prompt trên dữ liệu mẫu nội bộ",
        "Bảng 25. Minh chứng AI hỗ trợ phân tích, thiết kế và rà soát mã nguồn",
        "Bảng 26. Đối chiếu kết quả với yêu cầu của dự án",
        "Bảng 27. Ma trận đối chiếu tiêu chí môn học và minh chứng",
        "Bảng 28. Bảng trạng thái dùng để kiểm thử",
        "Bảng 29. Bảng nhận xét dành cho giảng viên",
    ]:
        add_para(doc, item, indent=False, size=10.5)
    add_para(doc, "Danh mục hình", indent=False, bold=True, size=11.5)
    for item in [
        "Hình 1. Use Case tổng quát",
        "Hình 2. Sơ đồ BFD (phân rã chức năng)",
        "Hình 3. Bảng SQL nhóm sản phẩm và sản phẩm",
        "Hình 4. Bảng SQL của tài khoản, dữ liệu nền, chiến dịch và nội dung",
        "Hình 5. Bảng SQL của lịch đăng, KPI và nhật ký AI",
        "Hình 6. ERD từ các bảng SQL",
        "Hình 7. Kiến trúc hệ thống Python",
        "Hình 8. Vị trí AI trong quy trình marketing",
    ]:
        add_para(doc, item, indent=False, size=10.5)
    page_break(doc)


def build_abbreviations(doc):
    add_heading(doc, "DANH MỤC THUẬT NGỮ VÀ TỪ VIẾT TẮT", 1)
    add_table(doc, ["Từ viết tắt", "Giải thích"], [
        ("AI", "Artificial Intelligence - trí tuệ nhân tạo"),
        ("API", "Application Programming Interface"),
        ("BFD", "Business Function Diagram - sơ đồ phân rã chức năng"),
        ("CRUD", "Create, Read, Update, Delete"),
        ("DDL", "Data Definition Language"),
        ("ERD", "Entity Relationship Diagram"),
        ("FK", "Foreign Key - khóa ngoại"),
        ("KPI", "Key Performance Indicator"),
        ("PK", "Primary Key - khóa chính"),
        ("RBAC", "Role Based Access Control"),
        ("SQL", "Structured Query Language"),
    ], font_size=10.2)


def build_introduction(doc):
    add_heading(doc, "LỜI MỞ ĐẦU", 1)
    add_para(doc, "Đề tài xây dựng hệ thống quản lý chiến dịch marketing có tích hợp trí tuệ nhân tạo. Trọng tâm của báo cáo là giải thích yêu cầu nghiệp vụ, dữ liệu, quy trình và cách Python vận hành hệ thống; AI chỉ được đặt vào những bước tạo gợi ý, bản nháp và tóm tắt có kiểm duyệt.")
    add_para(doc, "Báo cáo được tổ chức thành năm chương theo một mạch thống nhất: phân tích bài toán và yêu cầu, thiết kế SQL, xây dựng hệ thống Python, tích hợp AI và tổng hợp kết quả. Cách trình bày này giúp giảng viên theo dõi được mối liên hệ từ yêu cầu đến bảng dữ liệu và chức năng.")
    add_table(doc, ["Chương", "Nội dung", "Điểm bắt đầu"], [
        ("Chương 1", "Khảo sát, actor, P01 - P26, quy trình, yêu cầu và phân quyền", "Trang mới"),
        ("Chương 2", "BFD, SQL, khóa chính, khóa ngoại, ERD và truy vấn", "Trang mới"),
        ("Chương 3", "Kiến trúc, API, RBAC, trạng thái, KPI và kiểm thử", "Trang mới"),
        ("Chương 4", "Vị trí AI, ba nhiệm vụ, prompt, kiểm duyệt và giới hạn", "Trang mới"),
        ("Chương 5", "Kết quả, giới hạn, hướng phát triển và hồ sơ triển khai", "Trang mới"),
    ], caption="Cấu trúc báo cáo và điểm bắt đầu của từng chương", font_size=9.3)
    add_heading(doc, "Mục tiêu báo cáo", 2)
    numbered(doc, [
        "Mô tả rõ người dùng, người quản lý và trách nhiệm của từng vai trò.",
        "Liệt kê toàn bộ yêu cầu nghiệp vụ của dự án từ tài khoản, dữ liệu nền đến báo cáo và AI.",
        "Dùng SQL làm nguồn thiết kế bảng, ràng buộc và sơ đồ ERD.",
        "Chứng minh Python là phần xây dựng hệ thống chính, còn AI là dịch vụ hỗ trợ có giới hạn.",
        "Đưa ra ca kiểm thử và checklist minh chứng để đánh giá được cả tài liệu lẫn sản phẩm.",
    ])
    add_heading(doc, "Phạm vi và giả định", 2)
    add_para(doc, "CSDL của bản thiết kế và demo mẫu dùng SQLite; backend minh họa dùng Python với FastAPI, Pydantic và SQLAlchemy. Các kênh marketing được lưu trong bảng, nội dung chỉ được lập lịch sau khi Manager duyệt. Số liệu KPI trong báo cáo là dữ liệu mẫu để minh họa công thức và truy vấn.")
    page_break(doc)


def build_chapter1(doc):
    add_heading(doc, "CHƯƠNG 1. PHÂN TÍCH BÀI TOÁN VÀ YÊU CẦU", 1)
    add_para(doc, "Chương này xác định đầu vào chung cho toàn bộ báo cáo. Mọi bảng SQL, nhánh BFD, endpoint Python và ca kiểm thử ở các chương sau đều phải đối chiếu được với danh mục yêu cầu ở đây.")
    add_heading(doc, "1.1. Bối cảnh và mục tiêu khảo sát", 2)
    add_para(doc, "Một nhóm marketing quản lý nhiều sản phẩm trên nhiều kênh truyền thông. Công việc gồm lưu thông tin sản phẩm, lập chiến dịch, phân công, kiểm soát ngân sách, soạn nội dung, duyệt, lập lịch, nhập số liệu và theo dõi hiệu quả. Nếu chỉ trình bày một màn hình AI thì chưa mô tả được hệ thống; vì vậy báo cáo bắt đầu từ nghiệp vụ và dữ liệu.")
    add_heading(doc, "1.2. Đối tượng sử dụng và trách nhiệm", 2)
    add_table(doc, ["Đối tượng", "Trách nhiệm chính", "Quyền quyết định"], [
        ("Marketing Manager", "Quản lý người dùng, nhóm sản phẩm, sản phẩm, kênh, chiến dịch, ngân sách; duyệt nội dung.", "Duyệt hoặc từ chối; điều chỉnh dữ liệu nền và quyền người dùng."),
        ("Marketer", "Xem chiến dịch được phân công, soạn nội dung, yêu cầu AI hỗ trợ, lập lịch theo quyền và nhập số liệu.", "Sửa bản nháp và gửi duyệt; không tự duyệt nội dung."),
        ("Hệ thống Python", "Kiểm tra đăng nhập, quyền, dữ liệu, khóa ngoại, trạng thái và giao dịch SQL.", "Thực hiện quy tắc đã lập trình, không tự quyết định nghiệp vụ."),
        ("AI service", "Nhận context đã chọn để gợi ý ý tưởng, tạo bản nháp hoặc tóm tắt số liệu.", "Không phải actor nghiệp vụ; không cấp quyền, duyệt, đổi ngân sách hoặc xuất bản."),
    ], caption="Đối tượng sử dụng và trách nhiệm trong hệ thống", font_size=8.8)
    add_para(doc, "CÁC QUYẾT ĐỊNH NGHIỆP VỤ DÙNG ĐỂ GIỮ ĐÚNG PHẠM VI", indent=False, bold=True, size=11.5)
    add_para(doc, "Trong bản thiết kế hiện tại, Manager xem được toàn bộ dữ liệu, tạo dữ liệu nền, đặt ngân sách, phân công và duyệt nội dung. Marketer chỉ xem chiến dịch được giao, tạo hoặc sửa bản nháp, gửi duyệt, đề xuất lịch cho nội dung đã được duyệt và nhập số liệu; Marketer không đổi ngân sách và không được duyệt nội dung. Hệ thống không tự xuất bản lên mạng xã hội.")
    add_para(doc, "Một chiến dịch hiện gắn với một sản phẩm và một người phụ trách để mô hình dễ kiểm tra; một chiến dịch có thể có nhiều nội dung nhưng mỗi nội dung gắn một kênh. Ngân sách dự kiến được lưu riêng với chi phí thực tế trong bảng chỉ số. Nếu nghiệp vụ cần nhiều sản phẩm hoặc nhiều người phụ trách, đó là phần mở rộng phải bổ sung bảng liên kết và ca kiểm thử, không tự đưa vào phạm vi hiện tại.")
    add_heading(doc, "1.3. Danh mục yêu cầu nghiệp vụ và quy tắc", 2)
    add_para(doc, "Mã P01 - P26 được dùng xuyên suốt báo cáo để truy vết. Đây không phải danh sách bài tập hay 26 tính năng độc lập; một yêu cầu lớn có thể bao gồm thêm, sửa, tìm kiếm và các kiểm tra như email trùng, giá âm, dữ liệu thiếu hoặc điều kiện xóa. Cột chủ thể cho biết ai sử dụng hoặc chịu trách nhiệm.")
    problems = [
        ("P01", "Tạo và quản lý tài khoản", "Manager", "Email, họ tên, vai trò; kiểm tra email duy nhất", "Tài khoản hoạt động hoặc lỗi trùng"),
        ("P02", "Đăng nhập hệ thống", "Cả hai", "Email và mật khẩu; kiểm tra giá trị băm", "Phiên đăng nhập hoặc lỗi 401"),
        ("P03", "Phân quyền theo vai trò", "Hệ thống", "Token và vai trò Manager/Marketer", "Cho phép hoặc từ chối endpoint"),
        ("P04", "Quản lý nhóm sản phẩm", "Manager", "Tên nhóm, mô tả; kiểm tra không trùng", "Bản ghi nhóm sản phẩm"),
        ("P05", "Quản lý sản phẩm", "Manager", "Tên, giá, USP, đối tượng, nhóm; kiểm tra FK và giá không âm", "Sản phẩm thuộc đúng nhóm"),
        ("P06", "Quản lý kênh marketing", "Manager", "Tên kênh và quy tắc định dạng", "Kênh có cấu hình dùng cho nội dung"),
        ("P07", "Tạo chiến dịch", "Manager", "Tên, sản phẩm, mục tiêu, thời gian, ngân sách", "Chiến dịch ở trạng thái DRAFT"),
        ("P08", "Kiểm tra thời gian và ngân sách", "Hệ thống", "Ngày bắt đầu, ngày kết thúc, ngân sách", "Không nhận ngày ngược hoặc tiền âm"),
        ("P09", "Phân công người vận hành", "Manager", "Chiến dịch và người phụ trách", "Marketer nhìn thấy đúng chiến dịch"),
        ("P10", "Tạo bản nháp thủ công", "Marketer", "Chiến dịch, kênh, tiêu đề và nội dung", "Nội dung DRAFT"),
        ("P11", "Sửa và lưu bản nháp", "Marketer", "Nội dung đang soạn và người sửa", "Bản ghi cập nhật, giữ trạng thái phù hợp"),
        ("P12", "Theo dõi nguồn bản nháp", "Hệ thống", "Người tạo, thời gian, provider và source_ids", "Biết nội dung do người hay AI tạo"),
        ("P13", "Gửi nội dung để duyệt", "Marketer", "DRAFT hoặc AI_DRAFT đủ trường", "Chuyển sang PENDING"),
        ("P14", "Duyệt nội dung", "Manager", "Nội dung PENDING và quyết định duyệt", "APPROVED hoặc yêu cầu sửa"),
        ("P15", "Từ chối có lý do", "Manager", "Nội dung PENDING và lý do từ chối", "REJECTED kèm lý do"),
        ("P16", "Lập lịch nội dung", "Người có quyền", "Nội dung APPROVED, thời điểm, múi giờ", "Bản ghi lịch PLANNED"),
        ("P17", "Hủy hoặc ghi nhận lịch", "Người có quyền", "Lịch và trạng thái thực hiện", "CANCELLED hoặc EXECUTED"),
        ("P18", "Nhập số liệu theo ngày và kênh", "Marketer", "Views, Clicks, Conversions, Cost, Revenue", "Chỉ số không âm"),
        ("P19", "Tính KPI", "Hệ thống", "Chỉ số đã lưu theo chiến dịch/kênh/ngày", "CTR, CPC, CPA, ROI; không chia cho 0"),
        ("P20", "Xem dashboard và báo cáo", "Cả hai", "Khoảng thời gian, chiến dịch, kênh", "Tổng hợp bảng và biểu đồ"),
        ("P21", "Tìm kiếm dữ liệu", "Cả hai", "Từ khóa tên sản phẩm, chiến dịch, nội dung", "Danh sách phù hợp, có phân trang"),
        ("P22", "Lọc và sắp xếp", "Cả hai", "Trạng thái, ngày, kênh, chi phí", "Kết quả đúng điều kiện và thứ tự"),
        ("P23", "Kiểm tra dữ liệu trùng và xóa", "Hệ thống", "Khóa duy nhất, quan hệ FK, yêu cầu xóa", "Giữ dữ liệu hợp lệ, báo lỗi quan hệ"),
        ("P24", "Xử lý lỗi và phản hồi", "Hệ thống", "Lỗi 400, 401, 403, 404, 409, 422, 500", "Thông báo dễ hiểu, có mã lỗi"),
        ("P25", "AI gợi ý và tạo bản nháp", "Marketer", "Sản phẩm, USP, đối tượng, kênh, format_rules", "AI_DRAFT có source_ids và cần duyệt"),
        ("P26", "AI tóm tắt số liệu và nhật ký", "Manager", "KPI đã truy vấn và kết quả model", "Tóm tắt có log, không tự quyết định"),
    ]
    add_table(doc, ["Mã", "Yêu cầu nghiệp vụ / quy tắc", "Chủ thể", "Đầu vào / xử lý", "Kết quả cần có"], problems, caption="Danh mục yêu cầu nghiệp vụ và quy tắc cần giải quyết", font_size=7.5)
    add_heading(doc, "1.4. Quy trình nghiệp vụ tổng thể", 2)
    numbered(doc, [
        "Manager tạo tài khoản, vai trò, nhóm sản phẩm, sản phẩm và kênh; hệ thống kiểm tra dữ liệu trùng, khóa ngoại và giá trị không hợp lệ.",
        "Manager tạo chiến dịch, đặt mục tiêu, thời gian, ngân sách và phân công Marketer. Hệ thống từ chối ngày kết thúc trước ngày bắt đầu hoặc ngân sách âm.",
        "Marketer tạo nội dung thủ công hoặc yêu cầu AI gợi ý. Bản AI sinh ra chỉ là AI_DRAFT, luôn lưu nguồn và người yêu cầu.",
        "Marketer kiểm tra, sửa và gửi nội dung. Manager xem PENDING, duyệt thành APPROVED hoặc từ chối với lý do.",
        "Nội dung đã duyệt mới được lập lịch. Người có quyền có thể hủy lịch hoặc ghi nhận EXECUTED.",
        "Marketer nhập chỉ số theo ngày và kênh; Python tính KPI bằng dữ liệu SQL và xử lý trường hợp mẫu số bằng 0.",
        "Manager và Marketer xem dashboard theo quyền, tìm kiếm, lọc và xuất báo cáo; AI chỉ có thể tóm tắt dữ liệu đã được truy vấn.",
    ])
    add_heading(doc, "1.5. Yêu cầu chức năng và phi chức năng", 2)
    add_table(doc, ["Mã", "Yêu cầu chức năng", "P liên quan"], [
        ("FR01", "Đăng nhập, đăng xuất và xác thực vai trò", "P01 - P03"),
        ("FR02", "Quản lý nhóm sản phẩm, sản phẩm và kênh", "P04 - P06"),
        ("FR03", "Tạo chiến dịch, kiểm tra ngân sách/thời gian và phân công", "P07 - P09"),
        ("FR04", "Tạo, sửa, lưu và theo dõi nguồn nội dung", "P10 - P12"),
        ("FR05", "Gửi, duyệt, từ chối và lập lịch nội dung", "P13 - P17"),
        ("FR06", "Nhập số liệu, tính KPI và xem báo cáo", "P18 - P20"),
        ("FR07", "Tìm kiếm, lọc, sắp xếp và phân trang", "P21 - P22"),
        ("FR08", "Ràng buộc dữ liệu, chống xóa sai và phản hồi lỗi", "P23 - P24"),
        ("FR09", "AI gợi ý ý tưởng và tạo bản nháp có nguồn", "P25"),
        ("FR10", "AI tóm tắt KPI và ghi nhật ký sử dụng", "P26"),
        ("FR11", "Audit người tạo, người duyệt và thời điểm thay đổi", "P11 - P15, P25 - P26"),
    ], caption="Yêu cầu chức năng của hệ thống", font_size=8.5)
    add_table(doc, ["Mã", "Yêu cầu phi chức năng", "Cách kiểm tra"], [
        ("NFR01", "Bảo mật mật khẩu và token; giới hạn quyền ở backend", "TC01 - TC04, xem mã RBAC"),
        ("NFR02", "Toàn vẹn dữ liệu bằng PK, FK, UNIQUE, CHECK", "Chạy ddl.sql và TC05 - TC09"),
        ("NFR03", "Phản hồi lỗi có mã và thông báo rõ", "TC17 - TC19"),
        ("NFR04", "Truy vấn có phân trang và bộ lọc", "TC14 - TC16"),
        ("NFR05", "AI có timeout, fallback và log", "TC19 - TC20"),
        ("NFR06", "Tài liệu có thể truy vết từ P đến SQL/Python/AI", "Bảng đối chiếu toàn báo cáo"),
        ("NFR07", "Có DDL, seed, hướng dẫn sao lưu và khôi phục dữ liệu mẫu", "Chạy quy trình backup/restore"),
    ], caption="Yêu cầu phi chức năng", font_size=8.7)
    add_heading(doc, "1.6. Phân quyền người dùng và người quản lý", 2)
    add_table(doc, ["Chức năng", "Manager", "Marketer", "Quy tắc"], [
        ("Tài khoản, vai trò", "Đầy đủ", "Xem hồ sơ", "Chỉ Manager được cấp quyền"),
        ("Nhóm sản phẩm, sản phẩm, kênh", "Tạo/sửa/xóa", "Xem", "Không xóa khi còn bản ghi phụ thuộc"),
        ("Chiến dịch và phân công", "Tạo/sửa/phân công", "Xem chiến dịch được giao", "Backend kiểm tra ownership"),
        ("Nội dung", "Duyệt/từ chối", "Tạo/sửa/gửi duyệt", "Không tự duyệt nội dung của mình"),
        ("Lịch đăng", "Xem/điều chỉnh", "Tạo theo quyền/hủy lịch", "Chỉ nội dung APPROVED"),
        ("Số liệu và báo cáo", "Xem toàn bộ", "Nhập và xem phạm vi được giao", "KPI tính từ SQL"),
        ("AI", "Tóm tắt KPI", "Gợi ý/bản nháp", "Không được cấp quyền cho AI"),
    ], caption="Ma trận phân quyền Manager và Marketer", font_size=8.6)
    add_heading(doc, "1.7. Use Case, đầu vào, đầu ra và điều kiện", 2)
    add_figure(doc, "usecase.png", "Hình 1. Use Case tổng quát của hệ thống", width=15.7)
    add_table(doc, ["Use Case", "Đầu vào", "Đầu ra", "Điều kiện / ngoại lệ"], [
        ("UC01 Đăng nhập", "Email, mật khẩu", "JWT và vai trò", "Sai thông tin: 401; tài khoản khóa: 403"),
        ("UC02 Quản lý dữ liệu nền", "Nhóm, sản phẩm, kênh", "Bản ghi SQL", "Trùng tên/FK sai: 409 hoặc 422"),
        ("UC03 Quản lý chiến dịch", "Mục tiêu, thời gian, ngân sách", "DRAFT và phân công", "Ngày ngược/tiền âm: 422"),
        ("UC04 Quản lý nội dung", "Bản nháp, quyết định duyệt", "PENDING/APPROVED/REJECTED", "Từ chối phải có lý do"),
        ("UC05 Lập lịch và KPI", "Thời điểm, chỉ số", "Lịch và báo cáo", "Chưa duyệt thì không lập lịch"),
        ("UC06 Trợ lý AI", "Context được chọn", "Gợi ý/AI_DRAFT/tóm tắt", "Timeout: fallback; kết quả luôn cần người xem"),
    ], caption="Đầu vào, đầu ra và điều kiện của các Use Case chính", font_size=8.5)
    add_para(doc, "Kết luận chương: hệ thống có hai vai trò nghiệp vụ rõ ràng, 26 mã yêu cầu được truy vết, quy trình có kiểm soát trạng thái và AI có phạm vi hẹp. Đây là căn cứ để thiết kế SQL, BFD, ERD, Python và kiểm thử.", bold=True, size=11.5)
    page_break(doc)


def build_chapter2(doc):
    add_heading(doc, "CHƯƠNG 2. THIẾT KẾ CƠ SỞ DỮ LIỆU BẰNG SQL", 1)
    add_para(doc, "Thiết kế cơ sở dữ liệu được xây dựng trực tiếp từ yêu cầu khảo sát. Mỗi nhóm yêu cầu P01 - P26 được chuyển thành bảng, khóa, trạng thái hoặc truy vấn như bảng đối chiếu dưới đây.")
    add_para(doc, "QUYẾT ĐỊNH NỀN TẢNG VÀ PHẠM VI DỮ LIỆU", indent=False, bold=True, size=11.5)
    add_para(doc, "Trong phạm vi bản thiết kế và demo mẫu, nhóm chốt SQLite kết hợp SQLAlchemy vì đề cương đề tài cho phép SQLite và tệp ddl.sql hiện tại dùng cú pháp SQLite có thể chạy lại trên máy cá nhân. Các hình bảng SQL và ERD trong báo cáo được dựng từ chính DDL này, không phải ảnh vẽ tay tách rời dữ liệu.")
    add_para(doc, "SQL Server chưa được coi là hệ quản trị đã triển khai trong báo cáo này. Nếu giảng viên yêu cầu dùng hệ Microsoft, nhóm cần xác nhận trước rồi chuyển DDL sang T-SQL, chạy tệp trên SQL Server bằng SSMS và dựng lại Database Diagram từ cơ sở dữ liệu đã tạo. Khi đó phải cập nhật kiểu dữ liệu, khóa tự tăng, câu lệnh bật khóa ngoại và ảnh sơ đồ; không được gọi bản SQLite hiện tại là kết quả chạy trên SQL Server.")
    add_para(doc, "Quyết định phạm vi dữ liệu hiện tại là: một chiến dịch gắn với một sản phẩm và một người phụ trách; một chiến dịch có thể có nhiều nội dung, mỗi nội dung gắn với một kênh. Ngân sách dự kiến nằm ở campaigns.budget, còn chi phí thực tế nằm ở campaign_metrics.cost. Nếu cần nhiều sản phẩm hoặc nhiều người phụ trách cho một chiến dịch, thiết kế mở rộng phải thêm các bảng liên kết tương ứng.")
    add_heading(doc, "2.1. Liên kết giữa yêu cầu và thiết kế dữ liệu", 2)
    add_table(doc, ["Nhóm P", "Yêu cầu nghiệp vụ", "Thiết kế dữ liệu"], [
        ("P01 - P03", "Tài khoản, đăng nhập, vai trò", "users, mật khẩu băm ở Python, JWT/RBAC"),
        ("P04 - P06", "Nhóm sản phẩm, sản phẩm, kênh", "product_categories, products, marketing_channels"),
        ("P07 - P09", "Chiến dịch, ngân sách, phân công", "campaigns, owner_id, kiểm tra ngày/tiền"),
        ("P10 - P17", "Nội dung, duyệt, lịch", "marketing_contents, marketing_schedules, status"),
        ("P18 - P22", "Chỉ số, KPI, báo cáo, tìm kiếm/lọc", "campaign_metrics, SELECT/JOIN, filter/pagination"),
        ("P23 - P24", "Toàn vẹn và lỗi", "UNIQUE, FK, CHECK, mã lỗi API"),
        ("P25 - P26", "AI và nhật ký", "ai_logs, source_ids, function_name, result_status"),
    ], caption="Đối chiếu yêu cầu và thiết kế dữ liệu", font_size=8.7)
    add_heading(doc, "2.2. Sơ đồ BFD phân rã chức năng", 2)
    add_para(doc, "BFD được vẽ từ danh mục yêu cầu P01 - P26. Sáu nhánh cấp một bao phủ toàn bộ nghiệp vụ; nhánh AI được tách riêng để tránh hiểu nhầm rằng AI là toàn bộ hệ thống.")
    add_figure(doc, "bfd.png", "Hình 2. Sơ đồ BFD (phân rã chức năng)", width=16.0)
    add_table(doc, ["Mã nhánh", "Chức năng cấp một", "Yêu cầu bao phủ", "Đầu ra"], [
        ("F1", "Tài khoản và phân quyền", "P01 - P03", "Người dùng đúng vai trò"),
        ("F2", "Danh mục và sản phẩm", "P04 - P06", "Dữ liệu nền hợp lệ"),
        ("F3", "Chiến dịch và ngân sách", "P07 - P09", "Chiến dịch DRAFT và phân công"),
        ("F4", "Nội dung và lịch đăng", "P10 - P17", "Nội dung được duyệt và lịch"),
        ("F5", "Chỉ số và báo cáo", "P18 - P24", "KPI, dashboard, lỗi và toàn vẹn"),
        ("F6", "Trợ lý AI", "P25 - P26", "Gợi ý, AI_DRAFT và tóm tắt có log"),
    ], caption="Phân rã chức năng theo BFD", font_size=8.8)
    add_heading(doc, "2.3. Bảng SQL nhóm sản phẩm và sản phẩm", 2)
    add_para(doc, "Đây là phần SQL cốt lõi theo yêu cầu của dự án. Bảng products bắt buộc thuộc một product_categories bằng khóa ngoại; giá không âm; tên sản phẩm không rỗng; việc xóa nhóm đang có sản phẩm bị chặn. Hình dưới đây trình bày trực tiếp cấu trúc bảng, kiểu dữ liệu, khóa và ràng buộc.")
    add_figure(doc, "sql_product_tables.png", "Hình 3. Bảng SQL nhóm sản phẩm và sản phẩm", width=16.2)
    add_para(doc, "Giải thích thuộc tính: name là tên hiển thị; description mô tả nhóm; category_id nối sản phẩm với nhóm; usp là điểm bán hàng khác biệt; audience là đối tượng; price phục vụ kiểm soát ngân sách và báo cáo; status cho phép ẩn sản phẩm mà không xóa dữ liệu lịch sử. Lệnh SQL đầy đủ được giữ ở Phụ lục A và trong tệp ddl.sql.")
    add_table(doc, ["Thành phần", "Vai trò", "Áp dụng trong hệ thống"], [
        ("CREATE TABLE", "Khai báo một bảng và các cột dữ liệu.", "Tạo products, campaigns và các bảng nghiệp vụ."),
        ("PRIMARY KEY", "Định danh duy nhất từng dòng.", "Trường id giúp sửa, xóa và liên kết đúng bản ghi."),
        ("FOREIGN KEY ... REFERENCES", "Tạo quan hệ tới bảng cha và ngăn dữ liệu mồ côi.", "products.category_id phải trỏ tới nhóm có thật."),
        ("NOT NULL", "Bắt buộc trường phải có giá trị.", "Tên, mục tiêu, ngày và số liệu cốt lõi không được bỏ trống."),
        ("UNIQUE", "Không cho phép dữ liệu trùng trong phạm vi khai báo.", "Email, tên nhóm/kênh và bộ khóa ngày đo không bị lặp."),
        ("CHECK", "Chặn giá trị không hợp lệ theo điều kiện.", "Giá, ngân sách, chỉ số không âm; trạng thái thuộc tập cho phép."),
        ("DEFAULT", "Điền giá trị mặc định khi không truyền vào.", "Trạng thái mới, số liệu 0 và thời điểm tạo nhất quán."),
        ("JOIN/GROUP BY/CASE", "Nối bảng, tổng hợp và xử lý điều kiện trong truy vấn.", "Lập danh sách và tính KPI mà không chia cho 0."),
    ], caption="Ý nghĩa các thành phần SQL trong thiết kế bảng", font_size=8.2)
    add_heading(doc, "2.4. Mô hình các bảng nghiệp vụ", 2)
    add_para(doc, "Các bảng còn lại được trình bày theo cùng một quy tắc. Mỗi thẻ bảng có đủ tên cột, kiểu dữ liệu, khóa chính (PK), khóa ngoại (FK), giá trị mặc định và ràng buộc kiểm tra; tách theo nhóm để sơ đồ đọc được trên khổ A4.")
    add_figure(doc, "sql_schema_core.png", "Hình 4. Bảng SQL của tài khoản, dữ liệu nền, chiến dịch và nội dung", width=16.0)
    add_figure(doc, "sql_schema_ops.png", "Hình 5. Bảng SQL của lịch đăng, KPI và nhật ký AI", width=16.0)
    add_para(doc, "Cột Ràng buộc trong các thẻ bảng đồng thời là từ điển dữ liệu tối thiểu: nó ghi rõ khóa, bắt buộc, mặc định, tập trạng thái và quan hệ tới bảng cha. Vì vậy người đọc có thể kiểm tra từng thuộc tính ngay trên hình, còn DDL đầy đủ được đối chiếu ở Phụ lục A.")
    add_heading(doc, "2.5. ERD được suy ra từ khóa chính và khóa ngoại", 2)
    add_para(doc, "ERD dưới đây được dựng từ đúng các FOREIGN KEY trong DDL. Mũi tên đi từ bảng cha đến bảng con; vì vậy sơ đồ có thể kiểm tra ngược lại bằng câu lệnh SQL thay vì chỉ là hình minh họa.")
    add_figure(doc, "erd.png", "Hình 6. ERD từ các bảng SQL, khóa chính và khóa ngoại", width=16.3)
    add_table(doc, ["Quan hệ", "Ý nghĩa", "Ràng buộc"], [
        ("product_categories - products", "Một nhóm có nhiều sản phẩm", "products.category_id NOT NULL, ON DELETE RESTRICT"),
        ("products - campaigns", "Một sản phẩm có nhiều chiến dịch", "campaigns.product_id FK"),
        ("users - campaigns", "Manager/owner phụ trách chiến dịch", "campaigns.owner_id FK"),
        ("campaigns - marketing_contents", "Chiến dịch có nhiều nội dung", "marketing_contents.campaign_id FK"),
        ("marketing_channels - contents/metrics", "Kênh dùng cho nội dung và chỉ số", "channel_id FK"),
        ("contents - schedules", "Nội dung được lập lịch", "chỉ APPROVED mới được Python cho tạo lịch"),
        ("campaigns - metrics", "Chiến dịch có số liệu theo ngày/kênh", "UNIQUE campaign_id, channel_id, metric_date"),
        ("users/campaigns - ai_logs", "Truy vết yêu cầu AI", "user_id bắt buộc; campaign_id có thể rỗng"),
    ], caption="Các quan hệ được kiểm chứng từ DDL", font_size=8.5)
    add_heading(doc, "2.6. Truy vấn nghiệp vụ, KPI và kiểm tra toàn vẹn", 2)
    query_sql = """-- Danh sách sản phẩm theo nhóm
SELECT pc.name AS category_name, p.name AS product_name,
       p.usp, p.audience, p.price
FROM product_categories AS pc
JOIN products AS p ON p.category_id = pc.id
WHERE p.status = 'ACTIVE'
ORDER BY pc.name, p.name;

-- Tổng hợp KPI theo chiến dịch và kênh
SELECT c.name AS campaign_name, mc.name AS channel_name,
       SUM(m.views) AS views, SUM(m.clicks) AS clicks,
       SUM(m.conversions) AS conversions, SUM(m.cost) AS cost,
       SUM(m.revenue) AS revenue,
       CASE WHEN SUM(m.views) = 0 THEN 0.0
            ELSE 1.0 * SUM(m.clicks) / SUM(m.views) END AS ctr,
       CASE WHEN SUM(m.cost) = 0 THEN 0.0
            ELSE (SUM(m.revenue) - SUM(m.cost)) / SUM(m.cost) END AS roi
FROM campaign_metrics AS m
JOIN campaigns AS c ON c.id = m.campaign_id
JOIN marketing_channels AS mc ON mc.id = m.channel_id
GROUP BY c.id, mc.id
ORDER BY roi DESC;"""
    add_code(doc, query_sql, caption="SQL 3. JOIN và tính KPI không chia cho 0", size=7.8)
    add_table(doc, ["Kiểm tra", "Câu hỏi", "Kết quả mong đợi"], [
        ("C01", "Tạo sản phẩm với category_id không tồn tại?", "SQLite báo FOREIGN KEY constraint failed"),
        ("C02", "Tạo sản phẩm có price = -1?", "SQLite báo CHECK constraint failed"),
        ("C03", "Tạo hai nhóm cùng name?", "SQLite báo UNIQUE constraint failed"),
        ("C04", "Nhập hai số liệu cùng chiến dịch/kênh/ngày?", "SQLite báo UNIQUE constraint failed"),
        ("C05", "Xóa nhóm còn sản phẩm?", "Không xóa được khi bật foreign_keys"),
        ("C06", "views = 0 khi tính CTR?", "CTR trả về 0.0, không phát sinh lỗi chia 0"),
    ], caption="Kiểm tra toàn vẹn và quy tắc SQL", font_size=8.8)
    add_para(doc, "Kết luận chương: BFD mô tả đủ sáu nhóm chức năng; DDL chứa bảng nhóm sản phẩm, sản phẩm và toàn bộ bảng liên quan; ERD được suy ra từ SQL; các truy vấn đã bao phủ danh sách, KPI và các lỗi toàn vẹn.", bold=True, size=11.5)
    page_break(doc)


def build_chapter3(doc):
    add_heading(doc, "CHƯƠNG 3. THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG PYTHON", 1)
    add_para(doc, "Python là phần xây dựng hệ thống chính: nhận request, xác thực, kiểm tra quyền, kiểm tra dữ liệu, gọi SQL, chuyển trạng thái và trả kết quả. AI chỉ được gọi sau khi Python đã kiểm tra người dùng và context.")
    add_heading(doc, "3.1. Kiến trúc và cấu trúc mã nguồn", 2)
    add_figure(doc, "architecture.png", "Hình 7. Kiến trúc hệ thống Python", width=16.0)
    tree = """app/
+-- main.py                 # khởi tạo FastAPI
+-- core/
|   +-- config.py           # đọc biến môi trường
|   +-- security.py         # mật khẩu băm, JWT, RBAC
+-- db/
|   +-- session.py          # SQLAlchemy session
|   +-- models.py           # ánh xạ bảng SQL
+-- schemas/                # Pydantic request/response
+-- routers/
|   +-- auth.py
|   +-- products.py
|   +-- campaigns.py
|   +-- contents.py
|   +-- reports.py
+-- services/
|   +-- kpi_service.py
|   +-- ai_service.py       # mô-đun AI có giới hạn
+-- tests/                  # ca kiểm thử nghiệp vụ"""
    add_code(doc, tree, caption="Cấu trúc mã nguồn Python đề xuất", size=8.3)
    add_table(doc, ["Lớp", "Nhiệm vụ", "Không được làm"], [
        ("Router/API", "Nhận request, gọi service, trả mã HTTP", "Không tự bỏ qua RBAC"),
        ("Schema", "Kiểm tra kiểu, trường bắt buộc, định dạng", "Không thay thế kiểm tra nghiệp vụ"),
        ("Service", "Kiểm tra trạng thái, nghiệp vụ, tính KPI", "Không ghi dữ liệu ngoài quy trình"),
        ("SQL/ORM", "CRUD, JOIN, transaction, FK", "Không chứa prompt AI"),
        ("AI service", "Gọi model/mock, parse JSON, log kết quả", "Không duyệt, xuất bản, đổi ngân sách"),
    ], caption="Phân lớp của hệ thống Python", font_size=8.8)
    add_heading(doc, "3.2. Đăng nhập và phân quyền", 2)
    auth_code = """from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')

def require_roles(*allowed_roles):
    def dependency(token: str = Depends(oauth2_scheme)):
        user = decode_and_validate_jwt(token)
        if user['role'] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail='Role is not allowed')
        return user
    return dependency

@router.post('/products')
def create_product(payload: ProductCreate,
                   current_user=Depends(require_roles('MANAGER')),
                   db: Session = Depends(get_db)):
    if payload.price < 0:
        raise HTTPException(status_code=422, detail='price must be non-negative')
    category = db.get(ProductCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=422, detail='category does not exist')
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product"""
    add_code(doc, auth_code, caption="Python 1. JWT/RBAC và API tạo sản phẩm", size=7.5)
    add_table(doc, ["Dòng hoặc khối mã", "Ý nghĩa"], [
        ("OAuth2PasswordBearer", "Đọc Bearer token do client gửi trong request."),
        ("decode_and_validate_jwt", "Kiểm tra chữ ký, giải mã token và lấy người dùng."),
        ("Depends(require_roles(...))", "Buộc endpoint kiểm tra xác thực và vai trò trước khi chạy."),
        ("@router.post(...)", "Ánh xạ request HTTP POST vào hàm xử lý tương ứng."),
        ("HTTPException 401/403/422", "Trả lỗi rõ ràng khi sai xác thực, quyền hoặc dữ liệu."),
        ("db.add / commit / refresh", "Ghi bản ghi vào SQL, xác nhận giao dịch và lấy dữ liệu sau khi lưu."),
    ], caption="Ý nghĩa các dòng mã Python trong luồng đăng nhập và phân quyền", font_size=8.6)
    add_para(doc, "Manager được phép quản lý dữ liệu nền; Marketer chỉ được xem dữ liệu trong phạm vi được phân công và thao tác nội dung. Kiểm tra quyền nằm ở backend, nên việc ẩn nút trên giao diện không được coi là biện pháp bảo mật duy nhất.")
    add_heading(doc, "3.3. CRUD nhóm sản phẩm và sản phẩm", 2)
    add_table(doc, ["Endpoint", "Vai trò", "Xử lý chính", "Mã lỗi"], [
        ("POST /categories", "MANAGER", "Tên không trùng, tạo nhóm", "401, 403, 409, 422"),
        ("GET /categories", "Cả hai", "Danh sách, search, pagination", "401, 422"),
        ("POST /products", "MANAGER", "Kiểm tra FK, giá, tên theo nhóm", "401, 403, 409, 422"),
        ("PATCH /products/{id}", "MANAGER", "Sửa thuộc tính, ghi updated_at", "401, 403, 404, 422"),
        ("DELETE /products/{id}", "MANAGER", "Chặn nếu campaign phụ thuộc", "401, 403, 404, 409"),
    ], caption="API CRUD nhóm sản phẩm và sản phẩm", font_size=8.7)
    add_heading(doc, "3.4. Quy trình chiến dịch, nội dung, lịch và chỉ số", 2)
    add_table(doc, ["Đối tượng", "Trạng thái", "Chuyển tiếp hợp lệ", "Ai thực hiện"], [
        ("Campaign", "DRAFT", "DRAFT -> ACTIVE -> PAUSED -> CLOSED", "Manager"),
        ("Content", "DRAFT", "DRAFT -> PENDING", "Marketer"),
        ("Content", "AI_DRAFT", "AI_DRAFT -> PENDING", "Marketer sau khi sửa"),
        ("Content", "PENDING", "PENDING -> APPROVED hoặc REJECTED", "Manager"),
        ("Content", "REJECTED", "REJECTED -> DRAFT -> PENDING", "Marketer"),
        ("Content", "APPROVED", "APPROVED -> lịch PLANNED", "Người có quyền"),
        ("Schedule", "PLANNED", "PLANNED -> CANCELLED hoặc EXECUTED", "Người có quyền"),
    ], caption="Quy tắc trạng thái nghiệp vụ", font_size=8.5)
    add_para(doc, "Python kiểm tra chuyển trạng thái ở service layer. Ví dụ: không cho tạo lịch nếu content.status khác APPROVED; không cho Manager duyệt content do chính mình tạo nếu quy tắc nhóm yêu cầu tách người soạn và người duyệt; từ chối phải có rejection_reason.")
    add_heading(doc, "3.5. Tìm kiếm, KPI, giao diện và xử lý lỗi", 2)
    search_code = """def list_products(db, q='', category_id=None, page=1, page_size=20):
    stmt = select(Product).where(Product.status == 'ACTIVE')
    if q:
        stmt = stmt.where(Product.name.ilike(f'%{q}%'))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    stmt = stmt.order_by(Product.name).offset((page - 1) * page_size)
    return db.execute(stmt.limit(page_size)).scalars().all()

def kpi(views, clicks, conversions, cost, revenue):
    ctr = clicks / views if views else 0.0
    cpc = cost / clicks if clicks else 0.0
    cpa = cost / conversions if conversions else 0.0
    roi = (revenue - cost) / cost if cost else 0.0
    return {'ctr': ctr, 'cpc': cpc, 'cpa': cpa, 'roi': roi}"""
    add_code(doc, search_code, caption="Python 2. Tìm kiếm, phân trang và công thức KPI", size=7.6)
    add_table(doc, ["Màn hình", "Manager", "Marketer"], [
        ("Dashboard", "Toàn bộ chiến dịch, KPI và tóm tắt", "Chiến dịch được giao"),
        ("Danh mục", "CRUD nhóm/sản phẩm/kênh", "Xem và tìm kiếm"),
        ("Chiến dịch", "Tạo, ngân sách, phân công, duyệt", "Xem và cập nhật phần được giao"),
        ("Nội dung", "Duyệt/từ chối, xem nguồn", "Soạn/sửa/gửi, gọi AI"),
        ("AI log", "Xem nhật ký và trạng thái", "Xem yêu cầu của mình"),
    ], caption="Giao diện theo vai trò", font_size=8.8)
    add_table(doc, ["Tình huống", "Mã", "Phản hồi người dùng"], [
        ("Thiếu trường hoặc sai kiểu", "422", "Kiểm tra lại dữ liệu nhập"),
        ("Chưa đăng nhập", "401", "Vui lòng đăng nhập"),
        ("Không đủ quyền", "403", "Vai trò hiện tại không được phép"),
        ("Không tìm thấy bản ghi", "404", "Dữ liệu không tồn tại"),
        ("Trùng tên hoặc vi phạm FK", "409", "Không thể lưu vì xung đột dữ liệu"),
        ("Lỗi dịch vụ AI/DB", "500/503", "Đã ghi log; thử lại hoặc dùng thao tác thủ công"),
    ], caption="Mã lỗi và cách phản hồi", font_size=8.8)
    add_heading(doc, "3.6. Kiểm thử và minh chứng", 2)
    tests = [
        ("TC01", "Đăng nhập Manager đúng", "JWT role=MANAGER"),
        ("TC02", "Đăng nhập sai mật khẩu", "401"),
        ("TC03", "Marketer gọi POST /products", "403"),
        ("TC04", "Tài khoản bị khóa đăng nhập", "403"),
        ("TC05", "Tạo nhóm sản phẩm hợp lệ", "201 và id"),
        ("TC06", "Tạo nhóm trùng tên", "409"),
        ("TC07", "Tạo sản phẩm đúng category", "201 và FK đúng"),
        ("TC08", "Tạo sản phẩm giá âm", "422"),
        ("TC09", "Xóa category còn product", "409/FK"),
        ("TC10", "Tạo campaign ngày hợp lệ", "DRAFT"),
        ("TC11", "Tạo campaign ngày ngược", "422"),
        ("TC12", "Marketer gửi content đủ trường", "PENDING"),
        ("TC13", "Manager duyệt content", "APPROVED"),
        ("TC14", "Lập lịch content chưa duyệt", "422"),
        ("TC15", "Nhập metric âm", "422"),
        ("TC16", "Tính KPI views=0/cost=0", "0.0, không lỗi"),
        ("TC17", "Tìm kiếm và phân trang", "Kết quả đúng page/size"),
        ("TC18", "Marketer gọi AI tạo nháp", "AI_DRAFT + source_ids"),
        ("TC19", "AI timeout", "Fallback + ai_logs FAILED"),
        ("TC20", "Manager xem tóm tắt KPI", "Summary + log, không đổi dữ liệu"),
    ]
    add_table(doc, ["Mã", "Ca kiểm thử", "Kết quả mong đợi"], tests, caption="Danh sách ca kiểm thử từ nghiệp vụ đến AI", font_size=8.15)
    add_para(doc, "Các giá trị trong bảng là kết quả mong đợi của kế hoạch kiểm thử, chưa phải xác nhận chạy thật. Khi nộp cần thay bằng ảnh hoặc log có ngày chạy, phiên bản mã nguồn và người xác nhận.", indent=False, size=10.5)
    add_para(doc, "Minh chứng cần đính kèm khi demo: ảnh đăng nhập theo hai vai trò; ảnh CRUD nhóm/sản phẩm; ảnh chiến dịch và phân công; ảnh nội dung từ DRAFT đến APPROVED; ảnh lịch; ảnh dashboard/KPI; log AI có source_ids; terminal chạy ddl.sql và kết quả kiểm thử.")
    add_para(doc, "Kết luận chương: Python kiểm soát toàn bộ luồng chính và gọi SQL theo quy tắc. Quyền người dùng, trạng thái nội dung, KPI và lỗi đều được xử lý trước khi hiển thị. Đây là phần hệ thống; AI được tách thành service riêng ở Chương 4.", bold=True, size=11.5)


def build_chapter4(doc):
    add_heading(doc, "CHƯƠNG 4. XÁC ĐỊNH VÀ TÍCH HỢP AI ĐÚNG PHẠM VI", 1)
    add_para(doc, "Phần này trả lời trực tiếp câu hỏi: AI nằm ở đâu, nhận dữ liệu gì, làm nhiệm vụ gì và không được làm gì. AI là mô-đun hỗ trợ trong hệ thống Python, không phải người quản lý nghiệp vụ.")
    add_heading(doc, "4.1. AI nằm ở đâu trong hệ thống", 2)
    add_para(doc, "Vị trí mã nguồn: app/services/ai_service.py. Python gọi mô-đun này sau khi kiểm tra JWT/RBAC, lấy context từ SQL và loại bỏ dữ liệu không cần thiết. Kết quả được parse, gắn source_ids, lưu vào marketing_contents hoặc ai_logs, rồi trả về cho người dùng kiểm tra.")
    add_figure(doc, "ai_flow.png", "Hình 8. Vị trí AI trong quy trình marketing", width=16.0)
    add_table(doc, ["Bước", "Thành phần", "Nhiệm vụ", "Kết quả"], [
        ("1", "SQL", "Lưu sản phẩm, mục tiêu, kênh và KPI", "Context có nguồn"),
        ("2", "Python", "Kiểm tra quyền, chọn trường và dựng prompt", "Request hợp lệ"),
        ("3", "AI service", "Gọi model/mock, yêu cầu JSON, parse kết quả", "Gợi ý/bản nháp/tóm tắt"),
        ("4", "Python + SQL", "Lưu source_ids, status và ai_logs", "Có thể truy vết"),
        ("5", "Con người", "Marketer sửa; Manager duyệt", "Nội dung được dùng"),
    ], caption="Luồng xử lý AI trong hệ thống", font_size=8.7)
    add_heading(doc, "4.2. Ba nhiệm vụ AI được phép thực hiện", 2)
    add_table(doc, ["Mã", "Nhiệm vụ", "Dữ liệu vào", "Đầu ra", "Người kiểm tra"], [
        ("AI01", "Gợi ý ý tưởng", "Sản phẩm, USP, audience, mục tiêu, kênh", "3 - 5 ý tưởng có lý do", "Marketer"),
        ("AI02", "Tạo bản nháp", "Ý tưởng đã chọn, format_rules, CTA, giới hạn kênh", "title, body, cta, source_ids", "Marketer rồi Manager"),
        ("AI03", "Tóm tắt KPI", "Views, clicks, conversions, cost, revenue và KPI đã tính", "Nhận xét xu hướng và câu hỏi cần xem", "Manager"),
    ], caption="Phạm vi nhiệm vụ AI", font_size=8.3)
    page_break(doc)
    add_table(doc, ["AI được làm", "AI không được làm"], [
        ("Gợi ý ý tưởng theo context sản phẩm và kênh", "Cấp quyền, đổi vai trò hoặc sửa dữ liệu người dùng"),
        ("Tạo bản nháp có trạng thái AI_DRAFT", "Duyệt nội dung, tự chuyển APPROVED hoặc tự xuất bản"),
        ("Tóm tắt KPI đã truy vấn", "Đổi ngân sách, công thức KPI hoặc dữ liệu SQL"),
        ("Trả JSON và ghi log thành công/thất bại", "Tự lập lịch, tự xuất bản nội dung hoặc thay người chịu trách nhiệm"),
    ], caption="Ranh giới trách nhiệm của AI", font_size=8.6)
    add_heading(doc, "4.3. Prompt, dữ liệu nền và kiểm duyệt", 2)
    prompt_code = """SYSTEM:
Bạn là trợ lý marketing. Chỉ dùng dữ liệu trong CONTEXT.
Không tự bịa thuộc tính sản phẩm, số liệu hoặc chính sách.
Trả JSON đúng schema; nếu thiếu dữ liệu, trả needs_review=true.
Bạn không có quyền duyệt, xuất bản, đổi ngân sách hay cấp quyền.

USER:
Nhiệm vụ: tạo bản nháp cho kênh {channel_name}.
Mục tiêu: {objective}
CONTEXT từ SQL:
{product_name} | USP: {usp} | Audience: {audience}
Format rules: {format_rules}

OUTPUT JSON:
{"title":"...","body":"...","cta":"...",
 "source_ids":["product:{product_id}","channel:{channel_id}"],
 "needs_review":true}"""
    add_code(doc, prompt_code, caption="AI 1. Prompt có context, schema và giới hạn trách nhiệm", size=7.4)
    add_para(doc, "Các trường được phép đưa vào context gồm product.name, usp, audience, campaign.objective, marketing_channels.format_rules và các KPI đã tính. Không đưa password_hash, token, khóa bí mật hoặc dữ liệu không liên quan vào prompt.")
    add_para(doc, "Quy trình người trong vòng kiểm duyệt:")
    numbered(doc, [
        "Marketer chọn chiến dịch, kênh và sản phẩm; Python kiểm tra quyền và lấy dữ liệu SQL.",
        "AI trả gợi ý hoặc bản nháp; Python kiểm tra JSON, độ dài, trường bắt buộc và source_ids.",
        "Marketer đọc và sửa bản nháp; khi gửi duyệt, trạng thái chuyển PENDING.",
        "Manager kiểm tra nội dung, đối chiếu sản phẩm và quyết định APPROVED hoặc REJECTED kèm lý do.",
        "Chỉ nội dung APPROVED mới được lập lịch; AI không có nút hoặc endpoint để vượt bước này.",
    ])
    add_heading(doc, "4.4. Lỗi, nhật ký và thử nghiệm mẫu", 2)
    add_table(doc, ["Tình huống", "Xử lý Python", "Ai_logs"], [
        ("Thiếu context", "Không gọi model; báo needs_review", "FAILED - MISSING_CONTEXT"),
        ("Model timeout", "Fallback bản nháp rỗng hoặc cho soạn thủ công", "FAILED - TIMEOUT"),
        ("Model trả sai JSON", "Không lưu content; yêu cầu thử lại", "FAILED - INVALID_JSON"),
        ("Nội dung vượt quy tắc kênh", "Gắn needs_review; không gửi duyệt tự động", "SUCCESS - NEEDS_REVIEW"),
        ("Tóm tắt không khớp số liệu", "Hiển thị số liệu gốc và cảnh báo", "SUCCESS - REVIEW_REQUIRED"),
    ], caption="Ma trận lỗi AI", font_size=8.6)
    add_table(doc, ["Vòng", "Cách thử", "Chỉ số cần ghi khi chạy", "Điều kiện quyết định"], [
        ("R1", "Prompt tự do, không schema", "Thời gian, lỗi trường và lỗi nội dung", "Ghi lỗi làm cơ sở sửa prompt"),
        ("R2", "Có context và schema JSON", "Thời gian, tỷ lệ parse và số timeout", "Không dùng output thiếu trường"),
        ("R3", "Thêm source_ids, whitelist và needs_review", "Nguồn, tỷ lệ parse, timeout và số lần sửa", "Chỉ dùng sau khi parse và có người duyệt"),
    ], caption="Thử nghiệm prompt trên dữ liệu mẫu nội bộ", font_size=8.5)
    add_para(doc, "Ba vòng trên là kế hoạch đo phục vụ đánh giá thiết kế, chưa phải số liệu đã chạy. Khi triển khai thật cần điền log theo kênh, ngôn ngữ, chính sách nội dung và dữ liệu thực tế; không tự điền số liệu nếu chưa có bằng chứng.")
    add_code(doc, """def generate_draft(user, campaign_id, channel_id, db, ai_provider, prompt_version):
    require_role(user, 'MARKETER')
    context = load_grounded_context(campaign_id, channel_id, db)
    if not context:
        write_ai_log(user.id, campaign_id, 'draft', 'FAILED', 'MISSING_CONTEXT')
        return {'status': 'NEEDS_REVIEW', 'draft': None}
    result = call_model_with_timeout(build_prompt(context), seconds=20)
    parsed = parse_json_or_none(result)
    if parsed is None:
        write_ai_log(user.id, campaign_id, 'draft', 'FAILED', 'INVALID_JSON')
        return {'status': 'NEEDS_REVIEW', 'draft': None}
    content = save_content(ai_provider=ai_provider,
                           prompt_version=prompt_version,
                           status='AI_DRAFT',
                           source_ids=parsed['source_ids'], db=db)
    write_ai_log(user.id, campaign_id, 'draft', 'SUCCESS', 'AI_DRAFT')
    return content""", caption="Python 3. AI service có kiểm tra, fallback và log", size=7.4)
    add_table(doc, ["Công việc", "AI hỗ trợ", "Nhóm kiểm tra lại"], [
        ("Phân tích nghiệp vụ", "Gợi ý nhóm chức năng quản lý marketing.", "Đối chiếu danh mục P01 - P26 và hai actor."),
        ("Thiết kế CSDL", "Gợi ý quan hệ sản phẩm - chiến dịch - nội dung.", "Viết DDL, thêm PK/FK/CHECK và chạy dữ liệu sai."),
        ("Viết service Python", "Gợi ý cấu trúc router/service.", "Đối chiếu quyền, trạng thái, lỗi HTTP và ca kiểm thử."),
        ("Rà soát mã nguồn", "Gợi ý phát hiện lỗi ở RBAC, trạng thái và ngoại lệ.", "Chạy lại test, đối chiếu DDL và kiểm tra thủ công trước khi chấp nhận."),
    ], caption="Minh chứng AI hỗ trợ phân tích, thiết kế và rà soát mã nguồn", font_size=8.5)
    add_para(doc, "Nhật ký ai_logs cần lưu user_id, campaign_id, function_name, provider, prompt_version, source_ids, result_status và created_at. Nhờ đó có thể trả lời ai gọi AI, gọi cho chiến dịch nào, dùng phiên bản prompt nào và kết quả có được dùng hay không.")
    add_para(doc, "Kết luận AI: AI chỉ gợi ý, tạo bản nháp và tóm tắt. Python/SQL kiểm soát quyền, dữ liệu, trạng thái, KPI và log; Marketer sửa, Manager duyệt.", bold=True, size=11.5)


def build_chapter5(doc):
    add_heading(doc, "CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", 1)
    add_heading(doc, "5.1. Kết quả đạt được", 2)
    add_table(doc, ["Nội dung", "Kết quả trong báo cáo", "Minh chứng"], [
        ("Khảo sát", "Xác định Manager, Marketer, hệ thống Python, AI service và mã yêu cầu P01 - P26", "Chương 1"),
        ("BFD", "Sáu nhánh cấp một bao phủ tài khoản, dữ liệu, chiến dịch, nội dung, báo cáo, AI", "Hình 2"),
        ("SQL", "Có DDL nhóm sản phẩm, sản phẩm và bảy nhóm bảng liên quan", "Chương 2, Phụ lục A, ddl.sql"),
        ("ERD", "Sơ đồ suy ra từ PK/FK trong DDL", "Hình 6"),
        ("Python", "API, RBAC, CRUD, trạng thái, KPI, tìm kiếm, lỗi và 20 ca kiểm thử", "Chương 3"),
        ("AI", "Ba nhiệm vụ, vị trí ai_service.py, prompt, source_ids, HITL, fallback, log", "Chương 4"),
    ], caption="Đối chiếu kết quả với yêu cầu của dự án", font_size=8.6)
    add_para(doc, "Báo cáo đã đi theo mạch: yêu cầu nghiệp vụ -> BFD -> SQL -> ERD -> Python -> AI -> kiểm thử. Vì vậy thiết kế có thể giải thích được bằng tài liệu và tài liệu có thể kiểm tra ngược bằng mã nguồn minh họa, DDL và sơ đồ.")
    add_heading(doc, "5.2. Hạn chế", 2)
    compact_numbered(doc, [
        "Chưa kết nối trực tiếp các API xuất bản nội dung của từng nền tảng; lịch hiện được quản lý trong hệ thống.",
        "Số liệu KPI và thử nghiệm AI trong báo cáo là dữ liệu mẫu; cần đánh giá lại bằng dữ liệu thật.",
        "Chưa trình bày ảnh chụp toàn bộ màn hình sản phẩm trong tài liệu; checklist ở Chương 3 cho biết ảnh cần bổ sung khi demo.",
        "SQLite phù hợp cho bản mẫu trên một máy; nếu cần SQL Server hoặc nhiều người dùng, phải xác nhận hệ quản trị, chuyển DDL và dựng lại sơ đồ trước khi bàn giao.",
    ])
    add_heading(doc, "5.3. Hướng phát triển", 2)
    compact_numbered(doc, [
        "Bổ sung dashboard biểu đồ theo ngày, kênh, chiến dịch và cảnh báo KPI bất thường.",
        "Thêm hàng đợi tác vụ, retry có giới hạn và cache cho yêu cầu AI.",
        "Bổ sung kiểm duyệt nội dung theo chính sách từng kênh và danh sách từ khóa bị cấm.",
        "Thêm audit log cho mọi thay đổi ngân sách, trạng thái và quyền người dùng.",
        "Đóng gói Docker, CI kiểm thử DDL/API và triển khai cơ sở dữ liệu phù hợp với quy mô thật.",
    ])
    add_para(doc, "Các hướng phát triển vẫn giữ nguyên nguyên tắc của đề tài: nghiệp vụ và dữ liệu là nền tảng; Python điều phối quy trình; SQL bảo đảm tính toàn vẹn; AI hỗ trợ tại điểm phù hợp và luôn có người kiểm tra.")
    add_para(doc, "Kết luận: hệ thống được xây dựng trên Python và SQL; AI được tích hợp như trợ lý có kiểm soát. Cách tách vai trò này giúp hệ thống rõ trách nhiệm, dễ kiểm thử và phù hợp với yêu cầu đánh giá cả báo cáo lẫn sản phẩm.", bold=True, size=11.5)
    add_heading(doc, "5.4. Kịch bản demo và bàn giao", 2)
    compact_numbered(doc, [
        "Khởi động CSDL và ứng dụng Python theo README; kiểm tra tài khoản Manager và Marketer.",
        "Manager tạo nhóm sản phẩm, sản phẩm, kênh, chiến dịch và phân công người phụ trách.",
        "Marketer tạo nội dung, gọi AI để nhận bản nháp có source_ids, chỉnh sửa và gửi duyệt.",
        "Manager duyệt nội dung, lập lịch; sau đó nhập số liệu và mở dashboard KPI.",
        "Mở log AI, ca kiểm thử, DDL và cấu hình mẫu để chứng minh dữ liệu, quyền, lỗi và kết quả có thể truy vết.",
    ])
    page_break(doc)


def build_references(doc):
    add_heading(doc, "TÀI LIỆU THAM KHẢO", 1)
    add_para(doc, "Các tài liệu sau được dùng để đối chiếu cách thiết kế kỹ thuật; phần nghiệp vụ, thuộc tính và quy trình là lựa chọn của nhóm cho đề tài này.", indent=False)
    refs = [
        ("[1]", "FastAPI Documentation - OAuth2 with Password and JWT", "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/"),
        ("[2]", "Pydantic Documentation - Settings Management", "https://docs.pydantic.dev/latest/concepts/pydantic_settings/"),
        ("[3]", "SQLite Documentation - Write-Ahead Logging", "https://www.sqlite.org/wal.html"),
        ("[4]", "OWASP Cheat Sheet Series - Password Storage", "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"),
        ("[5]", "SQLite Documentation - SQL Language and Foreign Key Support", "https://www.sqlite.org/foreignkeys.html"),
        ("[6]", "Microsoft Learn - Design Database Diagrams", "https://learn.microsoft.com/en-us/ssms/visual-db-tools/design-database-diagrams-visual-database-tools"),
        ("[7]", "Microsoft Learn - Transact-SQL Language Reference", "https://learn.microsoft.com/en-us/sql/t-sql/language-reference?view=sql-server-ver17"),
    ]
    for code, title, url in refs:
        add_para(doc, f"{code} {title}", indent=False, size=11)
        add_url(doc, "Liên kết", url)
    page_break(doc)


def build_appendix(doc):
    add_heading(doc, "PHỤ LỤC A. DDL, TRẠNG THÁI VÀ CHECKLIST MINH CHỨNG", 1)
    add_para(doc, "File ddl.sql đi kèm thư mục báo cáo chứa DDL đầy đủ. Phần dưới đây chèn lại toàn bộ nội dung để giảng viên có thể xem trực tiếp trong báo cáo và chạy độc lập trên SQLite. Nếu chuyển sang SQL Server, phải tạo bản T-SQL riêng và cập nhật lại sơ đồ.", indent=False)
    add_heading(doc, "A.1. Ma trận đối chiếu tiêu chí môn học và minh chứng", 2)
    add_para(doc, "Ma trận dùng để kiểm toán báo cáo trước khi nộp. ‘Đã mô tả’ chỉ nghĩa là nội dung đã có trong tài liệu; ‘Cần minh chứng’ phải được thay bằng ảnh chụp, log, mã nguồn hoặc kết quả chạy thật. Không ghi ‘Đạt’ nếu chưa có bằng chứng tương ứng.", indent=False, size=10.5)
    criteria = [
        ("KT1-01", "Phân tích bối cảnh, người dùng, dữ liệu và quy trình nghiệp vụ", "Chương 1, mục 1.1 - 1.4", "Đã mô tả"),
        ("KT1-02", "Liệt kê chức năng, đầu vào, xử lý và đầu ra", "Chương 1, yêu cầu chức năng", "Đã mô tả"),
        ("KT1-03", "Yêu cầu phi chức năng: bảo mật, hiệu năng, dễ dùng, sao lưu và RBAC", "Chương 1, NFR; Phụ lục A", "Thiết kế; cần đo"),
        ("KT1-04", "Xác định actor, Use Case và mô hình tương tác", "Chương 1, ma trận quyền và Hình 1", "Đã mô tả"),
        ("KT1-05", "Thiết kế CSDL, ERD, bảng, PK, FK và ràng buộc", "Chương 2, DDL và Hình 2 - 6", "DDL đã chạy"),
        ("KT1-06", "Thiết kế kiến trúc frontend, backend, database, AI và luồng dữ liệu", "Chương 3, mục 3.1 - 3.2, Hình 7", "Thiết kế"),
        ("KT1-07", "Xác định vị trí AI gắn với dữ liệu và nhu cầu thực tế", "Chương 4, mục 4.1, Hình 8", "Đã mô tả"),
        ("KT1-08", "Thiết kế system prompt, user prompt, input, output và giới hạn", "Chương 4, mục 4.3", "Thiết kế"),
        ("KT1-09", "Chứng minh AI hỗ trợ phân tích và thiết kế; có nhận xét của nhóm", "Chương 4, mục 4.9 và nhật ký prompt", "Cần lưu prompt gốc"),
        ("KT1-10", "Tài liệu phân tích, thiết kế và kế hoạch triển khai bước tiếp theo", "Chương 1 - 5 và checklist", "Đã mô tả"),
        ("KT2-01", "Cấu trúc dự án frontend, backend, database, config và docs hợp lý", "Chương 3, mục 3.3; cây thư mục mẫu", "Mẫu; cần source"),
        ("KT2-02", "Đăng nhập và phân quyền theo vai trò", "Chương 3, mục 3.4; mã Python minh họa", "Cần ảnh/log"),
        ("KT2-03", "CRUD các nghiệp vụ chính", "Chương 3, mục 3.5; API mẫu", "Cần ảnh/log"),
        ("KT2-04", "Tìm kiếm, lọc và sắp xếp dữ liệu", "Chương 3, mục 3.6; tham số truy vấn", "Thiết kế; cần chạy"),
        ("KT2-05", "Thống kê, báo cáo hoặc dashboard phục vụ nghiệp vụ", "Chương 3, mục 3.6 và KPI", "Cần ảnh chạy"),
        ("KT2-06", "Giao diện rõ ràng, phản hồi lỗi và trạng thái dễ hiểu", "Chương 3, mục 3.7; bảng giao diện", "Cần ảnh chạy"),
        ("KT2-07", "CSDL ổn định, dữ liệu mẫu và seed có thể tạo lại", "Chương 2 và Phụ lục A, DDL", "DDL OK; seed cần"),
        ("KT2-08", "Xử lý input sai, dữ liệu thiếu, lỗi truy vấn và lỗi phân quyền", "Chương 3, mục 3.8 và ma trận lỗi", "Thiết kế; cần test"),
        ("KT2-09", "Minh chứng AI được dùng khi lập trình", "Chương 4, bảng nhật ký hỗ trợ phát triển", "Cần log thật"),
        ("KT2-10", "README, hướng dẫn cài đặt, env.example và phiên bản mã nguồn", "Checklist và hồ sơ bàn giao", "Cần tệp bàn giao"),
        ("KT3-01", "AI được tích hợp để phục vụ nghiệp vụ trong hệ thống", "Chương 4, mục 4.1 - 4.2", "Thiết kế; cần chạy"),
        ("KT3-02", "Kết nối API/model và quản lý API key bằng môi trường", "Chương 4, mục 4.6; env.example", "Cần provider"),
        ("KT3-03", "Tách system/user prompt, định dạng và kiểm tra output", "Chương 4, mục 4.3", "Đã thiết kế"),
        ("KT3-04", "Có ít nhất ba vòng thử prompt hoặc so sánh model", "Chương 4, mục 4.8; mẫu kế hoạch đo", "Cần log thật"),
        ("KT3-05", "AI dùng dữ liệu hệ thống qua truy vấn và kiểm soát quyền", "Chương 4, mục 4.4; whitelist context", "Đã thiết kế"),
        ("KT3-06", "Kết quả AI dễ đọc, đúng định dạng và có cảnh báo", "Chương 4, mục 4.2 và 4.5", "Thiết kế"),
        ("KT3-07", "Xử lý timeout, rate limit, dữ liệu rỗng, JSON sai và model lỗi", "Chương 4, mục 4.7; ma trận lỗi", "Thiết kế; cần test"),
        ("KT3-08", "Kiểm thử chức năng quản lý và chức năng AI", "Chương 3, bộ 20 ca; Chương 4", "Chưa chạy"),
        ("KT3-09", "AI hỗ trợ review code và nhóm kiểm tra lại kết quả", "Chương 4, mục 4.9", "Cần bằng chứng"),
        ("KT3-10", "AI được tích hợp vào UX hữu ích, không lẫn với quyền quản lý", "Chương 4, mục 4.5; Hình 8", "Thiết kế; cần ảnh"),
        ("CK-01", "Chức năng hoàn chỉnh, ổn định và dùng được", "Chương 3, Chương 5 và bộ kiểm thử", "Chưa xác nhận"),
        ("CK-02", "Chất lượng mã nguồn: rõ ràng, module hóa và bảo trì được", "Chương 3, cấu trúc Python và checklist", "Thiết kế"),
        ("CK-03", "Chất lượng CSDL: nhất quán, ràng buộc, sao lưu và khôi phục", "Chương 2, DDL và Phụ lục A", "DDL OK; cần restore"),
        ("CK-04", "Chất lượng giao diện và trải nghiệm người dùng", "Chương 3, mục 3.7; ảnh màn hình", "Cần ảnh"),
        ("CK-05", "Chất lượng AI: đúng context, kiểm soát, cảnh báo và có người duyệt", "Chương 4 toàn bộ", "Thiết kế; cần đo"),
        ("CK-06", "Bảo mật, quyền riêng tư, phân quyền và bảo vệ API key", "Chương 1, 3, 4 và env.example", "Thiết kế; cần test"),
        ("CK-07", "Hiệu năng, ổn định, retry, fallback và không mất dữ liệu", "Chương 3 - 4, NFR và ma trận lỗi", "Thiết kế; cần đo"),
        ("CK-08", "Triển khai, đóng gói, README, dữ liệu mẫu và demo", "Phụ lục A, checklist bàn giao", "Cần tệp"),
        ("CK-09", "Báo cáo kỹ thuật đầy đủ về phân tích, thiết kế, triển khai và AI", "Toàn bộ báo cáo, DDL và minh chứng", "Đã trình bày"),
        ("CK-10", "Thuyết trình và demo mạch lạc, trả lời được câu hỏi", "Chương 5, kịch bản demo và bàn giao", "Cần demo thật"),
    ]
    add_table(doc, ["Mã", "Tiêu chí", "Vị trí hoặc minh chứng", "Trạng thái"], criteria, caption="Ma trận đối chiếu tiêu chí môn học và minh chứng", font_size=7.2)
    add_para(doc, "Các trạng thái trong ma trận là điểm kiểm toán của hồ sơ, không phải điểm số. Trước khi nộp, thay những mục ‘Cần...’ bằng minh chứng thực tế hoặc ghi rõ phần đó là kế hoạch.", indent=False, size=10.2)
    add_heading(doc, "A.2. Cách chạy DDL và dữ liệu mẫu", 2)
    add_para(doc, "Tạo môi trường Python, cài dependency, sao chép .env.example thành .env, chạy DDL và seed dữ liệu mẫu theo README. Không đưa secret thật vào tệp hoặc nhật ký.", indent=False, size=10.5)
    add_heading(doc, "A.3. DDL đầy đủ", 2)
    ddl_path = ROOT / "ddl.sql"
    if ddl_path.exists():
        add_code(doc, ddl_path.read_text(encoding="utf-8"), caption="DDL đầy đủ của hệ thống", size=6.8)
    add_heading(doc, "A.4. Quy tắc trạng thái", 2)
    add_table(doc, ["Đối tượng", "Trạng thái", "Điều kiện"], [
        ("Campaign", "DRAFT", "Mới tạo; Manager còn chỉnh sửa"),
        ("Campaign", "ACTIVE/PAUSED/CLOSED", "Theo thời gian và quyết định Manager"),
        ("Content", "DRAFT/AI_DRAFT", "Marketer còn sửa; AI_DRAFT phải có nguồn"),
        ("Content", "PENDING", "Đủ title/body, Marketer gửi duyệt"),
        ("Content", "APPROVED/REJECTED", "Manager quyết định; REJECTED phải có lý do"),
        ("Schedule", "PLANNED", "Chỉ content APPROVED"),
        ("Schedule", "CANCELLED/EXECUTED", "Hủy hoặc ghi nhận đã thực hiện"),
    ], caption="Bảng trạng thái dùng để kiểm thử", font_size=8.8)
    add_heading(doc, "A.5. Checklist trước khi nộp", 2)
    checklist = [
        "Trang bìa có trường, học phần, hình thức, mã số 80300, giảng viên, nhóm và sinh viên.",
        "Mục lục ghi rõ năm chương và điểm bắt đầu của từng chương.",
        "Chương 1 liệt kê đủ mã yêu cầu P01 - P26 và phân biệt Manager với Marketer.",
        "Chương 2 có BFD, SQL product_categories/products, DDL đầy đủ và ERD.",
        "Chương 3 chứng minh Python là phần lõi, có RBAC, CRUD, KPI, trạng thái và test.",
        "Chương 4 chỉ rõ ai_service.py, ba nhiệm vụ AI, nguồn context, kiểm duyệt và giới hạn.",
        "Chạy ddl.sql thành công; kiểm tra khóa ngoại, giá âm, dữ liệu trùng và chia cho 0; chỉ ghi Đạt khi có ảnh hoặc log chạy thật.",
    ]
    for item in checklist:
        p = add_bullet(doc, item)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(0)
    page_break(doc)


def main():
    doc = Document()
    style_document(doc)
    setup_sections(doc)
    build_cover(doc)
    build_contents(doc)
    build_introduction(doc)
    build_chapter1(doc)
    build_chapter2(doc)
    build_chapter3(doc)
    build_chapter4(doc)
    build_chapter5(doc)
    build_references(doc)
    build_appendix(doc)
    build_rubric(doc)
    build_acknowledgment(doc)
    build_commitment(doc)
    build_abbreviations(doc)
    doc.save(OUT)
    print("Created DOCX successfully")


if __name__ == "__main__":
    main()
