# Security and Operations Documentation

## Security method

Use NIST SSDF as a secure-development reference, OWASP Threat Modeling for structured threat analysis, and OWASP ASVS for relevant web application verification requirements. Do not claim certification unless an authorized process established it.

## Threat modeling flow

1. Decompose the system and trust boundaries.
2. Identify assets and data flows.
3. Identify threats/abuse cases.
4. Rank/prioritize risk using a stated method.
5. Identify mitigations.
6. Verify mitigations.
7. Revisit when architecture changes.

Use a DFD/security view when it clarifies trust boundaries.

## Evidence areas

- authentication;
- authorization/RBAC;
- session/token handling;
- input validation;
- injection protection;
- sensitive data handling;
- secret management;
- logging/audit;
- dependency management;
- error handling;
- secure configuration;
- backup/recovery when in scope.

## Operations

Document when relevant:
- deployment topology;
- config sources;
- environment separation;
- health checks;
- logs, metrics, traces;
- SLO/SLA only if actually defined;
- failure/recovery procedures;
- backup/restore evidence;
- scheduled jobs/workers;
- external service dependencies.

Google SRE and cloud Well-Architected frameworks are useful question banks for observability/reliability, not proof that the project is production-ready.
