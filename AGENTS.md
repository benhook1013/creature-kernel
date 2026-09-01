# Creature Kernel contributor instructions

## Purpose

Creature Kernel is a research-heavy procedural creature compiler and embodiment
runtime. Keep product intent, specifications, architecture, decisions,
research, experiments, implementation status, and evidence distinct. One kind
of information never silently redefines another.

## Governance status

Governance operates under Accepted DR-0001 Revision 5; DR-0001 Revision 6 is
Proposed transition guidance and formal acceptance remains pending. This file
preserves authority separation and routing; it accepts no product,
specification, or architecture proposal.

## Authority

- `docs/product/` owns desired outcomes, scope, users, and observable
  requirements.
- `spec/` owns normative formats, semantics, identifiers, versioning, and
  compatibility.
- `docs/architecture/` owns target boundaries, data flow, invariants, and
  responsibilities.
- `docs/decisions/` owns consequential decision rationale and records which
  canonical documents a decision affects; a decision record does not replace
  those documents.
- `docs/research/` owns open questions, hypotheses, and research context; it
  does not define the accepted target state.
- `experiments/` owns reproducible evidence, results, and limitations; an
  experiment does not become a product or architecture contract automatically.
- `docs/developer-workflows/` owns conditional contributor and review
  procedures; it does not define product behaviour or technical contracts.
- `docs/project/` owns roadmap, current status, handover, and repository
  evolution; it does not redefine product or technical contracts.
- Code, tests, fixtures, benchmarks, and runtime outputs own evidence of what
  is implemented or demonstrated; they do not supply missing intent.

When sources appear to define one contract differently, stop and resolve the
conflict in the canonical owner. Secondary material links to that owner and
describes only its local consequence.

## Reading and active runway

