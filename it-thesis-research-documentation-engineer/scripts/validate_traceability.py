#!/usr/bin/env python3
"""Validate a requirements traceability CSV without modifying it."""
import argparse,csv,sys
from pathlib import Path
REQ=['requirement_id','requirement','type','priority','source','design_element','implementation_artifact','verification_method','test_id','evidence_result','status','report_section']

def blank(v): return not (v or '').strip()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('csvfile'); args=ap.parse_args()
    p=Path(args.csvfile); rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
    fields=list(rows[0].keys()) if rows else []
    missing=[x for x in REQ if x not in fields]
    if missing:
        print('FAIL missing columns:',', '.join(missing)); return 2
    errors=[]; warns=[]; ids=set()
    for i,r in enumerate(rows,2):
        rid=r['requirement_id'].strip()
        if not rid: errors.append(f'row {i}: missing requirement_id')
        elif rid in ids: errors.append(f'row {i}: duplicate requirement_id {rid}')
        ids.add(rid)
        st=(r['status'] or '').strip().upper()
        if st in {'IMPLEMENTED','TESTED','MEASURED','VALIDATED','DONE','PASS'}:
            if blank(r['implementation_artifact']): warns.append(f'{rid}: status {st} but no implementation artifact')
        if st in {'TESTED','MEASURED','VALIDATED','PASS'}:
            if blank(r['verification_method']) or blank(r['evidence_result']): errors.append(f'{rid}: {st} requires verification method and evidence result')
        if r['priority'].strip().upper() in {'HIGH','MUST','P0','P1'}:
            for c in ['design_element','verification_method','report_section']:
                if blank(r[c]): warns.append(f'{rid}: high-priority requirement missing {c}')
    for x in errors: print('FAIL',x)
    for x in warns: print('WARN',x)
    print(f'SUMMARY rows={len(rows)} fail={len(errors)} warn={len(warns)}')
    return 2 if errors else (1 if warns else 0)
if __name__=='__main__': sys.exit(main())
