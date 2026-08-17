from pathlib import Path

from django.test import SimpleTestCase

from .services import (
    chunk_text,
    extract_metadata,
    format_context,
    is_allowed_source,
    stable_chunk_id,
)


class KnowledgeTextTests(SimpleTestCase):
    def test_chunk_text_respects_limit_and_keeps_overlap(self):
        text = "Đoạn đầu nói về hóa đơn.\n\n" + ("ton kho " * 30)

        chunks = chunk_text(text, max_chars=80, overlap=12)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 80 for chunk in chunks))
        self.assertTrue(set(chunks[0][-12:]) & set(chunks[1][:12]))

    def test_extract_metadata_reads_frontmatter_and_derives_source_fields(self):
        source = Path("docs/01-requirements-summary.md")
        text = "---\ndocument_id: REQ-DOC\nproject_id: BAI03-SALES-AI\nstatus: CANONICAL\n---\n# Yêu cầu"

        metadata = extract_metadata(source, text)

        self.assertEqual(metadata["document_id"], "REQ-DOC")
        self.assertEqual(metadata["project_id"], "BAI03-SALES-AI")
        self.assertEqual(metadata["status"], "CANONICAL")
        self.assertEqual(metadata["source_type"], "documentation")

    def test_source_status_is_safe_for_implemented_and_legacy_code(self):
        self.assertTrue(is_allowed_source(Path("sales_management/apps/sales/models.py"), include_code=True))
        self.assertEqual(
            extract_metadata(Path("sales_management/apps/sales/models.py"), "")["status"],
            "IMPLEMENTED",
        )
        self.assertEqual(
            extract_metadata(Path("docs/legacy-prime-number-utilities.md"), "")["status"],
            "LEGACY",
        )
        self.assertFalse(is_allowed_source(Path("Slide_PDF/slide.pdf")))
        self.assertFalse(is_allowed_source(Path("Code QLBH/apps/sales/models.py")))

    def test_stable_chunk_id_is_deterministic(self):
        first = stable_chunk_id("docs/guide.md", "hash", 0)

        self.assertEqual(first, stable_chunk_id("docs/guide.md", "hash", 0))
        self.assertNotEqual(first, stable_chunk_id("docs/guide.md", "hash", 1))

    def test_format_context_contains_citations(self):
        context = format_context(
            [
                {
                    "text": "Invoice.confirm cập nhật tổng tiền.",
                    "score": 0.9,
                    "metadata": {
                        "source_path": "sales_management/apps/sales/models.py",
                        "section": "Invoice",
                    },
                }
            ]
        )

        self.assertIn("[1]", context)
        self.assertIn("sales_management/apps/sales/models.py", context)
        self.assertIn("Invoice.confirm", context)