For ordinary work, begin with [docs/README.md](docs/README.md) and the
[Active runway](docs/project/status.md#active-runway) only. Then read the
task-relevant canonical material: product documents for outcomes, `spec/` for
contracts, architecture documents for boundaries, a decision record for a
consequential choice, research or experiment records for evidence, and the
relevant workflow for an operational procedure.

The named human checkpoint in Active runway governs autonomous work. Advance
direct prerequisites as far as useful within the recorded scope, but never
substitute an internal experiment, evidence result, governance gate, or
infrastructure milestone for that checkpoint. If progress requires reactivating
a parked workstream, materially expanding scope, or resolving a retained-human
decision, stop and ask Ben.

The current handover is a live-check pointer for continuation, not an authority
over Active runway. Use it when resuming from another session, worktree, or
stale state, then verify the current canonical status.

## Human and thread authority

Ben retains decisions about:

- product purpose and scope;
- user-visible experience and quality targets;
- supported morphology or runtime promises;
- material platform or engine lock-in;
- licensing, cost, privacy, and external impact;
- large or otherwise irreversible trade-offs; and
- acceptance or rejection of product and direction-setting decision records.

The main Sol thread owns planning, task decomposition, synthesis, integration,
consolidated validation, Git and pull-request operations, review orchestration,
external effects, and final repository judgment. It escalates whenever work
would change a retained human boundary.

Routine, reversible technical implementation may proceed autonomously within a
recorded runway. This includes implementation details, defect resolution,
build integrity, code and test organization, diagnostics, status plumbing,
deterministic or numeric algorithms, and reversible dependencies or tools when
they remain inside canonical boundaries. The reasoning for a consequential
technical choice remains durable in its owner document.

Subagents are bounded executors, investigators, or reviewers. They may collect
evidence, implement settled technical work, and challenge proposals, but they
never decide product or architecture direction. They do not spawn descendants
unless the main thread explicitly authorizes a narrowly bounded exception. The
main thread inspects, integrates, and disposes of delegated work; the detailed
workflow defines the exception and routing response.

## Runway and merge control

Autonomous merge authority exists only inside a recorded Active runway and
after all applicable checks, reviews, evidence, and repository gates pass. Stop
before the first actual human-visible checkpoint, a user-visible CLI/viewer/API
checkpoint explicitly named for Ben's appraisal, or a retained-human boundary,
and present that candidate with the judgment Ben is being asked to make. That
candidate must not be merged autonomously; it requires Ben's explicit, recorded
authorization. An instruction for one PR is not standing authority for later
PRs.

Changes to agent authority, workflow routing, merge authority, retained-human
boundaries, or the governing runway scope are presented to Ben and require his
explicit, recorded authorization before merge. They are outside routine
autonomous implementation and auto-merge authority even when they do not
change product behaviour.

## Decision records

Use a DR when a choice is hard to reverse, cross-cutting, contractual or
public, performance-defining, dependency/portability/licensing-locking, or
likely to be disputed. Ordinary wording, derived detail, and reversible
implementation normally remain outside the DR process.

Keep decision scope and status explicit. Unaccepted material is labelled
`Candidate`, `Proposed`, `Under Review`, or `provisional` as appropriate;
`Accepted`, `Rejected`, `Superseded`, and `Withdrawn` describe recorded states.
A plausible assistant synthesis is not an accepted contract.

Classify findings lightly: correctness needed now; retained-human direction or
material trade-off; implementation- or evidence-dependent; or speculative
hardening without a present need. Fix the first within authority, escalate the
second, record the trigger and defer the third, and do not build the fourth.
Detailed DR creation, scope, revision, review, waiver, and acceptance procedure
belongs to [the decision-record process](docs/decisions/README.md).

## Evidence and research

- Label hypotheses, expectations, measurements, decisions, and implementation
  evidence separately.
- Support performance claims with a reproducible benchmark and hardware or
  environment profile.
- Support visual or geometric claims with fixtures, captures, or metrics, or
  state clearly that the judgment remains subjective.
- Treat human visual feedback as scoped to the exact artifact, fixture,
  generator or renderer, and revision shown. Re-baseline it when the
  representation or consumer materially changes unless Ben promotes the
  underlying outcome into product intent.
- Record failed and inconclusive experiments, their limitations, provenance,
  and reproduction commands. Evidence informs decisions but does not accept a
  contract automatically.
- Name the authoritative source and regeneration command for generated
  references.

## Repository safety

Preserve unrelated user changes. Keep edits and staged paths limited to the
task, and keep future components in their documented evolution record until
their activation trigger is met. Do not commit large generated meshes, caches,
captures, videos, or datasets without an accepted artifact-storage decision.

Use a reviewed file for a GitHub pull-request body, then read the PR back and
verify its title, body, head, base, and state. Keep destructive cleanup bounded
to exact, verified targets; never use broad recursive cleanup for convenience.
Keep external side effects under the main thread's ownership and the applicable
workflow.

## Conditional workflow routing

Read the named owner before taking the corresponding action:

1. When delegating work, selecting a model, requesting model-backed review,
   planning or running a hands-on feature trial, or changing the AI control
   plane, read [AI delegation and review](docs/developer-workflows/ai-delegation-and-review.md).
2. When creating, updating, pushing, or presenting any PR; requesting or
   performing external review; merging; enabling auto-merge; or considering an
   administrative bypass, read the same [AI delegation and review workflow](docs/developer-workflows/ai-delegation-and-review.md).
   It owns delegation, model routing, PR operations, external review, merge,
   auto-merge, and bypass controls.
3. When deciding whether a DR is required or taking any DR action, read
   [the decision-record process](docs/decisions/README.md).
4. For browser navigation, inspection, screenshots, recordings, gallery work,
   or visual appraisal, read [the visual-review gallery workflow](docs/developer-workflows/visual-review-gallery.md)
   and its linked tool documentation.
5. For any command, test, artifact, or interpretation under `experiments/`,
   read [the experiments workflow](experiments/README.md), the relevant
   experiment README, and use the required launcher named there.
6. When operational friction is unexpected and recurring or likely reusable,
   subagents return a concise `AI observation candidate`. The main thread
   searches the inbox narrowly, deduplicates it, and writes a durable record
   only for an evidenced recurring or reusable pattern. A maintenance round
   consumes, resolves, promotes, or retains inbox entries.
7. When resuming from another session, worktree, or stale state, read
   [current-handover](docs/project/current-handover.md) as a live-check pointer;
   it never overrides the Active runway or a canonical authority.

## Validation and reporting

Report every requested check honestly as passed, failed, unavailable, or not
applicable. Never describe an unrun check as passing. Before committing
documentation or decision-record changes, run:

```bash
python3 dev-tools/validation/validate_docs.py
dev-tools/validation/check_worktree_whitespace.sh
```
