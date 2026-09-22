# Documentation Information Architecture

## Principle

Documentation is a system with audiences, entry points, navigation, source-of-truth boundaries, and maintenance rules. Do not treat the thesis PDF as the only documentation artifact.

## Audience map

Typical audiences and needs:
- assessor/supervisor: problem, contribution, rigor, evidence, limitations;
- developer/maintainer: repository map, architecture, interfaces, rationale, setup, tests;
- operator: configuration, deployment, health, logs, recovery;
- user/stakeholder: workflow and expected behavior;
- security reviewer: trust boundaries, permissions, sensitive data, mitigations;
- future project team: why decisions were made and what remains unresolved.

Design documentation so each audience has an obvious entry point.

## Documentation layers

### Layer 1 — Orientation
- README / project overview;
- purpose and scope;
- quick start;
- repository map;
- links to deeper docs.

### Layer 2 — Design and rationale
- requirements;
- architecture overview and views;
- ADRs;
- data model;
- key workflows;
- security/AI design.

### Layer 3 — Interface/reference
- API schema;
- database dictionary;
- configuration reference;
- error/status codes;
- role/permission matrix.

### Layer 4 — Verification/evidence
- test plan and executed results;
- benchmark/evaluation setup;
- raw result links;
- reproducibility manifest;
- audit reports.

### Layer 5 — Operations/maintenance
- deployment/runbook;
- backup/recovery if applicable;
- observability;
- known issues;
- release/change history.

### Layer 6 — Academic communication
- thesis/report;
- appendices;
- bibliography;
- presentation/demo artifacts.

## Source of truth

For each fact category designate a canonical source when possible:
- API -> OpenAPI/router definitions;
- schema -> migrations/DDL;
- dependencies -> lockfile/manifest;
- configuration -> config schema/.env.example;
- architecture rationale -> ADR/design doc;
- executed results -> raw logs/data + analysis script;
- thesis narrative -> synthesized explanation, not source-of-truth for implementation facts.

Avoid duplicating volatile facts in many documents. Link to generated/canonical sources when practical.

## Design docs versus living reference docs

A design doc records a proposal/decision and can become historical after implementation. Do not silently rewrite it until it looks like the current system if preserving decision history matters. Maintain current reference docs separately or clearly mark the design doc status.

## Information flow inside a chapter

Prefer this rhythm:
1. question/context;
2. decision/model;
3. evidence/figure/table;
4. interpretation/rationale;
5. limitation/trade-off;
6. transition.

## Tables, code, screenshots, figures

- Table: exact structured comparison or specification.
- Figure: spatial/relational/behavioral concept.
- Plot: quantitative evidence.
- Code snippet: explains one design property, not proof of the whole system.
- Screenshot: UI/observed state evidence when visual appearance matters, not a substitute for source/test logs.

## Terminology and cross-references

Maintain a small controlled vocabulary for actors, modules, statuses, and AI terms. Use one canonical name consistently across code, diagrams, tables, and prose unless explaining aliases.

Use LaTeX labels/references rather than hard-coded figure/table numbers.

## Maintenance

Every major documentation artifact should have at least one of:
- generated from source;
- reviewed with the corresponding code/schema change;
- version/date/commit marker;
- explicit historical status.
