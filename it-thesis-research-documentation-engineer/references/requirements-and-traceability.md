# Requirements and Traceability

## Reference approach

Use ISO/IEC/IEEE 29148 concepts as a requirements-engineering benchmark, while following course-specific conventions.

## Requirement categories

- stakeholder/business needs;
- system/software functional requirements;
- quality/nonfunctional requirements;
- interface requirements;
- data requirements;
- security/privacy requirements;
- AI-specific requirements;
- operational requirements;
- constraints;
- acceptance criteria.

## Good requirement properties

A useful requirement is sufficiently:
- necessary;
- singular;
- unambiguous;
- feasible;
- verifiable;
- traceable;
- consistent with related requirements.

Avoid subjective words such as fast, easy, secure, intelligent, user-friendly without measurable interpretation.

## Quality attribute scenarios

For performance, reliability, security, maintainability, etc., express:
- source of stimulus;
- stimulus;
- environment;
- affected artifact;
- expected response;
- measurable response criterion.

## Traceability chain

Maintain:
Requirement -> design -> implementation -> verification/test -> evidence/result -> report section.

For every high-priority requirement, answer:
1. Where is it designed?
2. Where is it implemented?
3. How is it verified?
4. Where is the result recorded?

Mark `PLANNED` tests separately from `EXECUTED` tests.

## Change discipline

When a requirement changes, inspect the impact on:
- architecture;
- schema;
- API;
- UI/workflow;
- tests;
- report figures/tables;
- evaluation.
