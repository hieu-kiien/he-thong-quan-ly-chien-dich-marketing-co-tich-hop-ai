# Evidence and Claim Discipline

## Claim taxonomy

Tag important statements mentally as:
- observed fact;
- source-backed fact;
- measured result;
- interpretation;
- design rationale;
- assumption;
- proposal;
- limitation.

Do not phrase all of them as equally certain facts.

## Strong evidence order

For implementation claims:
1. executed test/log/measurement;
2. source/config/schema inspection;
3. generated documentation from source;
4. report prose;
5. intent/plan.

For external claims:
1. current standard/spec/primary docs;
2. peer-reviewed research;
3. recognized academic/industry guidance;
4. secondary commentary.

## Examples

Weak: “The system is secure because JWT is used.”

Better: “Authentication uses signed bearer tokens; authorization is enforced by backend role checks on protected endpoints. This report does not claim full application security; targeted authorization and input-validation tests are reported in Section X.”

Weak: “AI improves marketing content.”

Better: “On the defined 30-case evaluation set, version P3 produced schema-valid output in X/Y requests and was accepted without mandatory correction in A/B reviews. These results only support the defined scenarios and model configuration.”

## Inconsistency handling

When report, code, and schema disagree:
- identify the discrepancy;
- determine the strongest source of truth;
- do not silently rewrite history;
- update affected diagrams/tables/claims;
- record unresolved items as NOT VERIFIED.
