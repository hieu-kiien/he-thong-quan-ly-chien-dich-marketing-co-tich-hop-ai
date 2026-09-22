# Full Project Workflow

## Phase 1: Project fingerprint

Record:
- document class and engine;
- paper size/margins/text width;
- main font;
- caption/label style;
- figure/table directories;
- build command;
- existing source-backed vs raster-only visuals.

## Phase 2: Visual inventory

For each chapter/section, collect:
- existing figure/table/chart/listing;
- communication question;
- source/evidence;
- current format;
- print risk;
- semantic risk;
- replacement needed? yes/no.

## Phase 3: Visual Coverage Map

Use `templates/visual-coverage-map.csv`.

Prioritize:
1. technically incorrect/misleading figures;
2. unreadable or rasterized technical diagrams;
3. missing high-value architecture/data/behavior figures;
4. inconsistent notation/naming;
5. cosmetic improvements.

## Phase 4: Source traceability

Typical evidence paths:
- architecture: source tree, dependencies, config, API, deployment files;
- ERD: DDL, migrations, ORM, constraints;
- sequence/state: service code, API handlers, business rules, tests;
- results: CSV/JSON/database/test logs/notebooks;
- UI: application screenshots or source mockups.

## Phase 5: Generation

For each visual:
- write semantic manifest;
- pick renderer;
- generate editable source;
- render vector output;
- integrate into LaTeX;
- add caption/label/reference;
- validate.

## Phase 6: Thesis-wide consistency pass

Normalize:
- component/entity names;
- abbreviations;
- visual palette;
- box/line semantics;
- typography;
- file naming;
- captions;
- cross-references;
- status terms.

## Phase 7: Final print pass

Compile final PDF and inspect:
- cover/front matter/list of figures/tables;
- pages containing complex figures;
- pages containing large tables;
- landscape pages;
- grayscale-rendered samples if printing B/W is plausible;
- fonts/images/page-size via PDF audit tools;
- PDF/A if required.
