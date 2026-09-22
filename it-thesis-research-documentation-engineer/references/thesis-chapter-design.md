# Thesis / Project Report Design

## The report is an argument

A strong technical report lets an assessor answer:
- What problem was addressed?
- Why does it matter?
- What existed before?
- What was actually contributed?
- What requirements drove the work?
- Why were the design decisions reasonable?
- What was actually implemented?
- How was it tested/evaluated?
- What evidence supports the conclusions?
- What limitations remain?

## Strong chapter logic

Adapt to the official template.

### Introduction
Problem context -> motivation -> gap -> objectives/questions -> scope -> contributions -> structure.

### Preparation / Background / Related Work
Starting point -> domain research -> related systems/literature -> requirements -> technology/design drivers.

### Design
Architecture views -> data -> workflows -> security/AI -> decisions/trade-offs -> planned evaluation hooks.

### Implementation
Actual repository/modules -> interfaces -> implementation details that matter to design/evaluation -> deviations from plan.

### Evaluation
Questions -> setup -> experiments/tests -> results -> interpretation -> validity/limitations.

### Conclusion
Objectives revisited -> evidence-based achievements -> limitations -> future work.

## Section-level pattern

For technical sections, prefer:
1. state the question/decision;
2. present evidence/design;
3. explain rationale;
4. explain consequences/limitations;
5. link to validation or next section.

## What belongs in appendices

Good appendix material:
- full DDL;
- long code listings;
- complete test logs;
- raw questionnaires;
- additional tables;
- setup scripts;
- detailed API schemas.

Essential reasoning must remain in the main text.

## University benchmark lessons

Top CS project guidance commonly emphasizes:
- clear starting point;
- professional requirements/design process;
- repository overview;
- distinction between design and implementation;
- evaluation with explicit experimental setup/metrics;
- reproducibility and evidence;
- concise main narrative with supporting detail in appendices.
