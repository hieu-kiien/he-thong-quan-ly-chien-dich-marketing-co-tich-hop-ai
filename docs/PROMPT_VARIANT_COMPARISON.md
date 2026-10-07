# So sánh các phiên bản prompt (Tuần 3 — mục 4 rubric AIA331)

> **Tài liệu này được sinh tự động.** Generator: [`scripts/compare_prompt_variants.py`](../scripts/compare_prompt_variants.py). Đổi script thì phải sinh lại file này. Không sửa tay.

**Thời điểm chạy:** 2026-10-07 06:57 UTC  
**Mã nguồn:** xem `git log -1 --format=%H` trên commit sinh ra file này

## 1. Phạm vi kết luận — đọc trước khi trích số

Bảng dưới đo **tính đầy đủ và rõ ràng của đặc tả trong prompt**, không đo chất lượng văn phong của mô hình. Lý do: lời gọi mô hình được thay bằng stub tất định.

Stub tuân theo prompt một cách máy móc: nó sinh ra **chỉ những trường mà prompt nhắc tới**. Hệ quả trực tiếp và có lợi: nếu một phiên bản prompt không yêu cầu đủ trường, cột `Đủ trường bắt buộc` sẽ thấp — và đó chính là thứ ta muốn đo.

Những gì bảng này **KHÔNG** chứng minh:

- Văn phong hay sức thuyết phục của bài viết sinh ra.
- Mức độ chính xác ngữ nghĩa của mô hình thật.
- Rằng v3 "tốt hơn v1" với người đọc thật.
- Bất kỳ so sánh nào với LLM qua mạng.

Để so sánh chất lượng văn phong cần chạy cùng tập case qua provider thật và chấm bằng rubric có người đánh giá. Việc đó tốn credit và không tái lập được, nên nó không nằm trong CI.

## 2. Bảng so sánh

| Phiên bản | Ý định thiết kế của prompt đa kênh | Schema hợp lệ | Rò từ khóa cấm | Đủ trường bắt buộc | Placeholder chưa lấp | Prompt TB |
|:---|:---|---:|---:|---:|---:|---:|
| `v1` | 1 prompt, chỉ yêu cầu "tạo nội dung cho 3 kênh", **không** nêu khung JSON | 0% (0/4) | 0 | 0% | 0 | 249 ký tự |
| `v2` | 2 prompt, có nhắc tên các trường (facebook/tiktok/email) nhưng không cho khung đầy đủ | 75% (3/4) | 0 | 75% | 0 | 426 ký tự |
| `v3` | 2 prompt, có khung JSON đầy đủ cho 3 kênh + ràng buộc từ khóa cấm + quy tắc 100% tiếng Việt | 100% (4/4) | 0 | 100% | 0 | 1900 ký tự |

> Cột "Prompt TB" là trung bình trên 4 tác vụ, tính cả system lẫn user prompt sau khi lấp đầy ngữ cảnh. Nó tăng mạnh từ `v1` lên `v3`: đây là **chi phí** đổi lấy tính đầy đủ của đặc tả, và là một đánh đổi có ý thức chứ không phải kết quả đẹp. Xem mục 4.

## 3. Chi tiết theo từng tác vụ

### content_draft

| Phiên bản | Schema hợp lệ | Trường bắt buộc thiếu | Ghi chú |
|:---|:---:|:---|:---|
| `v1` | **không** | `title`, `body`, `cta` |  |
| `v2` | có | — |  |
| `v3` | có | — |  |

### idea_generation

| Phiên bản | Schema hợp lệ | Trường bắt buộc thiếu | Ghi chú |
|:---|:---:|:---|:---|
| `v1` | **không** | `ideas.0.headline`, `ideas.0.concept`, `ideas.0.target_emotion` |  |
| `v2` | có | — |  |
| `v3` | có | — |  |

### omnichannel_generation

| Phiên bản | Schema hợp lệ | Trường bắt buộc thiếu | Ghi chú |
|:---|:---:|:---|:---|
| `v1` | **không** | `facebook.title`, `facebook.body`, `facebook.cta`, `facebook.hashtags`, `tiktok.hook_3s`, `tiktok.scenes`, `email.body` |  |
| `v2` | có | — |  |
| `v3` | có | — |  |

