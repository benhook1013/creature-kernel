# DR-0005: Initial product boundary and reference workflow

ID: DR-0005

Scope: Product and architecture

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Supersedes: —

Superseded by: —

## Context

Round 2 needs a bounded product identity before later source, runtime, proof,
and implementation questions are discussed. The project has several plausible
audiences and outcomes, but recording all of them as one settled technical
contract would silently decide questions assigned to later records.

## Decision

This Proposed record owns four initial product-boundary and reference-workflow
choices:

1. Creature Kernel is an engine-independent procedural creature compiler and
   embodiment runtime, not initially a game, editor, or general-purpose engine.
   A real-time game is the first downstream proof and integration target.
2. The earliest workflow serves the project developer or researcher using
   structured source, CLI/API operations, diagnostics, and reproducible
   evidence. Technical artists and game developers are important downstream
   review and integration users, not excluded users.
3. Stylized anthropomorphic creatures are the initial domain, with the first
   bounded family represented by upright digitigrade animal-like bipeds.
   Demanding close-contact interactions are motivating use cases and difficult
   contact/deformation stress cases; reusable body, contact, and solver
   mechanisms remain general rather than hard-coded to one interaction
   category.
4. Native programmatic generation without a handcrafted base mesh is the first
   reference path. External authored-mesh conformance is later, and early
   contracts must not foreclose that path.

This record does not settle DR-0002's detailed source and semantic decisions,
DR-0003's compile/runtime mutation boundary, DR-0004's automation contract
detail, first-proof morphology, geometry backend, or performance budgets.
Those remain Proposed or provisional questions for later batches.

## Consequences

- Canonical product documents can describe a coherent initial identity without
  making Creature Kernel a general-purpose engine.
- The developer/researcher workflow is the first reference path, while
  downstream artist and game-developer integration remains in scope.
- Demanding close-contact interactions motivate difficult contact and
  deformation cases without narrowing reusable mechanisms to one interaction
  category.
- Native generation is the first proof path while external-mesh conformance
  remains a later compatibility path.
- Detailed source, runtime, automation, morphology, backend, and budget choices
  remain open and must not be inferred from this record.

## Alternatives Considered

### Start as a game, editor, or general-purpose engine

This could provide a familiar product surface, but would commit the project to
host-engine and creator-tool scope before the compiler and embodiment premise is
proved.

### Treat all possible users as the first workflow

This would sound inclusive but would make the first evidence path too broad.
The developer/researcher is the earliest workflow; technical artists and game
developers remain important downstream users.

### Start with external authored meshes

This could improve immediate artist integration, but would make conformance and
mapping the first proof instead of native procedural generation. The later path
must remain open without making it the initial reference path.

### Restrict the architecture to close-contact interaction mechanics

Demanding close-contact interactions are important motivating stress cases, but
a hard-coded mechanical scope would prevent the reusable body, contact, and
solver contracts from serving other embodiment cases.

## Adversarial Review Response

The current [Revision 1 review](reviews/DR-0005-rev-01-review-01.md)
recommends `Accept` with medium confidence and found no blockers. It leaves
five non-blocking risks visible or deferred: speculative engine-independent or
external-mesh abstraction, untested artist/integrator usability, unproved
generalization from close-contact stress cases, DR-0005's upstream constraint
on later DR-0002/DR-0004 detail, and misleading README review wording. The wording
defect is corrected mechanically in the root README. Revision 1 remains
Proposed with owner approval pending; this response records the review
evidence and recommendation and does not claim that Ben accepted any risk or
the DR.

## Implementation and Proof Obligations

- Keep the four choices visible and Proposed in the product and architecture
  indexes and status reporting.
- Use the developer/researcher workflow and native generated creature path as
  the first reference for evidence planning, without selecting a language,
  backend, schema, runtime engine, or numerical budget here.
- Preserve an explicit later path for external authored-mesh conformance.
- Defer source semantics, compile/runtime mutation, automation detail, proof
  morphology, backend, and budget obligations to their later decisions and
  experiments.

## Canonical Design Links

- [Product documentation](../product/README.md)
- [Vision and scope](../product/vision-and-scope.md)
- [Product requirements](../product/requirements.md)
- [Users and workflows](../product/users-and-workflows.md)
- [Architecture documentation](../architecture/README.md)
- [System overview](../architecture/system-overview.md)
- [DR-0002](DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0003](DR-0003-real-time-first-compiled-avatar-boundary.md)
- [DR-0004](DR-0004-external-automation-through-cli-and-api.md)

## Reversibility and Revisit Triggers

Revisit if initial evidence shows that the compiler/runtime boundary, earliest
workflow, motivating domain, or native reference path prevents useful proof or
downstream integration. Revisit before committing to a general-purpose engine,
a close-contact-only mechanism, or a closed external-mesh contract.
