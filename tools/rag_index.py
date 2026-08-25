"""Build and query a small, deterministic RAG index for the canonical project corpus.

The index deliberately uses SQLite FTS5 from the Python standard library.  It is
an agent/document retrieval layer, not a runtime feature of the Django product.
Generated data belongs in ``.rag/`` and must not be committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterable, Iterator


DEFAULT_PROJECT_ID = "AIA331-80300-MARKETING-AI"
DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "docs" / "rag-corpus.json"
DEFAULT_DB = Path(__file__).resolve().parents[1] / ".rag" / "marketing-rag.sqlite3"
MAX_CHUNK_CHARS = 2200
SCHEMA_VERSION = 1

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SYMBOL_RE = re.compile(r"^(?:async\s+def|def|class)\s+.+")
_TOKEN_RE = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


class CorpusError(ValueError):
    """Raised when the canonical corpus cannot be built safely."""


@dataclass(frozen=True)
class TextChunk:
    section: str
    line_start: int
    line_end: int
    content: str


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    document_id: str
    path: str
    project_id: str
    priority: str
    priority_level: str
    status: str
    modality: str
    authority_paths: tuple[str, ...]


def _clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def read_front_matter(text: str) -> dict[str, str]:
    """Read the scalar YAML front matter fields used by this repository."""

    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = _clean_scalar(value)
    return result


def _without_front_matter(text: str) -> tuple[str, int]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if not match:
        return text, 0
    return text[match.end() :], text[: match.end()].count("\n")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _matches_excluded(path: str, patterns: Iterable[str]) -> bool:
    path = path.replace("\\", "/")
    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        if fnmatch(path, pattern) or fnmatch(path + "/", pattern):
            return True
        if pattern.startswith("**/") and pattern.endswith("/**"):
            middle = pattern[3:-3].strip("/")
            if middle and f"/{middle}/" in f"/{path}/":
                return True
        if pattern.endswith("/**") and path.startswith(pattern[:-3].rstrip("/") + "/"):
            return True
    return False


def _candidate_paths(
    root: Path,
    item: dict[str, Any],
    excluded_patterns: Iterable[str] = (),
) -> Iterator[Path]:
    if "path" in item:
        yield root / str(item["path"])
    elif "glob" in item:
        pattern = str(item["glob"]).replace("\\", "/")
        wildcard_positions = [position for token in ("*", "?", "[") if (position := pattern.find(token)) >= 0]
        if wildcard_positions:
            wildcard_start = min(wildcard_positions)
            base = pattern[:wildcard_start].rsplit("/", 1)[0]
        else:
            base = pattern
        base = base.rstrip("/")
        walk_root = root / base if base else root
        if not walk_root.is_dir():
            return
        for current, directories, filenames in os.walk(walk_root):
            current_path = Path(current)
            current_relative = _relative(root, current_path) if current_path != root else ""
            directories[:] = [
                directory
                for directory in directories
                if not _matches_excluded(
                    f"{current_relative}/{directory}".strip("/"), excluded_patterns
                )
            ]
            for filename in filenames:
                path = current_path / filename
                relative = _relative(root, path)
                if (fnmatch(relative, pattern) or Path(relative).match(pattern)) and not _matches_excluded(
                    relative, excluded_patterns
                ):
                    yield path
    else:
        raise CorpusError(f"Manifest source thiếu path/glob: {item!r}")


def load_manifest(manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusError(f"Không đọc được manifest RAG: {manifest_path}: {exc}") from exc
    if data.get("schema_version") != SCHEMA_VERSION:
        raise CorpusError("schema_version của manifest RAG không được hỗ trợ")
    if not data.get("project_id") or not data.get("sources"):
        raise CorpusError("Manifest RAG phải có project_id và sources")
    return data


def _authority_map(manifest: dict[str, Any], root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    assets: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for item in manifest.get("authority_assets", []):
        path = str(item["path"])
        source_path = root / path
        exists = source_path.is_file()
        assets[item["source_id"]] = {**item, "exists": exists}
        if not exists:
            missing.append(path)
        elif item.get("sha256") and _sha256(source_path.read_bytes()) != item["sha256"]:
            missing.append(f"{path} (sha256 mismatch)")
    return assets, missing


def iter_sources(root: Path, manifest: dict[str, Any]) -> tuple[list[SourceRecord], dict[str, dict[str, Any]]]:
    authority_assets, missing = _authority_map(manifest, root)
    if missing:
        raise CorpusError(f"Thiếu nguồn P0: {', '.join(missing)}")

    excluded = manifest.get("excluded_paths", [])
    records: list[SourceRecord] = []
    seen_paths: set[str] = set()
    for item in manifest.get("sources", []):
        if item.get("index", True) is False:
            continue
        for candidate in _candidate_paths(root, item, excluded):
            relative = _relative(root, candidate)
            if not candidate.is_file() or relative in seen_paths:
                continue
            if _matches_excluded(relative, excluded):
                continue
            seen_paths.add(relative)
            raw = candidate.read_text(encoding="utf-8", errors="replace")
            front = read_front_matter(raw) if item.get("front_matter", True) else {}
            source_id = str(item["source_id"])
            if "glob" in item:
                source_id = f"{source_id}::{relative}"
            document_id = front.get("document_id") or str(item.get("document_id") or source_id)
            project_id = front.get("project_id") or str(manifest["project_id"])
            authority_source_id = front.get("authority_source_id") or item.get("authority_source_id")
            authority_paths = ()
            if authority_source_id and authority_source_id in authority_assets:
                authority_paths = (str(authority_assets[authority_source_id]["path"]),)
            records.append(
                SourceRecord(
                    source_id=source_id,
                    document_id=document_id,
                    path=relative,
                    project_id=project_id,
                    priority=front.get("priority") or str(item.get("priority", "P2")),
                    priority_level=front.get("priority_level")
                    or str(item.get("priority_level", "MEDIUM")),
                    status=front.get("status") or str(item.get("status", "DERIVED")),
                    modality=candidate.suffix.lower().lstrip(".") or "text",
                    authority_paths=authority_paths,
                )
            )
    return records, authority_assets


def validate_corpus(root: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    authority_assets, missing = _authority_map(manifest, root)
    source_missing: list[str] = []
    indexed_paths: list[str] = []
    for item in manifest.get("sources", []):
        if item.get("index", True) is False:
            continue
        for candidate in _candidate_paths(root, item, manifest.get("excluded_paths", [])):
            relative = _relative(root, candidate)
            if not candidate.is_file():
                if "path" in item:
                    source_missing.append(relative)
                continue
            if _matches_excluded(relative, manifest.get("excluded_paths", [])):
                continue
            indexed_paths.append(relative)
    excluded_hits: list[str] = []
    records: list[SourceRecord] = []
    if not missing and not source_missing and not excluded_hits:
        records, _ = iter_sources(root, manifest)
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": manifest["project_id"],
        "missing": sorted(missing + source_missing),
        "excluded_hits": sorted(excluded_hits),
        "authority_assets": len(authority_assets),
        "indexed_sources": len(records),
        "indexed_paths": sorted(set(indexed_paths)),
        "ok": not missing and not source_missing and not excluded_hits,
    }


def _split_lines(lines: list[str], section: str, start_line: int, max_chars: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_start = start_line
    for offset, line in enumerate(lines):
        if current and len("\n".join(current)) + len(line) + 1 > max_chars:
            content = "\n".join(current).strip()
            if content:
                chunks.append(TextChunk(section, current_start, current_start + len(current) - 1, content))
            current = []
            current_start = start_line + offset
        current.append(line)
    content = "\n".join(current).strip()
    if content:
        chunks.append(TextChunk(section, current_start, current_start + len(current) - 1, content))
    return chunks


def _sections(lines: list[str], marker: re.Pattern[str]) -> list[tuple[str, int, list[str]]]:
    starts = [(index, marker.match(line)) for index, line in enumerate(lines) if marker.match(line)]
    if not starts:
        return [("Document", 1, lines)]
    sections: list[tuple[str, int, list[str]]] = []
    if starts[0][0] > 0 and "\n".join(lines[: starts[0][0]]).strip():
        sections.append(("Preamble", 1, lines[: starts[0][0]]))
    for position, (start, match) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        title = match.group(0).strip() if match else "Section"
        title = re.sub(r"^#{1,6}\s+", "", title)
        sections.append((title, start + 1, lines[start:end]))
    return sections


def chunk_markdown(text: str, max_chars: int = MAX_CHUNK_CHARS, line_offset: int = 0) -> list[TextChunk]:
    lines = text.splitlines()
    chunks: list[TextChunk] = []
    for section, start, section_lines in _sections(lines, _HEADING_RE):
        chunks.extend(_split_lines(section_lines, section, line_offset + start, max_chars))
    return chunks


def chunk_code(text: str, max_chars: int = MAX_CHUNK_CHARS, line_offset: int = 0) -> list[TextChunk]:
    lines = text.splitlines()
    chunks: list[TextChunk] = []
    for section, start, section_lines in _sections(lines, _SYMBOL_RE):
        chunks.extend(_split_lines(section_lines, section, line_offset + start, max_chars))
    return chunks


def chunk_document(path: str, text: str) -> list[TextChunk]:
    body, line_offset = _without_front_matter(text)
    suffix = Path(path).suffix.lower()
    if suffix == ".md":
        return chunk_markdown(body, line_offset=line_offset)
    if suffix == ".py":
        return chunk_code(body, line_offset=line_offset)
    return _split_lines(body.splitlines(), "Document", line_offset + 1, MAX_CHUNK_CHARS)


def _sha256(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def _database_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode = DELETE;
        PRAGMA foreign_keys = ON;
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS authority_assets;
        DROP TABLE IF EXISTS metadata;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE authority_assets (
            source_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            path TEXT NOT NULL,
            priority TEXT NOT NULL,
            priority_level TEXT NOT NULL,
            status TEXT NOT NULL,
            description TEXT NOT NULL
        );
        CREATE TABLE documents (
            document_key TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            project_id TEXT NOT NULL,
            priority TEXT NOT NULL,
            priority_level TEXT NOT NULL,
            status TEXT NOT NULL,
            modality TEXT NOT NULL,
            checksum TEXT NOT NULL,
            authority_paths_json TEXT NOT NULL
        );
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            document_key TEXT NOT NULL REFERENCES documents(document_key),
            document_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            path TEXT NOT NULL,
            project_id TEXT NOT NULL,
            priority TEXT NOT NULL,
            priority_level TEXT NOT NULL,
            status TEXT NOT NULL,
            modality TEXT NOT NULL,
            section TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            authority_paths_json TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            chunk_id UNINDEXED,
            title,
            content,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        """
    )


