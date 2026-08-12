# Creature Kernel contributor instructions

## Purpose

Creature Kernel is a research-heavy procedural creature compiler and embodiment
runtime. Treat product intent, specifications, architecture, decisions,
experiments, implementation status, and evidence as different kinds of
information. Do not allow one kind to silently redefine another.

## Accepted governance and operational guidance

This file is binding operational guidance under Accepted DR-0001 Revision 5.
It preserves authority separation, proposal labels, review evidence, repository
safety, and explicit human ownership. Acceptance applies to the governance
process only; it accepts no product, specification, or architecture proposal.
If Ben later supersedes or materially replaces DR-0001, the main thread retires
or migrates these controls while preserving proposal and review history.

## Required reading order

Before consequential design or implementation work, read:

1. `docs/README.md`
2. `docs/product/vision-and-scope.md`
3. `docs/product/requirements.md`
4. `docs/architecture/README.md`
5. `docs/project/status.md`
6. Any relevant specification, decision record, research question, or experiment record

`docs/FOUNDATION.md` is the historical founding record. It explains how the
project arrived here but is not the canonical owner of current contracts.

## Authority

- `docs/product/` owns desired outcomes and externally observable requirements.
- `spec/` owns normative formats, semantics, identifiers, and compatibility.
- `docs/architecture/` owns target technical boundaries and invariants.
- Accepted decision records explain decisions but do not replace canonical product,
  specification, or architecture documents.
- `docs/research/` owns open questions and research context, not target contracts.
- `experiments/` records evidence. Results may inform decisions but do not become
  architecture automatically.
- `docs/developer-workflows/` owns conditional contributor procedures, not product
  or technical contracts.
- `docs/project/` reports plans and status without redefining target behaviour.
- Code, tests, fixtures, and benchmarks provide implementation evidence.

When documents conflict, stop and resolve the conflict in the canonical owner.

## Decision records and adversarial review

- Use one neutral Decision Record (DR) registry in `docs/decisions/` for
  consequential Governance, Product, Specification, Architecture, or
  cross-cutting choices. Add a `Scope:` field to every DR and registry row.
- Require a DR only for hard-to-reverse, cross-cutting, contractual/public,
  performance-defining, dependency/portability/licensing-locking, or likely to
  be disputed choices. Ordinary wording, derived detail, and reversible
  implementation do not require one.
- Work in batches of roughly two to five related decisions or talking points:
  finish and resolve the discussion, have Luna apply non-trivial document
  edits, let the main thread inspect and integrate them, then select a
  risk-scaled adversarial review level. At the end of every substantive
  design-cycle handoff, the main thread explicitly states
  `Recommended adversarial level: None|Single|Double — <one-line reason>`.
  This is advice to Ben and a durable planning signal, not automatic
  acceptance. `None` is for purely mechanical/reversible work or discussion
  with no created or materially revised consequential DR and no novel
  evidence-bearing claim; it cannot satisfy the review prerequisite for a
  created or materially revised consequential DR, which still needs review or
  Ben's explicit recorded waiver. `Single` is the normal default for a
  consequential DR or meaningful bounded design batch and means one fresh
  independent pass. `Double` is exceptional for direction-setting,
  cross-cutting, hard-to-reverse or locking, technically complex,
  strongly evidence-dependent, disputed, or difficult-to-audit work; it means
  two genuinely independent fresh passes with distinct named lenses, normally
  Sol medium for foundational work, not duplicate prompts presented as
  diversity. More than Double or Sol above medium requires Ben's explicit
  approval. Ben may raise or lower the recommendation or waive as already
  governed. A material proposal change increments its revision and makes
  older reviews stale; when Double remains justified by the decision's impact,
  the revised current version normally receives Double again unless Ben
  changes or waives it. Double is one pass per reviewer on the current
  revision, not review-until-clean. The main thread consolidates duplicates
  and contradictions and presents only actionable findings. Return concise
  findings with the next researched batch; do not auto-fix decision-bearing
  findings or run a review-until-clean loop.
