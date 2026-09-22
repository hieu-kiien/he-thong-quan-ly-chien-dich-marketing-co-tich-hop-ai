# Evaluation and Experimentation

## Principle

Every project should be evaluated, but evaluation must match the claims.

## Claim-to-evidence mapping

- “meets requirement” -> acceptance/requirement test;
- “prevents unauthorized approval” -> negative RBAC tests;
- “database preserves integrity” -> constraint/transaction tests;
- “fast” -> latency/throughput measurement with stated workload;
- “reliable under provider timeout” -> controlled failure-path test;
- “AI output follows schema” -> schema-valid rate on a defined test set;
- “AI output is useful” -> explicit rubric + qualified human evaluation or task metric;
- “maintainable” -> justified maintainability evidence, not code organization screenshots.

## Experimental setup

Record enough for replication:
- commit/version;
- hardware/OS/runtime;
- dependency versions;
- DB state/seed;
- model/provider/version and relevant parameters;
- dataset/workload;
- environment variables excluding secrets;
- number of runs;
- warmup/cache policy;
- commands;
- timestamps when external services can drift.

## Baselines

Use a baseline when the claim is comparative. For an AI feature, useful baselines may include:
- manual workflow;
- simple template/rule approach;
- earlier prompt version;
- no-grounding configuration;
- different model/provider, if the research question warrants it.

Do not add a baseline merely to look academic; it must answer a real question.

## Result reporting

Report raw counts and denominators where possible. Avoid only percentages for tiny samples. Use confidence intervals/statistical tests only when assumptions and sample size justify them.

## Threats to validity

Consider:
- construct validity: did the metric represent the claim?
- internal validity: could another factor explain the result?
- external validity: does the setup generalize?
- conclusion validity: is evidence sufficient for the conclusion?
- reproducibility threats: external APIs, stochastic models, changing data.

## Negative results

Document failures and limitations. A failed experiment can be useful evidence for redesign or bounded conclusions.
