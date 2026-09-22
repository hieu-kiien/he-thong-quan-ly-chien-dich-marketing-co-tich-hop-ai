#!/usr/bin/env python3
"""Non-destructive static audit for LaTeX thesis visual integration.

Checks common figure/table/reference risks. It does not edit files and does not
replace compilation or visual inspection.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path

TECHNICAL_HINTS = (
    "architecture", "arch", "erd", "schema", "database", "uml", "sequence",
    "activity", "state", "class", "deployment", "network", "flow", "flowchart",
    "bfd", "dfd", "bpmn", "diagram", "topology", "pipeline"
)
RASTER_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
GRAPHIC_EXTS = [".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"]


def strip_comments(s: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", s)


def add(issues, level, code, file, msg):
    issues.append({"level": level, "code": code, "file": str(file), "message": msg})


def resolve_graphic(tex_file: Path, root: Path, raw: str):
    p = Path(raw)
    candidates = []
    bases = [tex_file.parent / p, root / p]
    for b in bases:
        if b.suffix:
            candidates.append(b)
        else:
            candidates += [b.with_suffix(e) for e in GRAPHIC_EXTS]
    for c in candidates:
        if c.exists():
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--json", action="store_true", dest="json_out")
    args = ap.parse_args()
    root = args.root.resolve()
    tex_files = sorted(root.rglob("*.tex"))
    issues = []
    labels, refs = [], []
    figures = tables = graphics = 0
    H_count = 0

    for f in tex_files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        text = strip_comments(raw)
        labels += [(m.group(1), f) for m in re.finditer(r"\\label\{([^}]+)\}", text)]
        refs += [(m.group(1), f) for m in re.finditer(r"\\(?:ref|autoref|cref|Cref)\{([^}]+)\}", text)]
        H_count += len(re.findall(r"\\begin\{figure\}\[H\]", text)) + len(re.findall(r"\\begin\{table\}\[H\]", text))

        for env, kind in (("figure", "figure"), ("table", "table")):
            blocks = re.findall(rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}", text, flags=re.S)
            if kind == "figure": figures += len(blocks)
            else: tables += len(blocks)
            for idx, block in enumerate(blocks, 1):
                if "\\caption" not in block:
                    add(issues, "WARN", f"{kind}-caption", f, f"{kind} environment #{idx} has no caption")
                if "\\label" not in block:
                    add(issues, "WARN", f"{kind}-label", f, f"{kind} environment #{idx} has no label")
                cap = block.find("\\caption")
                lab = block.find("\\label")
                if lab >= 0 and cap >= 0 and lab < cap:
                    add(issues, "WARN", f"{kind}-label-order", f, f"{kind} environment #{idx} places label before caption")

        for m in re.finditer(r"\\includegraphics(?:\[([^]]*)\])?\{([^}]+)\}", text):
            graphics += 1
            opts, raw_path = m.group(1) or "", m.group(2).strip()
            resolved = resolve_graphic(f, root, raw_path)
            if not resolved:
                add(issues, "FAIL", "missing-graphic", f, f"Graphic not found: {raw_path}")
                continue
            lname = resolved.name.lower()
            if resolved.suffix.lower() in RASTER_EXTS and any(k in lname for k in TECHNICAL_HINTS):
                add(issues, "WARN", "raster-technical-diagram", f, f"Technical diagram is raster: {resolved.relative_to(root)}; prefer editable source + vector PDF")
            w = re.search(r"width\s*=\s*([0-9.]+)\\(?:textwidth|linewidth)", opts)
            if w:
                try:
                    val = float(w.group(1))
                    if val < 0.50:
                        add(issues, "WARN", "small-figure-width", f, f"Graphic {raw_path} inserted at {val:.2f} of text/line width; verify label readability")
                except ValueError:
                    pass

        if re.search(r"\\resizebox\s*\{\\(?:textwidth|linewidth)\}", text):
            add(issues, "WARN", "resizebox", f, "Uses resizebox to full width; verify this is not hiding a density/readability problem")
        if re.search(r"\\scalebox\s*\{", text):
            add(issues, "WARN", "scalebox", f, "Uses scalebox; verify final effective font size")

        for m in re.finditer(r"\b(?:Hình|Figure|Fig\.|Bảng|Table)\s+\d+(?:\.\d+)*", text, flags=re.I):
            add(issues, "WARN", "hardcoded-reference", f, f"Hard-coded cross-reference: '{m.group(0)}'")

        for m in re.finditer(r"\\begin\{tabular\*?\}(?:\[[^]]*\])?\{([^}]*)\}", text):
            if "|" in m.group(1):
                add(issues, "WARN", "vertical-table-rules", f, "Table uses vertical rules; verify university style or consider booktabs-style formal table")

    counts = Counter(x[0] for x in labels)
    for label, n in counts.items():
        if n > 1:
            files = [str(f.relative_to(root)) for l, f in labels if l == label]
            add(issues, "FAIL", "duplicate-label", root, f"Duplicate label '{label}' in {files}")

    known = set(counts)
    for ref, f in refs:
        if ref not in known:
            add(issues, "FAIL", "unresolved-reference", f, f"Reference has no matching label: {ref}")

    if H_count > 8:
        add(issues, "WARN", "float-H-overuse", root, f"Found {H_count} strict [H] figure/table placements; excessive forced placement can degrade pagination")

    failures = sum(i["level"] == "FAIL" for i in issues)
    warnings = sum(i["level"] == "WARN" for i in issues)
    report = {
        "root": str(root), "tex_files": len(tex_files), "figures": figures,
        "tables": tables, "includegraphics": graphics,
        "failures": failures, "warnings": warnings, "issues": issues,
    }
    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"LaTeX visual audit: {root}")
        print(f"Files={len(tex_files)} figures={figures} tables={tables} graphics={graphics}")
        for i in issues:
            try: display = str(Path(i['file']).relative_to(root))
            except Exception: display = i['file']
            print(f"{i['level']}: {i['code']}: {display}: {i['message']}")
        print(f"SUMMARY: {failures} FAIL, {warnings} WARN")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
