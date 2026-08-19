# Creature Kernel contributor instructions

## Purpose

Creature Kernel is a research-heavy procedural creature compiler and embodiment
runtime. Treat product intent, specifications, architecture, decisions,
experiments, implementation status, and evidence as different kinds of
information. Do not allow one kind to silently redefine another.

## Active-runway discipline

Before autonomous work, read the `Active runway` section at the top of
`docs/project/status.md` and keep the named human checkpoint as the governing
destination. Multiple small reviewed PRs may advance direct prerequisites, but
the main thread must not substitute an internal experiment, evidence, governance,
or infrastructure gate for that checkpoint. If reaching it would require
reactivating a parked workstream or materially expanding the recorded scope,
stop and ask Ben before taking the detour.

## Accepted governance and proposed transition guidance

This file remains binding operational guidance under Accepted DR-0001 Revision
5 while DR-0001 Revision 6 is Proposed. It preserves authority separation,
proposal labels, review evidence, repository safety, and explicit human
ownership. Acceptance applies to the governance process only; it accepts no
product, specification, or architecture proposal. Ben approved the Revision 6
workflow direction on 2026-08-13, so the proposed autonomous engineering lane
below may guide routine implementation during the controlled transition, but
that direction is not formal Revision 6 acceptance. If Ben later accepts,
rejects, or materially replaces DR-0001, the main thread updates or retires
this transition guidance while preserving proposal and review history.

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

## Proposed autonomous engineering lane (DR-0001 Revision 6)

Ben retains decisions about product purpose and scope, user-visible experience
and quality targets, supported morphology or runtime promises, material
platform or engine lock-in, licensing, cost, privacy, external side effects,
large irreversible trade-offs, and acceptance or rejection of product or
direction-setting DRs. The main thread escalates when implementation would
change one of those boundaries.

Within those boundaries, the main thread may settle routine technical
engineering choices without a separate user decision round, including exact
schemas and field names, deterministic or numeric algorithms, diagnostics and
status implementation, build integrity, code and test organization,
reversible dependencies and tools, implementation details, and defect
resolution. Consequential technical reasoning remains durable in the relevant
DR, design note, issue, or implementation evidence; it is not silently
dropped, but it is not a routine approval queue.

The main thread classifies findings as: correctness needed now (fix it); a
retained-human direction or material trade-off (ask Ben); implementation- or
evidence-dependent (record the trigger and defer); or speculative hardening
without a present need (do not build now). Risk-scaled adversarial review,
tests, experiments, and implementation checkpoints remain required where
useful. This lane does not authorize product or architecture drift, external
side effects, DR acceptance, or review-until-clean loops. Subagents remain
bounded executors or reviewers and cannot make product or architecture
decisions independently. Until Revision 6 is accepted, the current accepted
DR-0001 safety and human-ownership controls remain in force.

Prioritize concrete product and implementation progress. Use the least
governance, evidence, and tooling machinery sufficient for an existing
accepted contract or observed risk; do not invent process for theoretical
completeness. Once a gate's stated requirements pass, close it and proceed. If
Ben directs the project to finish machinery and return to implementation, that
is a binding prioritization constraint; do not continue discretionary process
refinement.

When Ben authorizes an autonomous runway of small PRs toward a named human
checkpoint, record that checkpoint in `docs/project/status.md` before merging
along the runway. Merge authority applies only within that recorded runway and
only to internal, reversible preparatory PRs whose required reviews and checks
are complete. An instruction to merge one named or currently open PR is not
standing authority to merge its successors. Stop before merging the first PR
that reaches the named human-visible checkpoint, changes user-visible
CLI/viewer/API behavior intended for Ben's appraisal, or crosses any
retained-human boundary. Present that candidate and its review findings to Ben
first.

Routine developer instrumentation, CLI JSON, metadata tables, diagnostics, and
correctness plumbing remain autonomous implementation even when surfaced in a
browser. Do not infer that browser-visible means product-visually meaningful: a
retained-human visual checkpoint requires actual rendered spatial, form,
appearance, motion, or interaction output for which subjective judgment is
useful, unless Ben explicitly asks to inspect the tooling or UI itself. Before
interrupting Ben for appraisal, state what subjective judgment he can make. If
the honest answer is only technical correctness already addressed by tests or
review, do not present it as his checkpoint. Continue small internal and
reversible work autonomously within the recorded runway and merge authority
until a genuine retained-human design choice or useful visual result is ready.

## Decision records and adversarial review

- Use one neutral Decision Record (DR) registry in `docs/decisions/` for
  consequential Governance, Product, Specification, Architecture, or
  cross-cutting choices. Add a `Scope:` field to every DR and registry row.
