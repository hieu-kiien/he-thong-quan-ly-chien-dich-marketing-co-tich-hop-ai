# Tool Selection

Choose tools by semantic fidelity, editability, reproducibility, and print quality.

## TikZ / PGF

Best when:
- figure complexity is moderate;
- typography should match LaTeX;
- source-controlled reproducibility matters;
- custom layout is manageable.

Avoid forcing TikZ for enormous graph-layout problems that Graphviz/PlantUML handles more reliably.

## PGFPlots

Best for thesis-native scientific plots with manageable datasets and compile cost.

For very large datasets, pre-process with Python/R and export vector PDF or data tables for PGFPlots.

## PlantUML

Best for:
- sequence;
- state;
- class;
- component/deployment;
- use case;
- C4 through compatible libraries when the environment supports it.

Keep `.puml` source and export vector PDF/SVG.

## Graphviz

Best for:
- dependency graphs;
- hierarchies;
- automatic layout;
- medium/large node-link structures.

Use DOT attributes deliberately; do not accept default layout if it harms print readability.

## Mermaid

Best for portable, Markdown-friendly diagrams with adequate notation support. Prefer it when interoperability matters more than formal UML fidelity.

## DBML / schema-driven ERD tools

Useful for physical/logical ERD source that tracks database definitions. Verify optionality and constraints against actual DDL/migrations.

## diagrams.net / draw.io

Best when manual routing and mixed icon/box layouts matter. Keep the `.drawio` file; export PDF/SVG for LaTeX.

## Figma/FigJam

Useful for UI flow/wireframes and carefully composed diagrams. Keep editable source and export vector. Do not use Figma styling to turn academic architecture into marketing artwork.

## Visual Paradigm / Visio

Useful for formal enterprise/UML/BPMN/network deliverables when available. Export vector and retain native source.

## Python / R plotting

Best for data analysis and complex scientific charts. Export PDF/SVG whenever the chart remains vector-friendly. Keep data and plot script together for reproducibility.
