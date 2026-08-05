# Creature Kernel contributor instructions

## Purpose

Creature Kernel is a research-heavy procedural creature compiler and embodiment
runtime. Treat product intent, specifications, architecture, decisions,
experiments, implementation status, and evidence as different kinds of
information. Do not allow one kind to silently redefine another.

## Required reading order

Before consequential design or implementation work, read:

1. `docs/README.md`
2. `docs/product/vision-and-scope.md`
3. `docs/product/requirements.md`
4. `docs/architecture/README.md`
5. `docs/project/status.md`
6. Any relevant specification, ADR, research question, or experiment record

`docs/FOUNDATION.md` is the historical founding record. It explains how the
project arrived here but is not the canonical owner of current contracts.

## Authority

- `docs/product/` owns desired outcomes and externally observable requirements.
- `spec/` owns normative formats, semantics, identifiers, and compatibility.
- `docs/architecture/` owns target technical boundaries and invariants.
- Accepted ADRs explain decisions but do not replace canonical product,
  specification, or architecture documents.
- `docs/research/` owns open questions and research context, not target contracts.
- `experiments/` records evidence. Results may inform decisions but do not become
  architecture automatically.
- `docs/developer-workflows/` owns conditional contributor procedures, not product
  or technical contracts.
- `docs/project/` reports plans and status without redefining target behaviour.
- Code, tests, fixtures, and benchmarks provide implementation evidence.

When documents conflict, stop and resolve the conflict in the canonical owner.

## Decisions and adversarial review

- Add consequential choices to the ADR registry before treating them as settled.
- Do not change an ADR to `Accepted` without an adversarial review of its current
  revision and explicit human approval from the decision owner.
- A material proposal change increments its revision and makes older reviews
  stale.
- Preserve rejected and superseded decisions so their reasoning is not lost.
- Record waivers explicitly; never imply missing evidence was supplied.
- Reviews must challenge assumptions, alternatives, failure modes, performance,
  reversibility, portability, licensing, and missing expertise where relevant.

## Research and proof

- Label hypotheses, expectations, measurements, and decisions distinctly.
- Performance claims require a reproducible benchmark and hardware profile.
- Visual or geometric claims require fixtures, captures, metrics, or an explicit
  statement that judgment remains subjective.
- Record failed and inconclusive experiments; they are useful evidence.
- Generated references must identify their source and regeneration command.

## Repository discipline

- Keep future components in `docs/project/repository-evolution.md` until their
  activation trigger is met. Do not create empty implementation packages.
- Use stable semantic identifiers rather than generated mesh indices in durable
  contracts.
- Do not commit large generated meshes, caches, captures, or datasets without an
  approved artifact-storage decision.
- Keep the engine-independent core separate from host-engine adapters once code
  boundaries exist.
- Preserve unrelated user changes and stage only files belonging to the task.

## Conditional workflows

- Subagent selection, delegation boundaries, model routing, and independent
  review use
  `docs/developer-workflows/ai-delegation-and-review.md`.
- An ADR review may use
  `docs/architecture/decisions/reviews/fresh-reread-preamble.md` to force a
  current-disk, issue-only convergence pass.

## Orchestration

The main `gpt-5.6-sol` thread owns planning, human design discussion, task
decomposition, integration, consolidated validation, Git and pull-request
operations, CI and review orchestration, external side effects, and final
repository decisions. It does not delegate product or architecture decisions.
Reviewers may challenge a proposal and recommend a disposition, but only the
human decision owner accepts or rejects an ADR.

- Use `gpt-5.6-luna` at `high` for routine bounded investigation, mechanical
  patches, straightforward test updates, and multi-step search or tool-driven
  investigation. Prefer this route when it preserves Sol context or lowers cost,
  even when the bounded task is not difficult.
- Use Luna at `xhigh` for substantial delegated work and independent review. This
  is the normal Luna ceiling.
- Luna at `max` is exceptional and requires a main-thread admission decision. Use
  it only for known-hard cross-file correctness work, an exhaustive bounded audit,
  or an `xhigh` failure that the main thread confirms was caused by insufficient
  depth rather than ambiguity or poor decomposition. The prompt must define the
  exact corpus, coverage requirement, deliverable, and stop condition. Luna must
  return incomplete evidence rather than expand scope, self-retry, or start a
  continuation loop. No separate human approval is required when these conditions
  are met.
- Use `gpt-5.6-sol` at `medium` when broad synthesis, ambiguous evidence, or
  general reasoning matters more than coding-agent throughput. It is a task-type
  escalation, not the automatic tier after Luna.
- Using Sol at `high` requires explicit human approval. Sol at `high` is the
  absolute subagent ceiling. Do not use Terra as a normal routing tier.
- Delegate only bounded work with a disjoint scope and explicit success
  conditions. The main thread remains responsible for evaluating the evidence.
- Parallel workers must have disjoint write scopes. The main thread inspects every
  returned diff, reconciles interactions, and validates the integrated result.
- Independent reviewers should normally be fresh-context agents that did not
  implement the material under review.

## Validation

Run before committing documentation or ADR changes:

```bash
python3 dev-tools/validation/validate_docs.py
git diff --check
```

Report checks as passed, failed, unavailable, or not applicable. Never describe
an unrun check as passing.
