# Research pack của báo cáo AIA331

Đây là bộ hồ sơ nguồn cho bản LaTeX V8. Nó dùng để giữ traceability giữa yêu cầu, quyết định thiết kế, nguồn nghiên cứu, hình vẽ và kế hoạch kiểm tra.

Tình trạng hiện tại là baseline phân tích--thiết kế trước khi code. Các ô implementation/evaluation chưa có kết quả phải giữ trạng thái PLANNED hoặc UNKNOWN, không điền số liệu giả.

Các file chính:

- project-research-plan.md: identity, scope, research questions và risk.
- source-inventory.csv: nguồn người dùng cung cấp, skill và tài liệu chính thức.
- evidence-ledger.csv: claim/evidence/status.
- related-work-matrix.csv: so sánh nguồn tham chiếu.
- requirements-traceability.csv: requirement tới design/test/evidence.
- quality-attribute-scenarios.csv: kịch bản NFR có thể đo.
- evaluation-plan.md: fixture, metric, protocol và negative evidence.
- visual-coverage-map.csv: câu hỏi mà từng hình trả lời.
- reproducibility-manifest.yaml: manifest sẽ hoàn thiện sau khi có repository/runtime.

Nguồn chỉnh sửa của báo cáo nằm ở thư mục cha: main.tex, chapters/, figures/, design/schema.sql. PDF chỉ là artefact sinh ra.