def build_index(
    root: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    manifest = load_manifest(manifest_path)
    validation = validate_corpus(root, manifest_path)
    if not validation["ok"]:
        raise CorpusError(f"Corpus không hợp lệ: {json.dumps(validation, ensure_ascii=False)}")
    records, authority_assets = iter_sources(root, manifest)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    chunk_ids: list[str] = []
    document_count = 0
    chunk_count = 0
    try:
        _database_schema(connection)
        for source_id, asset in authority_assets.items():
            connection.execute(
                "INSERT INTO authority_assets VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id,
                    asset["document_id"],
                    asset["path"],
                    asset["priority"],
                    asset["priority_level"],
                    asset["status"],
                    asset.get("description", ""),
                ),
            )
        for record in records:
            path = root / record.path
            raw_bytes = path.read_bytes()
            raw = raw_bytes.decode("utf-8", errors="replace")
            document_key = _sha256(record.path)
            checksum = _sha256(raw_bytes)
            authority_json = json.dumps(record.authority_paths, ensure_ascii=False)
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document_key,
                    record.document_id,
                    record.source_id,
                    record.path,
                    record.project_id,
                    record.priority,
                    record.priority_level,
                    record.status,
                    record.modality,
                    checksum,
                    authority_json,
                ),
            )
            document_count += 1
            for index, chunk in enumerate(chunk_document(record.path, raw)):
                chunk_id = _sha256(
                    "|".join(
                        [record.project_id, record.path, chunk.section, str(index), chunk.content]
                    )
                )[:24]
                title = f"{record.path} — {chunk.section}"
                connection.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        chunk_id,
                        document_key,
                        record.document_id,
                        record.source_id,
                        record.path,
                        record.project_id,
                        record.priority,
                        record.priority_level,
                        record.status,
                        record.modality,
                        chunk.section,
                        chunk.line_start,
                        chunk.line_end,
                        title,
                        chunk.content,
                        authority_json,
                    ),
                )
                connection.execute(
                    "INSERT INTO chunks_fts(chunk_id, title, content) VALUES (?, ?, ?)",
                    (chunk_id, title, chunk.content),
                )
                chunk_ids.append(chunk_id)
                chunk_count += 1
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "project_id": manifest["project_id"],
            "project_title": manifest.get("project_title", ""),
            "manifest_sha256": _sha256(manifest_path.read_bytes()),
            "built_at": datetime.now(timezone.utc).isoformat(),
            "documents": document_count,
            "chunks": chunk_count,
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [(key, str(value)) for key, value in metadata.items()],
        )
        connection.commit()
    finally:
        connection.close()
    return {
        **metadata,
        "authority_assets": len(authority_assets),
        "chunk_ids_sha256": _sha256("\n".join(sorted(chunk_ids))),
        "db_path": str(db_path),
    }