- Do not change a DR to `Accepted` without a current-revision adversarial review
  or an explicit Ben waiver recorded as `Review status: Waived` with one
  non-placeholder `Waiver reason:` line, plus Ben's human approval.
- Preserve rejected and superseded decisions so their reasoning is not lost.
- Record waivers explicitly; never imply missing evidence was supplied.
- Reviews must challenge assumptions, alternatives, failure modes, performance,
  reversibility, portability, licensing, and missing expertise where relevant.
- Unaccepted material must be labelled `Proposed` or `provisional`; assistant-
  synthesized product and architecture prose is not an accepted contract.

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
- Track authoritative semantic source, durable semantic identity, and
  artifact/build identity as Proposed concerns in DR-0002 and DR-0006. Keep
  engine-independent core boundaries as Proposed concerns in DR-0003; none are
  binding implementation requirements until the relevant DR is accepted.
- Do not commit large generated meshes, caches, captures, or datasets without an
  approved artifact-storage decision.
- Keep any implementation boundaries consistent with accepted canonical
  contracts once those contracts exist; current engine-independent separation
  remains a Proposed architectural direction.
- Preserve unrelated user changes and stage only files belonging to the task.

## Conditional workflows

- Subagent selection, delegation boundaries, model routing, and independent
  review use
  `docs/developer-workflows/ai-delegation-and-review.md`.
- Any AI thread may append a genuinely reusable operational observation to
  `docs/project/ai-observations.md` after recurring tool misuse, unavailable or
  broken routes, misleading harness or environment behavior, or other token- or
  round-saving friction is evidenced, subject to normal write-scope rules. Do
  not read it as guidance for ordinary work; nobody rewrites or deletes
  existing entries during ordinary work. Consume or act on the inbox only in a
  purposeful human-requested AI tooling or instruction improvement round with
  Ben, using it as feedstock to improve tools or instructions and then
  deliberately removing or retaining entries.
- A decision-record review may use
  `docs/decisions/reviews/fresh-reread-preamble.md` to force a current-disk,
  issue-only convergence pass.

## Orchestration

The main `gpt-5.6-sol` thread owns planning, human design discussion, task
decomposition, integration, consolidated validation, Git and pull-request
operations, CI and review orchestration, external side effects, and final
repository decisions. It does not delegate product or architecture decisions.
Reviewers may challenge a proposal and recommend a disposition, but only Ben,
the human decision owner, accepts or rejects a DR.

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
- If a launch or turn fails because the selected model is at capacity, wait
  30–60 seconds and retry that same model and reasoning tier once. Escalate or
  fall back only if that same-tier retry also fails, or if the task independently
  warrants a different tier. Report to Ben immediately: the failed model/tier,
  first-failure time, actual wait duration, wait/retry count, retry result, and
  any fallback model/tier. Repeat the routing deviation and those details in
  the end-of-round subagent status. This 30–60 second wait is provisional; use
  outcome reporting to tune it, without adding heavyweight telemetry. Do not
  retry non-capacity failures or start an unbounded retry loop.
- Delegate only bounded work with a disjoint scope and explicit success
  conditions. The main thread remains responsible for evaluating the evidence.
- Parallel workers must have disjoint write scopes. The main thread inspects every
  returned diff, reconciles interactions, and validates the integrated result.
- Independent reviewers should normally be fresh-context agents that did not
  implement the material under review.
- Keep final subagent-use reporting brief and auditable: use one concise line per
  subagent stating its bounded role, model, reasoning effort, and either
  `edited files` or `evidence only`; then use one concise validation line for
  subagent-scoped and main consolidated checks. Also disclose any explicitly
  authorized routing deviation or incomplete review coverage. Do not require a
  prose summary in place of these lines.

## Validation

Run before committing documentation or decision-record changes:

```bash
python3 dev-tools/validation/validate_docs.py
git diff --check
```

Report checks as passed, failed, unavailable, or not applicable. Never describe
an unrun check as passing.
