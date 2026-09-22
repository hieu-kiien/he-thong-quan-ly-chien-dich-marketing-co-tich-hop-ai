# Worked Example: AI-Integrated Marketing Campaign Management Thesis

This example demonstrates routing and splitting decisions for a project with:
- Python/FastAPI backend;
- relational SQLite schema;
- campaign/content/scheduling/metrics modules;
- AI-assisted content generation;
- human approval workflow.

It is a pattern example, not a substitute for reading the actual repository.

## Recommended high-value visual set

### 1. System Context
Question: Who uses the marketing system and which external services exist outside its boundary?

Keep internal database tables and Python layers out of this view.

### 2. Container / high-level architecture
Question: What runtime applications/datastores make up the solution and how do they communicate?

Typical evidence to verify:
- web UI;
- FastAPI application;
- service/business layer if it is a meaningful runtime/code responsibility;
- database;
- external AI provider if actually configured/used.

Do not draw an `AI Audit Database` as a separate datastore when `ai_logs` is only a table in the same SQLite database.

### 3. Physical ERD split for A4
A full schema with nine or more detailed tables may be too dense at a thesis text width around 15–16 cm.

Prefer:
- ERD Core: users, product categories, products, campaigns, channels, content;
- ERD Operations/AI: schedules, metrics, AI logs plus necessary parent references;
- optional tiny overview showing bounded-group relationships.

Derive optionality from DDL. A nullable FK should not be drawn as mandatory.

### 4. Content lifecycle state machine
Question: Which content states are legal and who/what triggers transitions?

Example state vocabulary might include DRAFT, AI_DRAFT, PENDING, APPROVED, REJECTED, PUBLISHED, but the actual schema/code is the authority.

### 5. AI generation sequence
Question: How is a draft generated, validated, logged, preserved on error, and submitted for human approval?

Use `alt` for valid vs invalid/timeout and another `alt` for approve vs reject when those branches are part of the implementation/design claim.

### 6. RBAC/login sequence only if it adds new understanding
Do not add it merely because every thesis has a login flow. Add it when authentication/authorization is an important assessed requirement and the diagram clarifies backend enforcement.

## Why this is research-grade compared with one giant diagram

- Each visual answers one question.
- Architecture is not polluted with physical database columns.
- ERD is not shrunk below readable font size.
- AI behavior includes failure and human-control paths, not only the happy path.
- Proposed and implemented parts can be distinguished.
- Each figure can be traced back to code/schema/requirements.
