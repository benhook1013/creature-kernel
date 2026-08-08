# DR-0004: External automation through CLI and API

ID: DR-0004

Scope: Product and architecture

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Response status: Pending

Date proposed: 2026-08-05

Date decided: —

Supersedes: —

Superseded by: —

## Context

External AI assistance is expected, but the project owner does not intend to
make a built-in chat assistant the primary interface. Humans, scripts, automated
tests, and outside agents all need precise access to the same operations.

GUI computer use is fragile for deterministic creation and validation. A direct
tool surface can expose semantics, transactions, diagnostics, and artifacts.

## Decision

Make a documented CLI and programmatic API first-class interfaces to the same
deterministic core. The platform must remain fully usable without an embedded AI
model. External agents may discover capabilities, edit source, compile, validate,
render previews, inspect structured diagnostics, and present diffs for human
acceptance.

Semantic local coordinates and stable identifiers are preferred over raw global
coordinates and generated mesh indices, while low-level exact operations remain
available when necessary.

## Consequences

- Automation is not coupled to one AI provider or interface.
- Headless tests and reproducible workflows become natural requirements.
- CLI/API compatibility and error schemas become product surfaces.
- A GUI must call shared operations rather than accumulate private behaviour.
- Designing useful introspection and transactions adds early engineering work.

## Alternatives Considered

### Embedded AI-first interface

May be approachable for casual use but couples core workflows to model behaviour,
accounts, prompts, and provider integration.

### GUI-first with computer-use automation

Avoids API design initially but is brittle, difficult to validate, and inefficient
for precise iterative generation.

### Library API only

Supports integration but makes shell automation, external tools, and independent
validation less accessible.

## Adversarial Review Response

Pending review of revision 1.

## Implementation and Proof Obligations

- Define introspection, stable IDs, transactions, diagnostics, and exit behaviour.
- Keep GUI and CLI operations on a shared core.
- Provide machine-readable validation and artifact manifests.
- Establish compatibility/versioning rules before third-party automation is promised.
- Demonstrate an end-to-end headless character-edit and validation loop.

## Canonical Design Links

- [Product requirements](../product/requirements.md)
- [Users and workflows](../product/users-and-workflows.md)
- [System overview](../architecture/system-overview.md)

## Reversibility and Revisit Triggers

The project may later add an embedded assistant without changing this boundary.
Revisit if CLI/API maintenance prevents rapid research, if a GUI requires
irreducibly interactive operations, or if external-agent protocols require a
different abstraction.
