"""Tests for the deterministic RAG retrieval evaluator."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from rag_eval import evaluate_cases, load_cases  # noqa: E402
from rag_index import build_index  # noqa: E402


class RagEvalTests(unittest.TestCase):
    manifest = ROOT / "docs" / "rag-corpus.json"

    def test_cases_have_stable_ids_and_expected_evidence(self) -> None:
        cases = load_cases(ROOT / "tools" / "rag_eval_cases.json")

        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertTrue(all(case["expected_paths"] for case in cases))

    def test_evaluator_reports_hits_and_forbidden_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "marketing-rag.sqlite3"
            build_index(ROOT, self.manifest, db_path)
            cases = load_cases(ROOT / "tools" / "rag_eval_cases.json")

            report = evaluate_cases(db_path, cases, top_k=5)

            self.assertEqual(report["total_cases"], len(cases))
            self.assertGreaterEqual(report["hit_rate"], 0.9)
            self.assertEqual(report["forbidden_hits"], 0)
            json.dumps(report, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
