# AI/LLM System Documentation

## Purpose

Document AI as a bounded, fallible subsystem with explicit authority, data inputs, controls, measurements, and limitations.

Use NIST AI RMF / Generative AI Profile and human-centered AI guidance as reference frameworks when relevant. They are not automatic compliance claims.

## Required questions

1. What task is AI used for, and why is AI appropriate?
2. What task remains deterministic or human-controlled?
3. What data/context enters the model?
4. Which data is excluded and why?
5. What provider/model/version/configuration is used?
6. How are prompts/versioning managed?
7. What output schema/validation exists?
8. What happens on invalid, unsafe, irrelevant, or unavailable output?
9. What decisions require human review?
10. What is logged for traceability?
11. How are secrets and personal/sensitive data protected?
12. What are latency/cost limits?
13. How is quality evaluated?
14. What are known limitations and reproducibility constraints?

## Human oversight

Document the actual authority boundary. If only Manager can approve, show that the backend enforces it. UI labels alone are not sufficient evidence.

## AI evaluation dimensions

Depending on task:
- schema validity;
- grounded/source-supported content;
- completeness;
- factuality relative to supplied context;
- instruction adherence;
- format/channel compliance;
- unsafe/disallowed content rate;
- latency;
- cost/token usage;
- human edit distance/time saved;
- reviewer acceptance/rejection and reasons.

Never collapse all dimensions into a single “AI accuracy” number without justification.
