# Research-Grade Visual System

## Goal

Academic technical visuals should look calm, intentional, and reproducible. Their job is to compress technical meaning, not advertise the project.

## Typography

- Match the thesis font family when practical, or use a compatible neutral font.
- Keep element names visually stronger than descriptions/metadata.
- Use monospace selectively for code identifiers, table names, API paths, environment variables.
- Effective text after insertion should normally be around 9–10 pt for publication-style figures; do not shrink below the university/template minimum. If readability requires <8–9 pt, redesign the figure.
- Maintain consistent text sizes across all figures of the same class.

## Lines and shapes

- Use a small set of shape meanings and keep them stable across the thesis.
- Use medium line weights that survive common laser/office printing.
- Avoid hairline borders.
- Use orthogonal routing for architecture/data diagrams when it improves traceability.
- Minimize crossings; crossings are a layout defect when avoidable.
- Use dashed borders/lines only if they encode a documented meaning.

## Color

- Default to grayscale plus one restrained accent family.
- Color must be redundant with text, shape, marker, or line style.
- Avoid red/green-only distinctions.
- Verify grayscale where possible.
- Avoid low-contrast pastel-on-white labels.

## Composition

- Prefer left-to-right for time/data flow unless domain conventions suggest otherwise.
- Prefer top-to-bottom for hierarchy/decomposition.
- Align elements to a visible grid.
- Keep whitespace between groups larger than whitespace within groups.
- Make boundaries meaningful; do not box everything.
- Keep legends compact and close to the figure.

## Density

Split rather than shrink when:

- labels collide or connectors become hard to trace;
- more than one abstraction level is mixed;
- one figure needs several unrelated legends;
- the key text falls below readable size;
- a full physical ERD becomes a wall of columns;
- a sequence diagram spans too many independent scenarios.

Use overview + detail views rather than one giant figure.

## Captions

Captions should identify:

1. what the figure is;
2. scope/context;
3. one important constraint/takeaway only when necessary.

Do not move entire explanatory paragraphs into the figure itself.
