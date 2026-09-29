# Kế hoạch đánh giá

## Mục tiêu

Đánh giá riêng ba lớp: tính đúng của nghiệp vụ, chất lượng có kiểm soát của AI và khả năng tái lập. Không gộp chúng thành một điểm cảm tính.

## Đối tượng và fixture

Tạo một bộ fixture nhỏ, có version, gồm:

- ít nhất hai user với role Manager và Marketer;
- hai product, ba channel, hai campaign ở các trạng thái khác nhau;
- content ở DRAFT, AI_DRAFT, IN_REVIEW, APPROVED và REJECTED;
- metrics theo ngày/kênh, gồm một case views bằng 0 và một case clicks bằng 0;
- AI cases cho idea, draft và summary; mỗi case có context được phép và context cố ý bị loại.

Fixture không được chứa API key hoặc dữ liệu cá nhân thật. Mỗi run ghi commit, môi trường, seed hash, provider/model, prompt version và thời gian.

## Ma trận đo

| Nhóm | Biến/metric | Phương pháp | Báo cáo |
|---|---|---|---|
| Nghiệp vụ | pass rate T01--T15 | test tự động với fixture | số pass/fail, lỗi blocker và log |
| Dữ liệu | FK/constraint/state/KPI | test dương và âm | case, expected, actual |
| AI contract | schema-valid rate, error containment | replay input cố định | output gốc, parser result, status |
| AI grounding | fact ngoài context, source ids, warning | rubric theo case | điểm và ví dụ fail |
| AI usefulness | objective/channel/audience/CTA fit | chấm theo rubric định trước | phân bố điểm, edit rate |
| Performance | p50/p95 latency, error rate, token/cost nếu có | cùng máy và cấu hình | raw result và summary |
| Usability | task completion, thao tác sai, thời gian | demo script với người dùng | checklist và quan sát |
| Reproducibility | fresh setup, backup/restore | người khác chạy README | commit, commands, sai khác |

## So sánh prompt/model

Giữ nguyên fixture và thay đổi một biến mỗi vòng. Tối thiểu ba cấu hình được ghi trong prompt log. Không chọn riêng output đẹp để báo cáo. Nếu chỉ có mock provider, kết quả được giới hạn ở parser/workflow; không gọi đó là đánh giá model.

## Kết quả âm

Phải ghi lại timeout, rate limit, invalid JSON, context quá dài, thiếu metrics và output thêm fact. Một hệ thống AI tốt trong phạm vi môn học không phải hệ thống không bao giờ lỗi; đó là hệ thống lỗi có kiểm soát và cho người dùng đường lui rõ.
