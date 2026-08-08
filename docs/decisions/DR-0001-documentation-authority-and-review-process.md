# DR-0001: Documentation authority and adversarial review process

ID: DR-0001

Scope: Governance

Status: Proposed

Revision: 3

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Response status: Pending

Date proposed: 2026-08-08

Date decided: —

Supersedes: —

Superseded by: —

## Context

Creature Kernel begins with consequential graphics, geometry, physics, and
runtime choices outside the project owner's established expertise. A previous
project introduced an architecture-only ADR mechanism and validation after a
large design corpus already existed, making reconstruction expensive and
ambiguous. That revision-1 proposal shape is retained here as history; it was
not an accepted predecessor.

The project needs explicit separation between different kinds of information:
product outcomes and externally observable requirements; normative
specifications and semantics; target architecture and invariants; decision
rationale; research questions and references; experiments and evidence;
developer workflows; project status and roadmap; and implementation, tests,
fixtures, benchmarks, and other proof. Each authority may link to the others,
but none may silently redefine another authority's contract.

The process must record consequential choices without turning ordinary wording,
derived detail, or reversible implementation into ceremony. It must also give
the decision owner a reviewable bundle and enough time for fresh adversarial
challenge before a proposal becomes accepted project policy.

## Decision

Adopt one neutral Decision Record (DR) system in `docs/decisions/` for
consequential choices. A DR may have one scope or a cross-cutting combination
of these scopes: Governance, Product, Specification, and Architecture. Its
`Scope:` metadata and registry field identify the canonical authorities affected;
the DR explains rationale and links to those authorities but does not replace
them.

### Provisional bootstrap trial

Ben's 2026-08-08 governance-round direction authorizes this mechanism as a
provisional operational trial until DR-0001 receives a disposition. Contributor
instructions and validators may bind work during the trial solely to preserve
authority separation, proposal labels, review evidence, repository safety, and
explicit human ownership. Trial operation is not acceptance of DR-0001 or
DR-0002–0004 and cannot accept any DR automatically. If Ben rejects or
materially replaces DR-0001, the main thread must retire or migrate trial-only
controls while preserving the proposal and review history. Documents must
clearly distinguish an active/operational structure from an accepted contract.

Require a DR only for a choice that is hard to reverse, cross-cutting,
contractual or public, performance-defining, dependency/portability/licensing
locking, or likely to be disputed. Ordinary wording, derived detail, and
reversible implementation do not require a DR unless they later cross one of
those thresholds.

Use round-delayed adversarial acceptance:

1. The main thread finishes a discussion batch of roughly two to five related
   decisions or talking points.
2. It integrates the canonical document changes and Proposed DR revisions for
   that batch, then validates the integrated result.
3. During the next round, a fresh reviewer rereads the exact current revision,
   the affected canonical documents, and the relevant research or experiment
   evidence as one canonical review bundle, while independent research for the
   next batch starts concurrently when dependencies permit.
4. The main thread records responses and revisions, then obtains explicit Ben
   acceptance only after the current revision has been reviewed. It returns a
   short synthesized review status together with the next decision batch.

Every `Complete` review artifact identifies the exact target revision, the exact
canonical review bundle, and the sources actually read. Before acceptance, the
DR links a matching current-revision review and contains a structured,
non-placeholder objection response with `Response status: Complete`. Mechanical
checks prove presence and identity only; Ben and the main thread judge
completeness, truthful reading, reviewer competence, and response adequacy.

A current-revision adversarial review is mandatory under this proposal and
cannot be replaced by `Review status: Waived`. Explicit Ben waivers or
deferrals may apply only to non-review proof or evidence obligations; they must
record the waiver reason and accepted risk.

The main `gpt-5.6-sol` thread owns human discussion, decomposition, synthesis,
integration, validation, Git and pull-request operations, CI and review
orchestration, external side effects, and final repository recommendations. It
does not delegate product or architecture decisions. `gpt-5.6-luna` is the
preferred route for non-trivial document edits, evidence gathering, mechanical
work, and bounded technical audits. Fresh `gpt-5.6-sol` at medium is the
default for foundational adversarial review. Luna at xhigh remains suitable for
narrow convergence or implementation review. Sol above medium requires Ben's
explicit approval, and Luna max remains subject to its separate admission gate.

Material that has not received explicit Ben acceptance remains clearly labelled
`Proposed` or `provisional`; assistant-synthesized product and architecture
content must not be described as an accepted active baseline.

## Consequences

- Product, specification, architecture, rationale, evidence, workflow, status,
  and implementation authorities remain inspectable and separately maintainable.