def _fts_query(query: str) -> tuple[str, list[str]]:
    terms: list[str] = []
    for token in _TOKEN_RE.findall(query.lower()):
        if len(token) < 2 or token in terms:
            continue
        terms.append(token)
    if not terms:
        return "", []
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in terms), terms


def _priority_boost(priority: str) -> float:
    return {"P0": 2.0, "P1": 1.2, "P2": 0.5, "P3": 0.1}.get(priority, 0.0)


def search_index(
    db_path: Path = DEFAULT_DB,
    query: str = "",
    top_k: int = 5,
    project_id: str = DEFAULT_PROJECT_ID,
    include_reference: bool = False,
) -> list[dict[str, Any]]:
    fts_query, terms = _fts_query(query)
    if not fts_query or top_k <= 0:
        return []
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT c.*, bm25(chunks_fts, 3.0, 1.0) AS bm25_rank
            FROM chunks_fts
            JOIN chunks AS c ON c.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ?
              AND c.project_id = ?
            ORDER BY bm25_rank ASC
            LIMIT ?
            """,
            (fts_query, project_id, max(top_k * 8, top_k)),
        ).fetchall()
    finally:
        connection.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        if not include_reference and row["status"] in {"LEGACY", "REFERENCE"}:
            continue
        content_lower = row["content"].lower()
        term_hits = sum(1 for term in terms if term in content_lower)
        lexical = -float(row["bm25_rank"])
        authority_paths = json.loads(row["authority_paths_json"])
        score = lexical + term_hits * 0.08 + _priority_boost(row["priority"])
        if authority_paths:
            score += 0.75
        citation = f"{row['path']}#{row['section']} (dòng {row['line_start']}-{row['line_end']})"
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "path": row["path"],
                "section": row["section"],
                "line_start": row["line_start"],
                "line_end": row["line_end"],
                "priority": row["priority"],
                "priority_level": row["priority_level"],
                "status": row["status"],
                "authority_paths": authority_paths,
                "citation": citation,
                "score": round(score, 6),
                "snippet": re.sub(r"\s+", " ", row["content"]).strip()[:500],
                "content": row["content"],
            }
        )
    results.sort(key=lambda item: (-item["score"], item["path"], item["line_start"]))
    diverse_results: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for result in results:
        if result["path"] in seen_paths:
            continue
        seen_paths.add(result["path"])
        diverse_results.append(result)
        if len(diverse_results) == top_k:
            break
    return diverse_results


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Kiểm tra nguồn canonical và nguồn P0")
    subparsers.add_parser("build", help="Tạo lại SQLite FTS5 index local")
    search_parser = subparsers.add_parser("search", help="Tra cứu có metadata và citation")
    search_parser.add_argument("query", nargs="+", help="Câu hỏi hoặc cụm từ cần tìm")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--include-reference", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = _parse_args(argv or sys.argv[1:])
    try:
        if args.command == "validate":
            payload = validate_corpus(args.root.resolve(), args.manifest.resolve())
        elif args.command == "build":
            payload = build_index(args.root.resolve(), args.manifest.resolve(), args.db.resolve())
        else:
            payload = search_index(
                args.db.resolve(),
                " ".join(args.query),
                top_k=args.top_k,
                include_reference=args.include_reference,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (CorpusError, OSError, sqlite3.Error) as exc:
        print(f"RAG ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
