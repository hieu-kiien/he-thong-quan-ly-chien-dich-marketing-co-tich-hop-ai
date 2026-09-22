#!/usr/bin/env python3
"""Validate a visual-manifest JSON file for common research-grade requirements.

No third-party dependencies. This is a semantic lint, not a replacement for expert review.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

VALID_CARD = {"0..1", "1", "0..*", "1..*", "*", "many", "one"}


def issue(level, code, msg, out):
    out.append({"level": level, "code": code, "message": msg})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--json", action="store_true", dest="json_out")
    args = ap.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: cannot read JSON: {e}")
        return 2

    out = []
    required = ["figure_id", "question", "diagram_type", "scope", "evidence_status", "sources", "elements", "relationships", "print", "outputs"]
    for key in required:
        if key not in data:
            issue("FAIL", "missing-field", f"Missing required field: {key}", out)

    dtype = str(data.get("diagram_type", "")).lower()
    elements = data.get("elements") or []
    rels = data.get("relationships") or []
    ids = set()

    for i, el in enumerate(elements):
        eid = el.get("id")
        if not eid:
            issue("FAIL", "element-id", f"Element #{i+1} has no id", out)
        elif eid in ids:
            issue("FAIL", "duplicate-element-id", f"Duplicate element id: {eid}", out)
        else:
            ids.add(eid)
        if not el.get("name"):
            issue("FAIL", "element-name", f"Element {eid or i+1} has no name", out)
        if not el.get("type"):
            issue("WARN", "element-type", f"Element {eid or i+1} has no type", out)

    for i, rel in enumerate(rels):
        src, dst = rel.get("from"), rel.get("to")
        if not src or not dst:
            issue("FAIL", "relationship-endpoint", f"Relationship #{i+1} lacks from/to", out)
        else:
            if src not in ids:
                issue("FAIL", "unknown-source", f"Relationship #{i+1} source not found: {src}", out)
            if dst not in ids:
                issue("FAIL", "unknown-target", f"Relationship #{i+1} target not found: {dst}", out)
        if not rel.get("label") and not ("erd" in dtype or "class" in dtype):
            issue("WARN", "unlabeled-relationship", f"Relationship #{i+1} has no intent label", out)

    if "c4" in dtype or "architecture" in dtype:
        for el in elements:
            et = str(el.get("type", "")).lower()
            if not el.get("responsibility"):
                issue("WARN", "c4-responsibility", f"C4 element '{el.get('name','?')}' lacks responsibility/description", out)
            if et in {"container", "component"} and not el.get("technology"):
                issue("WARN", "c4-technology", f"{el.get('type')} '{el.get('name','?')}' lacks technology", out)
        for i, rel in enumerate(rels):
            if not rel.get("label"):
                issue("FAIL", "c4-rel-label", f"C4 relationship #{i+1} must be meaningfully labeled", out)

    if "erd" in dtype or "schema" in dtype:
        for i, rel in enumerate(rels):
            a = rel.get("from_cardinality") or rel.get("source_cardinality")
            b = rel.get("to_cardinality") or rel.get("target_cardinality")
            if not a or not b:
                issue("WARN", "erd-cardinality", f"ERD relationship #{i+1} lacks cardinality/optionality on both ends", out)
            else:
                if str(a) not in VALID_CARD:
                    issue("WARN", "erd-cardinality-format", f"Unusual source cardinality '{a}' in relationship #{i+1}", out)
                if str(b) not in VALID_CARD:
                    issue("WARN", "erd-cardinality-format", f"Unusual target cardinality '{b}' in relationship #{i+1}", out)

    if "sequence" in dtype:
        for i, rel in enumerate(rels):
            if "order" not in rel:
                issue("WARN", "sequence-order", f"Sequence message #{i+1} has no explicit order", out)

    p = data.get("print") or {}
    min_font = p.get("min_font_pt")
    if min_font is None:
        issue("WARN", "print-font", "print.min_font_pt is not recorded", out)
    else:
        try:
            if float(min_font) < 8.5:
                issue("WARN", "tiny-font", f"Recorded minimum font size is {min_font} pt; redesign rather than shrink", out)
        except Exception:
            issue("WARN", "print-font-format", "print.min_font_pt is not numeric", out)
    if p.get("vector_output") is not True:
        issue("WARN", "vector-output", "Vector output is not confirmed", out)
    if p.get("grayscale_checked") is not True:
        issue("WARN", "grayscale", "Grayscale readability is NOT VERIFIED", out)

    if not data.get("sources"):
        issue("FAIL", "sources", "No evidence sources recorded", out)

    failures = sum(x["level"] == "FAIL" for x in out)
    warnings = sum(x["level"] == "WARN" for x in out)

    if args.json_out:
        print(json.dumps({"failures": failures, "warnings": warnings, "issues": out}, ensure_ascii=False, indent=2))
    else:
        for x in out:
            print(f"{x['level']}: {x['code']}: {x['message']}")
        if not out:
            print("PASS: no manifest lint issues found")
        print(f"SUMMARY: {failures} FAIL, {warnings} WARN")

    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
