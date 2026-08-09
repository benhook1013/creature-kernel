# DR-0004: Shared deterministic domain operations for external automation

ID: DR-0004

Scope: Product and architecture

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Supersedes: —

Superseded by: —

## Context

External AI assistance is expected, but the project owner does not intend to
make a built-in chat assistant the primary interface. Humans, scripts, automated
tests, future GUI clients, and outside agents all need precise access to the same
operations. A private behaviour path in any one surface would undermine
determinism, validation, and reproducibility.

Revision 1 made CLI and programmatic API first-class. Revision 2 makes the
shared deterministic domain-operation model the decision and treats each user
surface as an adapter over it.

## Decision

Define one deterministic creature domain-operation model for query, semantic
mutation, resolution/compilation, validation, diagnostics, artifact inspection,
and future transaction semantics. The CLI, programmatic API, future GUI, tests,
scripts, and external AI agents are adapters over those shared operations; none
may gain private core behaviour. The first implementation may simply be an
in-process library plus a CLI adapter.

The platform must remain fully usable without an embedded AI dependency. External
agents may use the same operation model as other clients. Concrete interface
language, command names, wire/schema/transport, GUI interaction, undo details,
compatibility, authentication, and remote services remain separate decisions.

## Consequences

- Automation is not coupled to one AI provider or surface.
- Headless tests and reproducible workflows exercise the same core operations.
- Introspection, diagnostics, and artifact inspection become shared operation
  responsibilities.
- A GUI, test harness, script, or external agent must call shared operations
  rather than accumulate private behaviour.
- Concrete interface and transaction contracts remain later engineering work.

## Alternatives Considered

### Embedded AI-first interface

May be approachable for casual use but couples core workflows to model behaviour,
accounts, prompts, and provider integration.

### GUI-first with computer-use automation

Avoids API design initially but is brittle, difficult to validate, and inefficient
for precise iterative generation.

### Library API only

Supports integration but makes shell automation, external tools, and independent
validation less accessible. It remains a possible first in-process foundation,
but adapters still use the shared operation model.

## Adversarial Review Response

[Round 3 Revision 2 adversarial review](reviews/DR-0004-rev-02-review-01.md)
recommends Accept with Medium confidence and found no decision blocker or
revision requirement. It identified one mechanical system-overview diagram
ordering defect; that order was corrected mechanically with no decision change
or architecture-prose change. Interface, schema, transport, transaction,
compatibility, authentication, and service obligations remain deferred pending
owner disposition and later implementation work.

## Implementation and Proof Obligations

- Define the shared operation model and its deterministic boundaries.
- Keep CLI, API, GUI, tests, scripts, and external-agent adapters on that model.
- Provide machine-readable diagnostics and artifact inspection.
- Later define commands, schemas/transports, transaction and undo semantics,
  compatibility, authentication, and remote-service behaviour.
- Demonstrate an end-to-end headless semantic-edit and validation loop.

## Canonical Design Links

- [Product requirements](../product/requirements.md)
- [Users and workflows](../product/users-and-workflows.md)
- [System overview](../architecture/system-overview.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)

## Reversibility and Revisit Triggers

The project may later add an embedded assistant without changing this boundary.
Revisit if CLI/API maintenance prevents rapid research, if a GUI requires
irreducibly interactive operations, or if external-agent protocols require a
different abstraction.
