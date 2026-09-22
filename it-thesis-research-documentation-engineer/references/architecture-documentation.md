# Architecture Documentation

## Reference approach

Use ISO/IEC/IEEE 42010:2022 and CMU SEI Views and Beyond as conceptual benchmarks. Architecture documentation is stakeholder- and concern-driven, multi-view, and includes rationale beyond diagrams.

## Start with stakeholders and concerns

Examples:
- user: can I complete the workflow safely?
- developer: where does business logic live?
- assessor: does the implementation match the design?
- operator: how is it configured, monitored, and recovered?
- security reviewer: where are trust boundaries and sensitive data?
- maintainer: what are the stable interfaces and decisions?

## Recommended view package

Select only useful views:
- context/environment;
- runtime/container;
- module/component;
- data;
- behavior/state/sequence;
- deployment/operations;
- security/trust-boundary;
- mapping among views.

## Each view must document more than the graphic

Record:
- view purpose and stakeholders;
- scope;
- element catalog;
- relationships/interfaces;
- variability/configuration;
- quality implications;
- assumptions;
- rationale;
- known risks;
- mapping to source code/config.

## Architecture decisions

Use ADRs for consequential choices such as framework, database, auth strategy, AI provider abstraction, sync vs async workflow, deployment topology, caching, or schema design.

An ADR should capture options and consequences. Do not backfill fictional alternatives after implementation; distinguish contemporaneous evidence from retrospective rationale.

## Quality attributes

Use ISO/IEC 25010:2023 as a quality-model reference when helpful. Do not claim all characteristics matter equally. Select those that drive the project and define measurable scenarios.

## Architecture review

Use well-architected frameworks as question banks, not as certifications. Ask about reliability, security, operational excellence, performance efficiency, cost, and sustainability when appropriate to project scope.
