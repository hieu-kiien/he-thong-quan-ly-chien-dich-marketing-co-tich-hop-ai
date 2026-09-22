#!/usr/bin/env python3
"""Check presence and basic structure of a research/documentation pack."""
from pathlib import Path
import argparse,csv,sys
EXPECTED=['project-research-plan.md','source-inventory.csv','evidence-ledger.csv','related-work-matrix.csv','requirements-traceability.csv','evaluation-plan.md']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('dir'); args=ap.parse_args(); d=Path(args.dir)
    fail=[]; warn=[]
    for f in EXPECTED:
        p=d/f
        if not p.exists(): warn.append(f'missing recommended artifact: {f}')
        elif p.stat().st_size==0: fail.append(f'empty artifact: {f}')
    rt=d/'requirements-traceability.csv'
    if rt.exists() and rt.stat().st_size:
        try:
            rows=list(csv.DictReader(rt.open(encoding='utf-8-sig')))
            if not rows: warn.append('requirements-traceability.csv has no requirement rows')
        except Exception as e: fail.append(f'traceability CSV unreadable: {e}')
    for x in fail: print('FAIL',x)
    for x in warn: print('WARN',x)
    print(f'SUMMARY fail={len(fail)} warn={len(warn)}')
    return 2 if fail else (1 if warn else 0)
if __name__=='__main__': sys.exit(main())
