#!/usr/bin/env python3
"""Lightweight structural validator for this Agent Skill directory."""
from __future__ import annotations
import argparse,re,sys
from pathlib import Path

REQUIRED=[
 'SKILL.md','README-VI.md','LICENSE',
 'references/project-research-protocol.md','references/related-work-and-benchmarking.md',
 'references/requirements-and-traceability.md','references/architecture-documentation.md',
 'references/evaluation-and-experimentation.md','references/ai-system-documentation.md',
 'references/security-and-operations.md','references/thesis-chapter-design.md',
 'references/documentation-information-architecture.md','references/evidence-and-claim-discipline.md',
 'references/diagram-routing.md','references/notation-rules.md','references/latex-print-standard.md',
 'templates/project-research-plan.md','templates/requirements-traceability.csv',
 'templates/evaluation-plan.md','templates/adr-template.md','templates/visual-manifest.example.json',
 'scripts/inventory_project.py','scripts/validate_traceability.py','scripts/validate_research_pack.py',
 'scripts/audit_latex_project.py','scripts/audit_pdf.py','scripts/validate_visual_manifest.py'
]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('skill_dir',nargs='?',type=Path,default=Path(__file__).resolve().parents[1])
    root=ap.parse_args().skill_dir.resolve(); problems=[]
    p=root/'SKILL.md'
    if p.exists():
        text=p.read_text(encoding='utf-8')
        m=re.match(r'---\n(.*?)\n---\n',text,re.S)
        if not m: problems.append('SKILL.md YAML frontmatter delimiters missing')
        else:
            fm=m.group(1)
            nm=re.search(r'^name:\s*(.+)$',fm,re.M)
            desc=re.search(r'^description:\s*(.+)$',fm,re.M)
            if not nm or nm.group(1).strip()!=root.name: problems.append(f'frontmatter name must equal folder name: {root.name}')
            if not desc or len(desc.group(1).strip())<80: problems.append('description missing or too short')
            if 'version: "3.0.0"' not in fm: problems.append('expected metadata version 3.0.0')
    for rel in REQUIRED:
        q=root/rel
        if not q.exists(): problems.append(f'missing {rel}')
        elif q.is_file() and q.stat().st_size==0: problems.append(f'empty {rel}')
    if problems:
        for x in problems: print('FAIL:',x)
        return 2
    print('PASS: V3 skill package structure looks valid')
    return 0
if __name__=='__main__': sys.exit(main())