- A neutral DR can capture governance, product, specification, architecture,
  or cross-cutting choices without implying that every consequential choice is
  architectural.
- The high trigger threshold keeps routine editing and reversible implementation
  lightweight while preserving a durable record for disputed or locking choices.
- Review is intentionally delayed to the following round, allowing a coherent
  canonical bundle and fresh context rather than isolated review of chat turns.
- Proposals may remain active and useful before acceptance, but their provisional
  status must be visible to contributors and tooling.
- The bootstrap trial permits operational safety controls before acceptance while
  preserving an explicit rollback and migration boundary.
- Review artifacts must make their bundle, sources, current revision, and
  objection responses inspectable before acceptance.
- The main thread carries integration and validation responsibility, while
  bounded delegation preserves context and independent challenge.
- Governance introduces review and registry maintenance before implementation,
  and the process must be revisited if that cost outweighs the evidence it
  preserves.

## Alternatives Considered

### Informal Markdown and chat only

Lowest immediate effort, but authority boundaries, rationale, objections, and
decision state become difficult to recover or validate. It also makes a
round-delayed review bundle hard to identify.

### Full mature-project governance immediately

Would add machine-validated provenance, complete capability allocation, and
reconciliation machinery. It provides strong controls but is disproportionate
before implementation exists and would increase the cost of ordinary work.

### Separate architecture-only ADR mechanism

The revision-1 architecture-only proposal shape kept useful rationale and
review discipline, but it classified governance, product, and cross-cutting
choices too narrowly. Replacing it with neutral DRs preserves the useful
controls while making scope explicit. This is a proposed revision, not a claim
that the earlier mechanism was accepted.

### Immediate review and acceptance within one discussion batch

Would reduce latency, but the authoring context and canonical documents would
often be reviewed before the batch had settled. The next-round review creates a
clear fresh-context boundary at the cost of deliberate delay.

## Adversarial Review Response

[Fresh adversarial review of DR-0001 Revision 2](reviews/DR-0001-rev-02-review-01.md)
completed on 2026-08-08 recommended `Revise` with high confidence. Its two
blockers map to the Revision 3 changes below. Response status remains `Pending`
because Revision 3 has not received an independent review.

### Objection response 1

Objection: The provisional-status/bootstrap distinction was not explicit while
operational documents already bound unaccepted governance or DR-0002–0004
substance.

Response: Revision 3 adds the Provisional bootstrap trial rule above and aligns
the root guidance, authority indexes, workflow, registry, ledger, status, and
proposal labels with an operational trial that is not acceptance. The main
thread must retire or migrate trial-only controls if Ben rejects or materially
replaces DR-0001.

Disposition: Deferred

### Objection response 2

Objection: The exact canonical review bundle, sources actually read, and
structured objection responses were not required by the review template or
mechanically checked for presence and identity.

Response: Revision 3 adds required bundle and sources sections, a repeatable
structured objection-response format, and the review-evidence rule. The
validator changes are maintained separately; their independent verification is
still pending and is not claimed here.

Disposition: Deferred

Revision 3 must receive a fresh review of its exact revision and affected
canonical documents before Ben gives any disposition. DR-0001 remains Proposed,
and no text here claims independent verification, an accepted predecessor, or
acceptance of this revision.

## Implementation and Proof Obligations

- Maintain the authority index, neutral DR registry, templates, review records,
  and status vocabulary.
- Validate required documents, DR metadata and `Scope`, registry parity,
  headings, local links, UTF-8, whitespace, owner approval, response status,
  review bundle/source identity, and current-revision review links. Ben and the
  main thread judge non-review waiver reasons and accepted risk.
- Keep DR-0001 through DR-0004 visibly Proposed until their current revisions
  receive the round-delayed review and Ben's explicit disposition.
- Record each review's exact proposal revision and canonical review bundle.
- Review whether batch size, model routing, and the high trigger threshold are
  producing useful challenge without unnecessary process overhead after several
  rounds.

## Canonical Design Links

- [Documentation authority and navigation](../README.md)
- [Decision record process](README.md)
- [Repository evolution](../project/repository-evolution.md)
- [Contributor instructions](../../AGENTS.md)
- [AI delegation and review workflow](../developer-workflows/ai-delegation-and-review.md)

## Reversibility and Revisit Triggers

The process is documentation and tooling, so it is reversible. Revisit if DR
overhead delays ordinary work, reviewers cannot distinguish canonical owners,
the review bundle is too broad or too narrow to challenge a proposal, model
routing no longer fits the available expertise, validation becomes costly, or
important choices still bypass review. Any material governance change receives
a new DR revision and the next-round review rule applies again.
