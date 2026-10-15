---
name: anti-ai-taste-system
description: Khử hoàn toàn "mùi AI" trong mọi đầu ra của Agent (Giao diện App/Web, Slide, Sơ đồ SVG, Bài viết, Microcopy, Tài liệu sản phẩm). Kích hoạt bất cứ khi nào Agent cần tạo nội dung chữ tiếng Việt, thiết kế giao diện, chọn màu sắc/font chữ, vẽ icon/sơ đồ hoặc xây dựng sản phẩm.
version: 2.0.0
---

# SKILL: ANTI-AI TASTE & DESIGN SYSTEM (KHỬ MÙI AI TOÀN DIỆN)

## 1. NGUYÊN LÝ CỐT LÕI (CORE PHILOSOPHY)
AI tạo ra sản phẩm có "mùi AI" không phải vì nó cố tình bắt chước, mà vì **khi thiếu ràng buộc cụ thể, AI sẽ tự động lấp chỗ trống bằng giá trị mặc định có xác suất cao nhất**:
- **Trong chữ viết:** Dùng từ sáo rỗng (*"tận tâm", "toàn diện", "hàng đầu", "đột phá"*), câu dài lê thê nhiều dấu phẩy, chêm tiếng Anh lười biếng (*build, output, vibe, mindset*), mở bài/kết bài văn mẫu.
- **Trong thị giác (App, Slide, UI, Diagram):** Mặc định nền trắng ngả kem `rgb(255, 247, 241)` hoặc tím/xanh indigo công nghệ, phông chữ `Inter` mặc định hoặc phông ngoại bị lỗi rớt dấu tiếng Việt, icon nét dày mỏng lộn xộn.

## 2. BẢNG QUY ĐỊNH KHÓA CỨNG CHO DỰ ÁN MARKETFLOW
- **Bố cục & Nhịp điệu (Nguồn A - Linear / Stripe Dashboard):** Tối giản số lượng khối hộp trên mỗi màn hình (tối đa 3 khu vực chính), không xếp chồng nhiều hộp cảnh báo trùng lặp, ưu tiên bảng dữ liệu rõ ràng và khoảng trắng thoáng mắt.
- **Bảng màu & Bề mặt (Nguồn B - Editorial Ink & Terracotta):**
  - Nền chính: `#F6F5F0` | Thẻ nội dung: `#FFFFFF` | Viền thẻ: `#E4E2DD`
  - Chữ chính: `#121316` | Chữ phụ: `#5A5E66` | Nền điều hướng: `#141518`
  - Màu nhấn hành động chính: `#D95D39` (Hover: `#C04E2C`)
  - Cấm tuyệt đối mọi dải gradient tím-xanh (`indigo-600`, `violet-600`, `purple-600`) và cấm dùng Emoji trong giao diện.
- **Phông chữ (Đã kiểm tra 5 ký tự `Ế Ứ Ỡ Ặ Ằ`):**
  - Tiêu đề & Nội dung: `Plus Jakarta Sans` (tự host `.woff2` subset tiếng Việt)
  - Số liệu tiền tệ / ROAS: `JetBrains Mono` / `IBM Plex Mono` (`font-mono tabular-nums`)
- **Ngôn từ & Việt hóa 100%:**
  - Giải thích mọi chỉ số bằng tiếng Việt đời thường ngay trên màn hình để người không chuyên marketing nhìn vào hiểu ngay trong 3 giây.
  - Cấm dùng từ tự khen (*"toàn diện", "khép kín", "đột phá", "thế hệ mới", "tối ưu"*).
