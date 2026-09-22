# Notation Rules

## C4 / software architecture

Use C4 semantics rather than generic boxes-and-arrows when labeling a diagram as C4.

- Every diagram has a type and scope.
- Every element has name + type + short responsibility.
- Containers/components state technology where known.
- Relationships are one-directional, labeled with intent, and consistent with arrow direction.
- Container-to-container communication states protocol/technology when known.
- Use a legend if shape/color/border/line style encodes meaning.
- Keep Context, Container, Component, and Deployment views separate unless a deliberate mapping is the subject.
- Distinguish external systems from internal systems visually.
- Distinguish implemented vs proposed when relevant.

## UML Use Case

- Actors are roles, not individual people.
- Use cases are goals, usually verb phrases.
- System boundary should be explicit for nontrivial diagrams.
- Do not add `include`/`extend` merely to reduce line count.
- Keep workflow chronology out of use-case diagrams.

## UML Sequence

- Participants have stable semantic names.
- Messages are ordered and directional.
- Use return messages selectively; avoid clutter.
- Use activation bars when they clarify responsibility.
- Use `alt` for mutually exclusive branches, `opt` for optional behavior, `loop` for repetition/retry.
- Include failure branches when the thesis claims robust error handling.
- Human-in-the-loop approval must be shown when it is a system guarantee.
- Do not infer hidden internal calls without evidence.

## UML State Machine

- States are durable/meaningful states, not arbitrary function names.
- Transitions state trigger/event; add guards where needed.
- Validate legal transitions against code and database CHECK constraints.
- Show initial and terminal states where appropriate.
- If persistence has a status enum, the state diagram should reconcile with it.

## UML Class

- Show only attributes/operations needed for the design discussion.
- Use association, aggregation, composition, dependency, inheritance deliberately.
- Show multiplicities where they matter.
- Do not auto-export the entire codebase into an unreadable diagram.

## ERD

Declare the level in the title/caption:

- **Conceptual ERD**: business entities and relationships, minimal implementation detail.
- **Logical ERD**: attributes/keys/cardinalities, DBMS-neutral where possible.
- **Physical schema diagram**: table/column names, DBMS types, indexes/constraints where useful.

Rules:

- Use DDL/migrations/ORM as evidence if available.
- PK/FK must match source.
- Nullability affects optionality.
- UNIQUE constraints may change relationship semantics.
- Show `0..1`, `1`, `0..*`, `1..*` or consistent Crow's Foot.
- Avoid crossing connectors; split large schemas by bounded context/domain.
- Do not omit associative tables just to make the picture prettier when they are semantically important.

## BPMN

- Sequence flow is used within a process/pool.
- Message flow is used between pools/participants where appropriate.
- Lanes represent responsibility.
- Exclusive/parallel/event-based gateways must reflect actual semantics.
- Start/end events should be meaningful.
- Do not mix UML Activity symbols into a BPMN diagram without an explicit reason.

## DFD

- External entity, process, data store, and data flow symbols remain consistent.
- Data flows are nouns/data, not control commands.
- Level decomposition should be balanced: parent inputs/outputs remain represented in child levels unless there is a documented refinement.

## Deployment / network / cloud

- Separate logical architecture from runtime/physical deployment.
- Show node/container mapping explicitly.
- Only include region, VPC/VNet, subnet, port, protocol, TLS, firewall, load balancer, instance size, etc. when supported by source/config or clearly marked proposed.
- Use official cloud icons when available; otherwise neutral labeled shapes are preferable to inaccurate icons.
