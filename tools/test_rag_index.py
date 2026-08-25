"""Tests for the project-local canonical document index."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from rag_index import (  # noqa: E402
    build_index,
    chunk_markdown,
    search_index,
    validate_corpus,
)


class RagIndexTests(unittest.TestCase):
    manifest = ROOT / "docs" / "rag-corpus.json"

    def test_markdown_chunks_keep_heading_and_line_ranges(self) -> None:
        chunks = chunk_markdown("# Mục tiêu\n\nMột nội dung.\n\n## AI\n\nSinh bản nháp.")

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].section, "Mục tiêu")
        self.assertEqual(chunks[0].line_start, 1)
        self.assertEqual(chunks[1].section, "AI")
        self.assertIn("Sinh bản nháp", chunks[1].content)

    def test_validate_requires_both_p0_images(self) -> None:
        report = validate_corpus(ROOT, self.manifest)

        self.assertEqual(report["missing"], [])
        self.assertEqual(report["authority_assets"], 2)
        self.assertEqual(report["project_id"], "AIA331-80300-MARKETING-AI")

    def test_validate_detects_p0_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            altered_manifest = Path(temp_dir) / "rag-corpus.json"
            payload = json.loads(self.manifest.read_text(encoding="utf-8"))
            payload["authority_assets"][0]["sha256"] = "0" * 64
            altered_manifest.write_text(json.dumps(payload), encoding="utf-8")

            report = validate_corpus(ROOT, altered_manifest)

            self.assertTrue(any("sha256 mismatch" in item for item in report["missing"]))

    def test_build_filters_legacy_and_writes_citations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "marketing-rag.sqlite3"
            report = build_index(ROOT, self.manifest, db_path)
            self.assertGreater(report["chunks"], 20)
            self.assertEqual(report["authority_assets"], 2)

            results = search_index(
                db_path,
                "tên đề tài chính thức chiến dịch marketing tích hợp AI",
                top_k=8,
            )

            self.assertTrue(results)
            self.assertTrue(
                any(
                    item["path"] == "project.md"
                    and "source-materials/DỰ ÁN.png" in item["authority_paths"]
                    for item in results
                )
            )
            self.assertTrue(all("citation" in item for item in results))
            self.assertFalse(any("sales_management" in item["path"] for item in results))
            self.assertFalse(any("Code QLBH" in item["path"] for item in results))
            self.assertFalse(any("prompts/07-RAG" in item["path"] for item in results))

            assessment_results = search_index(db_path, "10 tiêu chí bài kiểm tra", top_k=3)
            self.assertTrue(
                any(
                    item["path"] == "docs/09-assessment-checklist.md"
                    and "source-materials/BÀI KIỂM TRA.png" in item["authority_paths"]
                    for item in assessment_results
                )
            )

    def test_build_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "marketing-rag.sqlite3"
            first = build_index(ROOT, self.manifest, db_path)
            first_results = search_index(db_path, "approval nội dung AI", top_k=10)
            second = build_index(ROOT, self.manifest, db_path)
            second_results = search_index(db_path, "approval nội dung AI", top_k=10)

            self.assertEqual(first["chunk_ids_sha256"], second["chunk_ids_sha256"])
            self.assertEqual(
                [item["chunk_id"] for item in first_results],
                [item["chunk_id"] for item in second_results],
            )

    def test_search_json_is_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "marketing-rag.sqlite3"
            build_index(ROOT, self.manifest, db_path)
            payload = search_index(db_path, "AI", top_k=3)

            json.dumps(payload, ensure_ascii=False)
            self.assertLessEqual(len(payload), 3)

    def test_search_returns_diverse_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "marketing-rag.sqlite3"
            build_index(ROOT, self.manifest, db_path)

            results = search_index(db_path, "tên đề tài chính thức chiến dịch marketing", top_k=5)

            self.assertEqual(len(results), len({item["path"] for item in results}))


if __name__ == "__main__":
    unittest.main()
