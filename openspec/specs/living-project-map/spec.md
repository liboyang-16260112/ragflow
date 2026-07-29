# Living Project Map

## Purpose

Provide a repository-owned living map that connects RAGFlow product capabilities, external APIs, runtime architecture, source code ownership, and verification tests into one navigable entry point. The map is the shared navigation layer — it does not replace the detailed HTTP reference, Python SDK reference, or developer guides.

**TBD**: Additional capabilities beyond the initial six (datasets, documents and ingestion, chunks and retrieval, chats and sessions, agents, files) will be documented as they are added.

## Requirements

### Requirement: Simplified Chinese documentation
The living-map deliverables SHALL use Simplified Chinese as their canonical authoring language for reader-facing titles, navigation, explanations, diagrams, examples, contribution guidance, and generated document labels. Code identifiers, file paths, commands, HTTP methods, endpoint paths, configuration keys, protocol names, and payload field names SHALL remain verbatim where translation would reduce technical accuracy.

#### Scenario: Reader opens a human-authored map page
- **WHEN** a reader opens the landing page, integration guidance, architecture view, capability page, golden path, or contribution guide delivered by this change
- **THEN** its reader-facing narrative and navigation are written in Simplified Chinese

#### Scenario: Reader opens a generated map view
- **WHEN** a reader opens a generated API inventory or runtime parity document
- **THEN** its headings, table labels, classifications, and explanatory text are written in Simplified Chinese while technical identifiers remain unchanged

#### Scenario: Implementation is reviewed for completion
- **WHEN** the living-map implementation is accepted as complete
- **THEN** automated or review-based validation finds no unexplained English reader-facing prose in the new living-map deliverables

### Requirement: Role-oriented map entry point
The documentation SHALL provide one repository-owned living-map entry point that offers distinct navigation paths for external API integrators and for readers who want to understand or modify RAGFlow.

#### Scenario: External integrator enters the map
- **WHEN** a reader chooses the integration path
- **THEN** the map presents authentication guidance, API selection guidance, golden integration paths, and public capability links before internal implementation detail

#### Scenario: Contributor enters the map
- **WHEN** a reader chooses the project-understanding path
- **THEN** the map presents runtime topology, domain boundaries, major data flows, source ownership, and extension points

### Requirement: Capability-centered navigation
The living map SHALL organize shared content around named product capabilities rather than around repository directories alone.

#### Scenario: Reader opens a capability
- **WHEN** a reader opens an initial capability page
- **THEN** the page states the capability purpose and boundary and links to its supported contracts, principal runtime flow, owning source, dependencies, and focused tests

#### Scenario: Capability has runtime-specific support
- **WHEN** a capability is implemented or supported by only one selectable API runtime
- **THEN** its page identifies that runtime explicitly and does not imply cross-runtime parity

### Requirement: Initial capability coverage
The first living-map release SHALL cover datasets, documents and ingestion, chunks and retrieval, chats and sessions, agents, and files.

#### Scenario: Reader surveys the initial map
- **WHEN** the initial living-map index is rendered
- **THEN** all six initial capabilities are reachable from the index without using repository search

### Requirement: Golden integration paths
The living map SHALL provide end-to-end golden paths for document ingestion and retrieval, chat-session conversation, and agent-session execution.

#### Scenario: Reader follows a golden path
- **WHEN** a reader follows one of the three initial golden paths
- **THEN** the path identifies prerequisites, ordered public operations, asynchronous or streaming behavior, expected result checkpoints, and links to detailed contracts

#### Scenario: Golden path crosses internal components
- **WHEN** a golden path explains how a request is fulfilled
- **THEN** it distinguishes public calls made by the integrating project from internal services and workers operated by RAGFlow

### Requirement: Current runtime topology
The project-understanding path SHALL document the selectable Python and Go API servers, background execution components, shared backing services, and the configuration that selects the active API runtime.

#### Scenario: Reader investigates service startup
- **WHEN** a reader opens the runtime topology view
- **THEN** the view identifies the default API server, the Go selection condition, and the separate ingestion or task-execution processes without presenting both API servers as simultaneously authoritative

### Requirement: Stable traceability links
Living-map pages SHALL link capability descriptions to stable source files or directories, public reference anchors, SDK surfaces where supported, and focused verification tests.

#### Scenario: Source moves or a link breaks
- **WHEN** a referenced repository target or documentation anchor no longer exists
- **THEN** automated validation fails with the originating map entry and missing target

### Requirement: Avoid duplicated contract detail
The living map SHALL treat the existing HTTP and Python API references as the canonical home for detailed parameter and response documentation.

#### Scenario: Capability documents a public endpoint
- **WHEN** a capability page mentions a public endpoint
- **THEN** it links to the canonical detailed reference and limits local content to navigation, context, or an end-to-end journey example

### Requirement: Standard extension template
The living map SHALL provide a repeatable capability-page template and contribution guidance for adding or updating capabilities.

#### Scenario: Maintainer adds a capability
- **WHEN** a maintainer follows the living-map contribution guidance
- **THEN** the resulting page includes required capability metadata, reader-facing context, implementation traceability, and validation evidence in the established structure
