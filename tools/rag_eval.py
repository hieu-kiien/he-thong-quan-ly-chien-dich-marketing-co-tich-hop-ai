"""Evaluate canonical RAG retrieval with a small, reviewable question set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from rag_index import DEFAULT_DB, search_index
except ImportError:  # pragma: no cover - supports direct module execution
    from tools.rag_index import DEFAULT_DB, search_index


DEFAULT_CASES = Path(__file__).with_name("rag_eval_cases.json")


def load_cases(path: Path = DEFAULT_CASES) -> list[dict[str, Any]]:
    """Load and validate the small, hand-reviewed evaluation set."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("RAG evaluation cases must be a non-empty JSON list")
    seen: set[str] = set()
    for case in payload:
        if not isinstance(case, dict) or not case.get("id") or not case.get("query"):
            raise ValueError(f"Invalid RAG evaluation case: {case!r}")
        if case["id"] in seen:
            raise ValueError(f"Duplicate RAG evaluation case id: {case['id']}")
        if not case.get("expected_paths"):
            raise ValueError(f"Case {case['id']} has no expected_paths")
        seen.add(case["id"])
    return payload


def _first_matching_rank(results: list[dict[str, Any]], expected_paths: list[str]) -> int | None:
    for rank, result in enumerate(results, start=1):
        if result["path"] in expected_paths:
            return rank
    return None


def evaluate_cases(
    db_path: Path,
    cases: list[dict[str, Any]],
    top_k: int = 5,
) -> dict[str, Any]:
    """Return hit-rate, reciprocal-rank and forbidden-source metrics."""

    details: list[dict[str, Any]] = []
    forbidden_hits = 0
    reciprocal_ranks: list[float] = []
    for case in cases:
        results = search_index(db_path, case["query"], top_k=top_k)
        paths = [result["path"] for result in results]
        rank = _first_matching_rank(results, case["expected_paths"])
        forbidden = [
            path
            for path in paths
            if any(path == prefix or path.startswith(prefix) for prefix in case.get("forbidden_paths", []))
        ]
        forbidden_hits += len(forbidden)
        if rank is not None:
            reciprocal_ranks.append(1.0 / rank)
        authority_paths = {
            authority_path
            for result in results
            for authority_path in result.get("authority_paths", [])
        }
        expected_authority = set(case.get("expected_authority_paths", []))
        details.append(
            {
                "id": case["id"],
                "query": case["query"],
                "hit": rank is not None,
                "rank": rank,
                "authority_hit": bool(expected_authority & authority_paths)
                if expected_authority
                else None,
                "paths": paths,
                "forbidden_hits": forbidden,
            }
        )

    total = len(cases)
    hits = sum(1 for detail in details if detail["hit"])
    authority_cases = [detail for detail in details if detail["authority_hit"] is not None]
    authority_hits = sum(1 for detail in authority_cases if detail["authority_hit"])
    return {
        "total_cases": total,
        "hits": hits,
        "hit_rate": round(hits / total, 4) if total else 0.0,
        "authority_cases": len(authority_cases),
        "authority_hits": authority_hits,
        "authority_hit_rate": round(authority_hits / len(authority_cases), 4)
        if authority_cases
        else None,
        "mrr": round(sum(reciprocal_ranks) / total, 4) if total else 0.0,
        "forbidden_hits": forbidden_hits,
        "details": details,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-hit-rate", type=float, default=0.9)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = _parse_args(argv or sys.argv[1:])
    try:
        report = evaluate_cases(args.db.resolve(), load_cases(args.cases.resolve()), args.top_k)
    except (OSError, ValueError) as exc:
        print(f"RAG EVAL ERROR: {exc}", file=sys.stderr)
        return 2
    report["threshold"] = {"min_hit_rate": args.min_hit_rate, "max_forbidden_hits": 0}
    report["passed"] = report["hit_rate"] >= args.min_hit_rate and report["forbidden_hits"] == 0
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
