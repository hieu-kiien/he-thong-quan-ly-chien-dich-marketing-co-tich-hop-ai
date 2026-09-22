#!/usr/bin/env python3
"""Audit a compiled thesis PDF using common Poppler tools when installed.

Checks page size, font embedding, and effective raster image resolution. PDF/A
validation is reported only if veraPDF is installed.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def add(out, level, code, msg): out.append({"level": level, "code": code, "message": msg})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--expected-paper", choices=["a4", "letter", "auto"], default="auto")
    ap.add_argument("--json", action="store_true", dest="json_out")
    args = ap.parse_args()
    pdf = args.pdf.resolve()
    issues, facts = [], {}
    if not pdf.exists():
        print(f"FAIL: PDF not found: {pdf}")
        return 2

    if shutil.which("pdfinfo"):
        rc, so, se = run(["pdfinfo", str(pdf)])
        facts["pdfinfo"] = so
        m = re.search(r"Page size:\s*([0-9.]+) x ([0-9.]+) pts", so)
        if m:
            w, h = float(m.group(1)), float(m.group(2))
            facts["page_size_pt"] = [w, h]
            if args.expected_paper != "auto":
                target = (595.28, 841.89) if args.expected_paper == "a4" else (612.0, 792.0)
                portrait_ok = abs(w-target[0]) < 4 and abs(h-target[1]) < 4
                landscape_ok = abs(h-target[0]) < 4 and abs(w-target[1]) < 4
                if not (portrait_ok or landscape_ok):
                    add(issues, "FAIL", "page-size", f"Page size {w:.1f}x{h:.1f} pt does not match expected {args.expected_paper.upper()}")
    else:
        add(issues, "NOT VERIFIED", "pdfinfo", "pdfinfo is unavailable; page size not checked")

    if shutil.which("pdffonts"):
        rc, so, se = run(["pdffonts", str(pdf)])
        bad = []
        lines = so.splitlines()[2:]
        for line in lines:
            if not line.strip(): continue
            parts = line.split()
            # Poppler columns end with emb sub uni object ID
            if len(parts) >= 7:
                emb = parts[-5].lower()
                if emb == "no": bad.append(line.strip())
        facts["font_lines"] = len(lines)
        if bad:
            add(issues, "FAIL", "fonts-not-embedded", f"Found {len(bad)} font entries not embedded")
    else:
        add(issues, "NOT VERIFIED", "pdffonts", "pdffonts is unavailable; font embedding not checked")

    if shutil.which("pdfimages"):
        rc, so, se = run(["pdfimages", "-list", str(pdf)])
        low = []
        for line in so.splitlines():
            parts = line.split()
            if len(parts) < 14 or not parts[0].isdigit():
                continue
            # Expected columns include x-ppi and y-ppi before size/ratio
            ppis = []
            for token in parts:
                try:
                    v = float(token)
                    if 20 <= v <= 5000: ppis.append(v)
                except Exception: pass
            # Poppler output is variable; use the last plausible two DPI-ish numbers conservatively.
            if len(ppis) >= 2:
                xppi, yppi = ppis[-2], ppis[-1]
                if min(xppi, yppi) < 300:
                    low.append((parts[0], xppi, yppi))
        facts["low_resolution_images"] = low
        if low:
            add(issues, "WARN", "raster-resolution", f"Found {len(low)} raster image entries that may be below 300 dpi effective resolution; inspect pdfimages output manually")
    else:
        add(issues, "NOT VERIFIED", "pdfimages", "pdfimages is unavailable; raster resolution not checked")

    if shutil.which("verapdf"):
        rc, so, se = run(["verapdf", str(pdf)])
        facts["verapdf_exit_code"] = rc
        if rc != 0 or "non-compliant" in so.lower() or "failed" in so.lower():
            add(issues, "WARN", "pdfa", "veraPDF did not confirm conformance; inspect validator output")
    else:
        add(issues, "NOT VERIFIED", "pdfa", "veraPDF is unavailable; PDF/A conformance not checked")

    failures = sum(i["level"] == "FAIL" for i in issues)
    warnings = sum(i["level"] == "WARN" for i in issues)
    nv = sum(i["level"] == "NOT VERIFIED" for i in issues)
    result = {"pdf": str(pdf), "failures": failures, "warnings": warnings, "not_verified": nv, "facts": facts, "issues": issues}
    if args.json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PDF audit: {pdf}")
        for i in issues: print(f"{i['level']}: {i['code']}: {i['message']}")
        print(f"SUMMARY: {failures} FAIL, {warnings} WARN, {nv} NOT VERIFIED")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
