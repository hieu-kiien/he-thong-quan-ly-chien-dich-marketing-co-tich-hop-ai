#!/usr/bin/env python3
"""Read-only project inventory for thesis/research documentation."""
from pathlib import Path
import argparse, json, hashlib

SKIP={'.git','node_modules','.venv','venv','__pycache__','dist','build','.idea','.vscode'}
KINDS={
    '.tex':'latex','.sty':'latex-style','.cls':'latex-class','.bib':'bibliography',
    '.py':'python','.js':'javascript','.ts':'typescript','.java':'java','.cs':'csharp',
    '.sql':'sql','.db':'database','.sqlite':'database','.yml':'config','.yaml':'config',
    '.toml':'config','.json':'json','.env':'secret-config','.md':'documentation',
    '.pdf':'report','.docx':'report','.png':'image','.jpg':'image','.jpeg':'image','.svg':'vector-image'
}

def sha256_small(p,limit=5_000_000):
    try:
        if p.stat().st_size>limit: return None
        h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
    except Exception: return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--json',dest='out')
    args=ap.parse_args(); root=Path(args.root).resolve()
    rows=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or any(part in SKIP for part in p.parts): continue
        rel=p.relative_to(root).as_posix(); ext=p.suffix.lower()
        kind=KINDS.get(ext,'other')
        rows.append({'path':rel,'kind':kind,'size':p.stat().st_size,'sha256':sha256_small(p)})
    summary={}
    for r in rows: summary[r['kind']]=summary.get(r['kind'],0)+1
    data={'root':str(root),'file_count':len(rows),'summary':summary,'files':rows}
    if args.out: Path(args.out).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'file_count':len(rows),'summary':summary},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