- Require a DR only for hard-to-reverse, cross-cutting, contractual/public,
  performance-defining, dependency/portability/licensing-locking, or likely to
  be disputed choices. Ordinary wording, derived detail, and reversible
  implementation do not require one.
- Work in batches of roughly two to five related product, direction-setting,
  architecture-boundary, or external-impact decisions or talking points:
  finish and resolve the discussion, have Luna apply non-trivial document
  edits, let the main thread inspect and integrate them, then select a
  risk-scaled adversarial review level. Routine technical implementation may
  proceed in the proposed autonomous lane without a separate decision round.
  At the end of every substantive
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
  and contradictions and presents only actionable findings. For product,
  direction-setting, architecture-boundary, and external-impact findings, do
  not auto-fix decision-bearing issues or run a review-until-clean loop; return
  concise findings for Ben. The main thread may autonomously fix technical
  correctness findings within the proposed delegated boundary and records
  implementation-dependent deferrals.
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
- Track the accepted semantic-foundation directions for authoritative semantic
  source, durable semantic identity, and artifact/build identity in DR-0002 and
  DR-0006; keep their concrete schemas, profiles, and activation bindings
  Proposed or gated. Keep engine-independent core boundaries as Proposed
  concerns in DR-0003; none are binding implementation requirements until the
  relevant DR is accepted.
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
- For browser navigation, inspection, interaction, screenshots, or recordings,
  use the T3 collaborative preview first. If that preview is unavailable and a
  Windows Chrome/CDP fallback is required, pass a readable PowerShell script on
  standard input only through
  `dev-tools/visual-review/powershell-stdin.sh`. Never use PowerShell
  `-EncodedCommand`, Base64, or another obfuscated command payload for this
  work.
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
- First inspect the authoritative live-thread list and statuses. Treat an
  `agent thread limit reached` failure as a structural slot condition, not model
  capacity; do not apply model fallback or capacity retry. If an obsolete
  interrupted or idle thread appears to occupy a slot, send it a no-work
  close-out message, trigger one bounded follow-up turn instructing it to return
  immediately without reads or edits, verify that it becomes `completed`, and
  retry the blocked spawn once. Do not interrupt useful active work or recycle a
  thread when fresh-context independence is required; wait for a genuine slot
  instead. The harness has no delete/archive operation. If this bounded recovery
  does not free a slot, report the authoritative statuses and stop rather than
  starting an unbounded recovery loop.
- Subagents must promptly report environment or tool failures that cause a
  retry, workaround, or changed execution path. Include the command/tool
  category, exact observed error, attempt count, workaround, and what is known
  versus inferred about the cause. Do not silently absorb repeated or opaque
  failures merely because the bounded task eventually succeeds. Evidence-only
  or read-only scopes prohibit repository edits, not reporting to the
  orchestrator. The main thread decides whether the friction warrants an AI
  observation, tooling change, or concise report to Ben.
- Delegate only bounded work with a disjoint scope and explicit success
  conditions. Proactively use Luna for substantial repository search,
  diagnosis, nontrivial code or documentation edits, evidence preparation, and
  focused checks when bounded. Sol normally retains planning, user decisions,
  returned-diff inspection and integration, one consolidated validation pass,
  Git/PR/CI/external operations, and final judgment; trivial edits and checks
  may remain local. Avoid repeated main-thread command/edit loops when one
  bounded worker plus consolidated final validation suffices, and do not
  delegate ceremonially.
- Before merging a PR that adds or materially changes an operable CLI, API,
  viewer, tool, or similar user/integrator-facing feature, normally use two
  fresh independent `gpt-5.6-luna`/`high` hands-on trial agents on the completed
  local candidate, after implementation and focused checks and before the
  first push or PR presentation. They execute the feature with distinct
  first-use/operator-usability and
  realistic/adversarial-scenario lenses; prompts bound the entrypoint,
  claims/scenarios, temporary data, stop condition, and prohibited side
  effects. Keep cost bounded to the PR's new or materially affected entrypoint
  and directly connected claims/flows, never the whole application by default.
  Prefer headless CLI/API execution and reusable smoke harnesses; use
  computer-use or screenshots only for changed visual/interactive claims.
  Sample representative success and failure paths rather than the full matrix;
  a broad release-level whole-application trial requires an explicit scoped
  decision. Their reports include commands/scenarios, observed outputs,
  correctness defects, usability concerns or suggestions, and untested gaps.
  The main thread reproduces correctness findings, fixes merge blockers, and
  reports remaining usability findings before merge. Material fixes rerun the
  affected hands-on scenario before push; tiny/local fixes need only focused
  regression where appropriate. Later changes retain the before-merge trial
  safeguard. This complements tests and adversarial design/code review and is
  not a review-until-clean loop. A purely internal change without an operable
  entrypoint may use one focused integration-consumer exercise when two user
  trials add no value.
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
