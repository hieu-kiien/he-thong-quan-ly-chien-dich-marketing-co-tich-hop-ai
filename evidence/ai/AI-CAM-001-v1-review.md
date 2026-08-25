---
document_id: AIA331-EV-001
project_id: AIA331-80300-MARKETING-AI
status: IMPLEMENTED_BASELINE
prompt_id: AI-CAM-001
version: AI-CAM-001-v1
last_reviewed: 2026-08-19
---

# Minh chứng prompt → phản hồi → kiểm chứng

## 1. Input đã khử dữ liệu riêng tư

```text
Campaign brief: Ra mắt sản phẩm A cho sinh viên và người đi làm trẻ tại Thái Nguyên
Channel: Facebook
Tone: thân thiện, rõ ràng
```

## 2. Phản hồi đã lưu

Phản hồi JSON đầy đủ nằm tại
`evidence/ai/AI-CAM-001-v1-response.json`. Đây là phản hồi fallback offline có
thể tái lập, dùng để chứng minh contract và approval gate mà không cần lưu API key
hoặc gọi provider bên ngoài.

Các trường quan sát được: `provider=fallback`, `prompt_version=AI-CAM-001-v1`,
5 `ideas[]`, mỗi ý tưởng có `title/channel/hook/draft/cta`,
`needs_human_approval=true` và warning bản nháp.

## 3. Bảng kiểm chứng và chỉnh sửa của sinh viên

| Kiểm tra | Kết quả | Hành động |
|---|---|---|
| Đúng kênh Facebook | Đạt; cả 5 ý tưởng trả về Facebook | Giữ trường `channel` để người duyệt đối chiếu |
| Có claim/số liệu chưa được cung cấp | Không có số liệu, giải thưởng hoặc chứng nhận | Giữ warning; không cho tự đăng |
| Có đủ cấu trúc title/hook/draft/CTA | Đạt; được kiểm tra bằng `_valid_result()` | Chỉ nhận output đủ schema; output sai chuyển fallback |
| Có cần người duyệt | Có; `needs_human_approval=true` | Manager duyệt hoặc từ chối trước publish |
| Văn phong | Bản fallback còn chung chung | Sinh viên chỉnh lại hook/draft theo brief trước khi sử dụng |

## 4. Kết luận kiểm chứng

Phản hồi được xem là **bản nháp**, không phải sự thật marketing. Sinh viên kiểm
tra cấu trúc, kênh, claim và approval flag trước khi đưa vào luồng Content. Không
đưa API key, PII hoặc dữ liệu khách hàng thật vào minh chứng.
