# Diagram Routing Guide

Choose the visual from the question, not from habit.

| Reader question | Preferred visual | Common misuse to avoid |
|---|---|---|
| Who uses the system and what external systems interact with it? | C4 System Context | Showing database tables or internal classes here |
| What deployable/runtime applications and datastores make up the solution? | C4 Container | Calling framework layers “containers” without runtime meaning |
| How is one service/module structured internally? | Component/module view | Dumping every class in the codebase |
| What goals can an actor accomplish? | UML Use Case | Using use cases as chronological flow steps |
| What messages happen in time order? | UML Sequence | Omitting important failure/approval branches |
| What business/application steps and decisions occur? | UML Activity / flowchart | Mixing BPMN symbols randomly |
| Who is responsible for each process step? | BPMN / swimlane | Lanes as decorative columns |
| What legal lifecycle transitions exist? | UML State Machine | Drawing mere CRUD operations as states |
| What are OO types and their static relations? | UML Class | Treating database tables as OO classes without purpose |
| What is the relational schema? | ERD | Mixing conceptual entities with physical implementation details without labeling |
| How does information move and transform? | DFD | Using DFD arrows as arbitrary control flow |
| Where do runtime units execute? | Deployment diagram | Mixing logical containers and physical hosts without clear mapping |
| What is the network/trust topology? | Network diagram | Inventing subnets/ports/security controls |
| How are cloud services connected? | Cloud architecture | Decorative vendor icons with no relationship labels |
| How does an algorithm proceed? | Flowchart/pseudocode | Using a flowchart for architecture |
| What is the project timeline? | Gantt | Using Gantt for runtime workflow |
| What exact values/specifications must readers compare? | Native table | Turning exact values into a chart only |
| What trend/distribution/relationship is in the data? | Plot/chart | 3D effects, dual axes without necessity |

## Multi-view rule

Use multiple coordinated views when one figure would mix abstraction levels. Typical thesis set:

1. System Context
2. Container / high-level architecture
3. One or more component/detail views only where technically important
4. Deployment view if deployment is part of the contribution
5. ERD logical/physical views
6. Sequence/state views for critical workflows

Avoid creating every possible UML diagram. Each visual must earn its place by reducing cognitive load or proving a design claim.