### performance_summary

| Phiên bản | Schema hợp lệ | Trường bắt buộc thiếu | Ghi chú |
|:---|:---:|:---|:---|
| `v1` | **không** | `executive_summary`, `strengths`, `weaknesses`, `recommendations` |  |
| `v2` | **không** | `executive_summary`, `strengths`, `weaknesses`, `recommendations` |  |
| `v3` | có | — |  |

## 4. Cái tiến và cái tụt — đọc thẳng, không diễn giải

So sánh `v1` → `v3` theo từng chỉ số:

- Schema hợp lệ (%): 0 → 100 (**cải thiện**)
- Đủ trường bắt buộc (%): 0 → 100 (**cải thiện**)
- Rò từ khóa cấm (số case): 0 → 0 (không đổi)
- Placeholder chưa lấp (số case): 0 → 0 (không đổi)

### Những gì KHÔNG cải thiện — và cái giá phải trả

- **Chi phí prompt tăng từ 249 lên 1900 ký tự** (xấp xỉ 7.6 lần). Với mỗi lời gọi AI thật, đây là token phải trả cho mỗi lần gọi. Đây là cái giá thật của v3, không phải điều gì đo bằng con số này được bù lại.

- **Rò từ khóa cấm vẫn bằng 0 ở cả ba phiên bản.** Nghĩa là bộ case hiện tại không phân biệt được prompt nào ràng buộc an toàn thương hiệu tốt hơn. Muốn đo được, phải có case mà mô hình thật *thực sự* cố phát ra từ khóa cấm — điều mà stub không làm được. Đây là khoảng trống thật, ghi ra để không ai tưởng đã đo.

- **Không có chỉ số nào đo độ dài hay văn phong.** Không so sánh được trong harness này (xem mục 1).


So sánh `v2` → `v3`:

- Schema hợp lệ (%): 75 → 100 (**cải thiện**)
- Đủ trường bắt buộc (%): 75 → 100 (**cải thiện**)

**Đọc kết quả này thế nào khi bảo vệ:** v3 thắng ở chỉ số "đủ trường bắt buộc" vì nó là phiên bản duy nhất liệt kê đầy đủ khung JSON của cả ba kênh. Đó là một phát hiện có thật về đặc tả prompt, không phải bằng chứng rằng bài viết của v3 hay hơn. Nếu một phiên bản nào đứng cuối ở một chỉ số, phải nói ra chứ không giấu đi.


## 5. Bộ đo có thật sự bắt được lỗi không?

Chỉ số "rò từ khóa cấm = 0" ở bảng trên chỉ có nghĩa nếu bộ dò thật sự bắt được lỗi. Nếu không thì nó cũng bằng 0 khi bộ đo hỏng — hai khả năng đó nhìn giống hệt nhau.

Vì vậy script chạy thêm một **đối chứng âm**: một stub cố ý nhét từ khóa cấm vào output, rồi kiểm tra bộ dò có bắt không. Kết quả lần chạy này:

- Bộ dò từ khóa cấm: **bắt được** — bắt 2 từ khóa ('săn mãi', 'chắc chắn hiệu quả').
- Bộ dò placeholder sót: **bắt được**.

Nói cách khác: cột "rò từ khóa cấm = 0" trong bảng trên là kết quả đo được, không phải giá trị mặc định của một phép đo không làm gì.

## 6. Cách tái lập

```bash
python scripts/compare_prompt_variants.py
```

Kết quả tất định: chạy lại cho ra cùng số. Không gọi mạng, không tốn credit. Script cũng ghi artifact máy đọc được ở [`scripts/prompt_variant_results.json`](../scripts/prompt_variant_results.json).

## 7. Điều chưa làm

- Chưa chạy cùng tập case này qua provider thật với người chấm điểm. Đó là khoảng trống thật của tài liệu này, không phải chi tiết nhỏ.
- Chưa thử so sánh **giữa các model** (cùng prompt, khác provider). Rubric cho phép "so sánh prompt **hoặc** model"; tài liệu này chỉ làm phần prompt.
- Các từ khóa cấm dùng trong benchmark là bộ cố định 3 từ để tập case là tất định, không phải blacklist thật của một workspace cụ thể.

