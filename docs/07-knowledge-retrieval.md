---
document_id: BAI03-DOC-RAG
document_type: retrieval-architecture
project_id: BAI03-SALES-AI
status: DERIVED
language: vi
last_reviewed: 2026-08-18
---

# Kiến trúc GitNexus và Document RAG

Quy ước phân loại tài liệu, source-of-truth và định dạng bản nộp nằm trong
[08-documentation-standard.md](08-documentation-standard.md). Tài liệu này
chỉ mô tả vận hành lớp truy hồi.

## Mục tiêu

`GitNexus` lập bản đồ quan hệ trong mã nguồn để AI truy vết symbol, caller,
flow và tác động thay đổi. Lớp `knowledge` lập chỉ mục tài liệu và trả về các
đoạn văn có metadata để một AI khác dùng làm context có trích dẫn. Hai lớp này
không thay thế nhau:

```text
Mã nguồn Django ──> GitNexus code graph ──> hiểu flow / impact / symbol
Tài liệu MD/YAML/DOCX ──> chunk + embedding ──> Chroma ──> context có nguồn
```

Hiện tại dự án mới triển khai lớp truy hồi. Chưa có provider LLM runtime nên API
không tự sinh câu trả lời và không được xem kết quả retrieval là kết luận cuối.

## Phạm vi corpus

Mặc định lệnh index đọc:

- tài liệu chuẩn trong `docs/`, `project.md`, `informember.md`, `ContextProject.md`;
- prompt và ghi chú Markdown/YAML của BAI03;
- pipeline `Bai 02/CacGiaiDoanThucHien/` ở cấp `Codes/`, chỉ dùng làm nguồn đối
  chiếu upstream.

Thêm `--include-code` để đưa Python của `sales_management/` và `Code QLBH/` vào
corpus. GitNexus vẫn là nguồn chính để hỏi quan hệ code. `.venv*`, `.gitnexus`,
`knowledge_store`, `Mau`, `BK`, `Slide_PDF`, `QLBH demo`, database và `.env` bị
loại khỏi index.

## Metadata bắt buộc

Mỗi chunk có ít nhất:

| Trường | Ý nghĩa |
|---|---|
| `source_path` | Đường dẫn tương đối từ thư mục `Codes`, dùng làm citation |
| `source_type` | `documentation`, `prompt`, `config`, `document` hoặc `code` |
| `project_id` | `BAI03-SALES-AI` hoặc `BAI02-SDLC` |
| `document_id` | ID frontmatter hoặc path ổn định |
| `status` | `CANONICAL`, `IMPLEMENTED`, `DERIVED`, `REFERENCE`, `TEMPLATE`, `LEGACY` |
| `content_hash` | Hash file để nhận diện phiên bản nguồn |
| `chunk_index`, `section` | Vị trí chunk trong tài liệu |

Khi trả lời, AI phải giữ citation `[n] source_path#section`, ưu tiên `CANONICAL`
và đối chiếu `IMPLEMENTED` trước khi nói một tính năng đã có.

## Cài đặt và vận hành

Từ thư mục `sales_management`:

```powershell
.\.venv-rag\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-rag\Scripts\python.exe manage.py index_knowledge
```

Index lại toàn bộ collection:

```powershell
.\.venv-rag\Scripts\python.exe manage.py index_knowledge --rebuild --include-code
```

Model mặc định là `intfloat/multilingual-e5-small`, phù hợp corpus tiếng Việt và
nhẹ hơn các model multilingual lớn. Có thể đổi bằng `.env`:

```dotenv
RAG_EMBEDDING_MODEL=intfloat/multilingual-e5-small
RAG_COLLECTION_NAME=bai03_knowledge
KNOWLEDGE_STORE_PATH=../knowledge_store
```

Lần index đầu có thể tải model từ Hugging Face. Dữ liệu vector được lưu local ở
`knowledge_store/` và không commit vào Git.

## API truy hồi

Khởi động Django rồi gọi:

```text
GET /knowledge/search/?q=Invoice.confirm%20ton%20kho&top_k=5
GET /knowledge/search/?q=REQ-F-004&status=CANONICAL
GET /knowledge/context/?q=quy%20trinh%20ban%20hang
```

`/search/` trả `query`, danh sách `results` gồm `text`, `score`, `metadata` và
`context`. `/context/` chỉ trả chuỗi context đã gắn citation để ghép vào prompt
của provider LLM sau này.

## Quy trình cập nhật nguồn

1. Sửa tài liệu nguồn và cập nhật frontmatter/status nếu cần.
2. Chạy `index_knowledge`; dùng `--rebuild` khi xóa hoặc đổi cấu trúc nguồn.
3. Kiểm tra một câu hỏi đại diện bằng `/knowledge/search/`.
4. Nếu thay đổi Python, chạy thêm `gitnexus analyze` trong repo `Bai 03`.
5. Không đưa API key, database local, model cache hoặc vector store vào Git.

## Giới hạn hiện tại

- Chưa có hybrid search riêng cho toàn bộ mã yêu cầu; lexical overlap chỉ dùng để
  rerank kết quả dense.
- Chưa có quyền truy cập theo người dùng cho endpoint; cần thêm auth trước khi
  mở ra môi trường production.
- Chưa có LLM answer/guardrail/evaluation; đó là lát cắt tiếp theo, không giả định
  là đã hoàn thành.
