# API Surface Governance

## Purpose

Define the structured classification, generated inventory, Python/Go runtime comparison, and CI drift rules for RAGFlow API surfaces. This capability ensures that every governed `/api/v1` route has reviewed policy metadata, that public contracts carry required evidence, and that the generated documentation does not silently drift from the source.

**TBD**: Policy approval workflow and CODEOWNERS assignment for visibility/stability changes.

## Requirements

### Requirement: Source-derived route inventory
The repository SHALL generate normalized route facts from Python REST route declarations, Go router registrations, and registered compatibility aliases without starting either API server or connecting to runtime services.

#### Scenario: Inventory is generated in a clean development environment
- **WHEN** the inventory command runs with repository source available but without databases, Redis, search engines, or model providers
- **THEN** it produces route facts without importing or starting the API applications

#### Scenario: Extractor encounters unsupported dynamic registration
- **WHEN** a route registration cannot be resolved by the language-aware extractor
- **THEN** generation reports the source location and unsupported construct instead of silently omitting the route

### Requirement: Canonical route normalization
The inventory SHALL normalize equivalent Quart and Gin path-parameter syntax while preserving the original path and source location for each runtime registration.

#### Scenario: Python and Go declare equivalent parameterized paths
- **WHEN** one runtime uses Quart parameter syntax and another uses Gin parameter syntax for the same method and path structure
- **THEN** both registrations resolve to the same canonical route key and remain traceable to their original declarations

### Requirement: Explicit API policy classification
Every governed `/api/v1` route SHALL have reviewed policy metadata defining its capability, visibility, stability, and intended runtime support.

#### Scenario: New route lacks policy metadata
- **WHEN** source extraction discovers a governed route with no matching policy entry
- **THEN** validation fails and identifies the method, normalized path, runtime, and source location

#### Scenario: Route policy references nonexistent code
- **WHEN** policy metadata names a method and path that no extractor discovers
- **THEN** validation fails and identifies the stale policy entry

### Requirement: Public contract evidence
Every route classified as public SHALL link to a stable detailed HTTP reference anchor and a focused executable or contract-test location.

#### Scenario: Public route lacks documentation
- **WHEN** a public policy entry has no valid detailed HTTP reference anchor
- **THEN** validation fails for that entry

#### Scenario: Public route is exposed by the Python SDK
- **WHEN** a public capability is declared as supported by the Python SDK
- **THEN** its policy entry links to the corresponding SDK surface and validation confirms that source target exists

### Requirement: Visibility-aware publication
Generated external integration views SHALL include public routes by default and SHALL exclude beta, internal, and compatibility routes unless the reader explicitly opens a maintainer or lifecycle view.

#### Scenario: External integration inventory is generated
- **WHEN** the public API view is rendered
- **THEN** only entries classified as public appear in its default tables and navigation

#### Scenario: Maintainer inspects full inventory
- **WHEN** the maintainer inventory is rendered
- **THEN** public, beta, internal, and compatibility entries are visible with their classifications

### Requirement: Runtime parity reporting
The generated inventory SHALL report policy-aware support across the Python and Go API runtimes without treating all differences as defects.

#### Scenario: Public route is expected in both runtimes
- **WHEN** policy declares both runtimes but extraction finds the route in only one
- **THEN** validation fails and reports the missing runtime registration

#### Scenario: Route is intentionally runtime-specific
- **WHEN** policy declares a single intended runtime and extraction matches it
- **THEN** the parity view marks the difference as intentional and validation succeeds

### Requirement: Compatibility lifecycle reporting
Compatibility routes SHALL be excluded from the supported public surface and SHALL identify their canonical replacement when a replacement exists.

#### Scenario: Deprecated alias has a replacement
- **WHEN** a compatibility entry represents a deprecated alias with a canonical endpoint
- **THEN** the maintainer inventory displays the replacement and the public integration path directs readers to the canonical endpoint

#### Scenario: Inventory discovers compatibility code
- **WHEN** a compatibility route is extracted
- **THEN** the generator records existing behavior without creating, extending, or recommending the compatibility route

### Requirement: Deterministic generated artifacts
Generated inventory and parity documents SHALL use stable ordering and content so identical repository inputs produce byte-identical outputs.

#### Scenario: Generator runs twice without source changes
- **WHEN** generation is performed twice from identical inputs
- **THEN** the resulting tracked artifacts are byte-identical

### Requirement: Drift check mode
The repository SHALL provide a validation command that compares generated results with committed artifacts and validates classifications, runtime expectations, documentation anchors, SDK links, and source/test links.

#### Scenario: Pull request changes a governed route
- **WHEN** a route is added, removed, or changed without the corresponding policy and generated documentation updates
- **THEN** the validation command exits unsuccessfully with actionable drift details

#### Scenario: Repository is synchronized
- **WHEN** source routes, policy metadata, map links, and committed generated files agree
- **THEN** the validation command exits successfully without modifying the worktree
