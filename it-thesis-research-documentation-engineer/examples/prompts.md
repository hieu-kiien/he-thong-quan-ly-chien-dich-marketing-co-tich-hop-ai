# Example Prompts

## 1. Full thesis visual audit

Dùng IT Thesis LaTeX Visual Designer ở THESIS_LATEX_PRINT_MODE + RESEARCH_GRADE_VISUAL_MODE. Đọc toàn bộ project. Trước tiên lập Visual Coverage Map. Với từng hình hiện có, xác định câu hỏi kỹ thuật, source evidence, notation, editable source, vector/raster, print risk và semantic risk. Không thêm hình chỉ để tăng số lượng. Sau đó sửa các hình priority=high, compile PDF và audit lại.

## 2. Architecture from repository

Đọc source tree, dependencies, environment/config, API routes và deployment files. Xác định cái nào IMPLEMENTED, cái nào chỉ PROPOSED. Nếu phù hợp, tạo System Context trước rồi Container view. Không đưa database tables vào Context. Mọi arrow phải có ý nghĩa; container-to-container relationship ghi protocol/technology nếu source chứng minh được. Xuất source + PDF vector + manifest.

## 3. ERD from SQL

Dùng DDL/migrations làm source of truth. Tạo Physical ERD. PK, FK, NOT NULL, UNIQUE phải ảnh hưởng đúng đến khóa, cardinality và optionality. Nếu một schema toàn phần không thể đọc ở A4 với font >=9pt, tách theo bounded context và thêm một overview quan hệ giữa các nhóm.

## 4. Sequence from feature

Tạo Sequence Diagram cho luồng thanh toán/AI/login từ code thật. Bao gồm lỗi/timeout/retry/approval bằng alt/opt/loop nếu code có. Nếu report mô tả khác code, báo inconsistency trước khi vẽ.

## 5. Experimental plot

Từ file CSV thật, chọn biểu đồ trả lời câu hỏi nghiên cứu, không chọn chart vì thẩm mỹ. Ghi đơn vị, uncertainty nếu có, không bịa error bars. Xuất PGFPlots hoặc vector PDF, kiểm tra grayscale và effective font size trong PDF luận văn.
