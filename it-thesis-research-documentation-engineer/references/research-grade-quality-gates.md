# Research-Grade Quality Gates

Use PASS / WARN / FAIL / NOT VERIFIED. Never mark PASS for a check not actually performed.

## 1. Claim/evidence gate

PASS when every significant visual claim is traceable to source, measurements, requirements, or explicitly declared proposal/inference.

FAIL examples:
- invented cloud region/port;
- guessed ERD cardinality despite available DDL;
- benchmark bars with fabricated values;
- proposed component drawn as implemented without annotation.

## 2. Representation gate

PASS when the visual type matches the reader question and abstraction level.

WARN/FAIL examples:
- flowchart used as system architecture;
- use-case diagram used as workflow;
- physical schema mixed into C4 Context;
- sequence diagram combines unrelated scenarios.

## 3. Notation gate

Check notation-specific semantics in `notation-rules.md`.

Important checks:
- C4 title/scope/legend/type/responsibility/technology/relationship labels;
- ERD PK/FK/nullability/cardinality;
- sequence messages/branches/retries;
- state transition legality;
- BPMN gateway/flow semantics.

## 4. Stand-alone comprehension gate

A reviewer should understand the figure without reading several paragraphs.

Check:
- title/type/scope;
- meaningful names;
- acronym expansion/legend;
- arrow intent;
- status/proposal notation;
- no unexplained decorative iconography.

## 5. Density gate

At final insertion width:
- text readable;
- connectors traceable;
- no crowded clusters;
- no severe aspect-ratio mismatch with page;
- no tiny legend.

If not, split the figure.

## 6. Print/accessibility gate

Check:
- vector line art;
- robust contrast;
- grayscale interpretation;
- non-color encodings;
- sufficient raster resolution;
- no content outside margins.

## 7. Consistency gate

Across the thesis:
- same component/entity names;
- stable colors and shape meanings;
- consistent typography;
- consistent cardinality notation;
- consistent caption/label conventions;
- status terminology matches code/schema.

## 8. Reproducibility gate

PASS when source + build/render instructions are available.

WARN when only exported PDF exists.
FAIL when only a screenshot exists for a diagram that can reasonably be source-controlled.

## 9. PDF gate

When tooling exists:
- compile succeeds;
- page size/orientation correct;
- font embedding acceptable;
- no missing figure references;
- effective image resolution acceptable;
- representative pages visually inspected;
- PDF/A validated if required.
