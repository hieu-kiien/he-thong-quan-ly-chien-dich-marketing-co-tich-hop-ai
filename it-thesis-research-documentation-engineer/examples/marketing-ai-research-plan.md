# Worked research plan: AI-assisted marketing campaign management system

This example shows how the skill should research a project similar to a campaign-management system with Python, SQLite, RBAC, dashboards, and AI-assisted content drafting.

## 1. Do not start from “AI marketing system” as one giant topic

Decompose into capabilities:
1. identity/RBAC;
2. product/channel master data;
3. campaign lifecycle and budget;
4. content workflow and approval;
5. scheduling/publishing;
6. metrics/KPI reporting;
7. AI ideation/drafting;
8. grounding/context selection;
9. AI validation/logging/audit;
10. security/error handling/operations.

Research each capability separately, then synthesize the architecture.

## 2. Starting point

Establish whether the repository already contains:
- real backend implementation or only report snippets;
- executable DDL;
- tests or only planned test tables;
- actual AI provider integration or mock adapter;
- deployment scripts;
- real experiment logs.

Do not describe a planned backend folder tree as implemented unless repository evidence confirms it.

## 3. Requirements package

Examples:
- FR-CONT-01: Marketer can create/edit draft content for an assigned campaign.
- FR-APP-01: Only Manager can approve PENDING content.
- FR-AI-01: User can request AI draft using selected campaign/product/channel context.
- QR-AI-01: Invalid AI output must not overwrite an existing draft.
- QR-SEC-01: Approval authorization must be enforced at backend endpoints.
- QR-TRACE-01: AI invocation records provider, prompt version, result status and source IDs.

Each requirement should map to design, implementation, and executed evidence.

## 4. Architecture package

Useful views:
- System Context;
- Container/runtime view;
- physical ERD split into core and operations/AI if needed for A4 readability;
- content state machine;
- AI generation sequence including invalid JSON/timeout path;
- security DFD/trust-boundary view if external model/API is used.

Beyond diagrams, document why FastAPI/SQLite/adapter pattern were selected under actual constraints, alternatives considered, and consequences.

## 5. AI research/evaluation

Do not evaluate “AI” with screenshots alone.

Example evaluation questions:
- EQ-AI-1: What percentage of AI responses pass the declared output schema?
- EQ-AI-2: How often does output preserve required source IDs and channel rules?
- EQ-AI-3: What latency distribution is observed under the selected provider/model?
- EQ-AI-4: How much human editing is required before submission to approval?
- EQ-AI-5: Do timeout/invalid-output paths preserve the previous draft and log the failure?

Record provider/model/version/date, prompt version, test cases, repetitions and raw results.

## 6. Thesis narrative

A defensible narrative is:
problem -> stakeholder workflow -> requirements -> design drivers -> architecture/data/AI controls -> implementation -> requirement-based tests -> AI evaluation -> limitations.

Avoid a narrative that is only:
Python -> SQL -> screenshots -> AI -> conclusion.
