# Provisional stacked integration ledger

Status: provisional local packaging record

Captured at: 2026-09-07T18:15:40.632513+12:00 (NZST)

Worktree: `/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor`

Branch: `codex/owned-root-assembly-successor`

This ledger records the current checkout inventory for packaging discussion. It
does not establish runway authority, merge authority, or an execution/acceptance
result. Local layer counts are checkout deltas only; prospective PR counts must
also account for files already present in the PR head and for repeated
stage-specific documentation overlays.

## Local baseline

`git status --short --untracked-files=all` reported 181 paths: 17 modified
tracked paths (16 eligible and one protected), and 164 eligible untracked
paths. The protected path, `docs/project/ai-observations.md`, was excluded
without reading, staging, editing, or assigning it. The 180 eligible paths
include the new ledger itself as a changed file. Preserved unrelated
modifications remain visible in Layer 1 but are marked relevance-pending and
are not automatically authorized for integration.

The filesystem scan found 37 ignored `__pycache__/*.pyc` files under the
scanned experiment and tool roots. They are cache artifacts and are excluded.
No binary or generated artifact path appeared in the status inventory after
that exclusion. Referenced `/home/ben/.cache` snapshots, renders, transcripts,
and manifests are outside this worktree and are not counted. Evidence JSON,
Markdown, source, and tests that are present in the worktree remain counted.

Each manifest hash below is SHA-256 over sorted eligible relative paths and
their individual SHA-256 values, one `path\0file-hash\n` record per path. Layer
1 counts the ledger path, while its digest excludes that self-referential file;
the other layer digests include every listed path. This gives a reproducible
local identity without pasting hundreds of file hashes.

## Three-layer candidate stack

The causal order is the existing PR127 baseline, lower connected-leg/source
prerequisites, then the active foundation and body integration. All counts in
the table are local checkout deltas and sum to all 180 eligible paths.

| Layer | Purpose and path set | Local delta | Headroom to 90 | Local manifest SHA-256 |
| --- | --- | ---: | ---: | --- |
| 1 | Existing tracked delta plus this ledger: all 16 eligible modified tracked paths (listed below) and `docs/project/stacked-integration-ledger.md` | 17 | 73 | `3677c96f96cc6bfdd50d9753f7a011489541ae872704174444b0e322040b7de7`* |
| 2 | Pelvis source experiments (35) plus lower connected-leg runner/source/check prerequisites, active foot/tail/calf paths, and standalone arm/head builders/tests (48 connected paths) | 83 | 7 | `0bd9074f6126901bf7bd0774bdbe02ba5470d14a80b97a1fd2ddc71c5170df19` |
| 3 | Remaining connected-leg foundation providers, body assembly/configs, pelvis support, torso/chest, and arm/head refinement paths (80 connected paths) | 80 | 10 | `99ef576357dbe98143f5fde9682131931fb800bdd3c7c07cb4a4079d4fc811c4` |

The Layer 1 digest is marked with `*` because the ledger is counted as a
changed file but omitted from its own digest to avoid a self-referential hash.

Layer 1's 16 pre-existing eligible modified tracked paths are
`dev-tools/visual-review/{static/app.js,static/style.css,tests/test_visual_review.py}`
(3), `docs/project/{README.md,current-handover.md,status.md}` (3),
`docs/research/README.md` and `experiments/README.md` (2), all seven status
paths under `experiments/owned-root-assembly-successor/`, and
`experiments/programmatic-root-complex-surface/tests/test_prepared_projection.py`.
Preserved unrelated changes in this set are relevance-pending; they are not
automatically authorized for integration.

Main supplied the current PR127 baseline evidence: OPEN DRAFT, base
`main` at `db5f11efff124d500d875f7839c53fee9a75f395`, head
`4ae0a5c8176c60791248ad6eb5e52dc657a2dd34`, and 51 changed files. Fourteen of
those remote paths overlap Layer 1's local delta. The three local-only paths
are `dev-tools/visual-review/static/style.css`, `docs/project/README.md`, and
this ledger, giving a provisional 54-path PR127 total if no other path is
added. This is current-head evidence supplied by Main, not a guarantee at the
future packaging boundary. A changed PR127 head or additional existing paths
could consume the remaining Layer 1 headroom, so recheck the exact head before
materialization; repeated documentation overlays must be counted again in each
follow-up PR.

Layer 2's 48 connected paths are: the lower shared set
`{README.md,protocol.json,hip_source.py,perturbations.py,inputs.json,binding.py,
checks.py,construction.py,root_source.py,runner.py,captured_tests.py,
collision_broadphase.py,example-brief.md}` plus the nine corresponding
`tests/test_{binding,captured_tests,checks,collision_broadphase,construction,
hip_source,perturbations,root_source,runner}.py` paths (22); standalone
`arm_construction.py`, `head_construction.py`, and their construction tests
(4); all foot paths and tests (17); all tail paths and its test (4); and
`005-calf-measurement.md` (1). The three pelvis experiment directories add 35.

The pelvis source directories and connected pelvis foundation paths are active
while Main continues the pelvis work. Their counts and hashes are therefore a
timestamped local snapshot and must be refreshed at the next clean packaging
boundary; no freeze or pause is requested.

Import inspection supports this boundary: `runner.py` has no module-level
`body_assembly` import and dynamically loads optional features, so a default
leg-only runner is plausible before the body feature layer, but it remains
unverified. Foot modules import the lower construction/runner helpers; tail
imports construction; arm/head construction modules are standalone. No
execution or numerical calculation was performed.

Layer 3's 80 connected paths are grouped as: pelvis foundation/support (19),
abdomen foundation/provider/evidence (9), thorax foundation/contract/evidence
(12), torso refinement (10), chest evidence (4), arm refinement (4), head
refinement (4), and body assembly/config variants/tests (18). Keeping these
together supplies the abdomen/thorax/provider/body-assembly dependencies
required by the pelvis foundation. In particular, body configs and
`body_assembly.py` remain above the lower runner layer; no config is treated as
active merely because it is present.

The lower and foundation follow-ups may each need roughly four repeated
documentation paths (`connected-leg-assembly/README.md`, project
status/handover/index material, and related experiment indexes). Budgeting
those overlays gives planning totals of about 87 for Layer 2 and 84 for Layer
3. Do not copy a later final README/status wholesale into an earlier layer;
materialize stage-specific overlays only after their referenced paths exist.

## Placement and retention decisions

All 180 eligible local paths are assigned above; there are no omissions or
deletions. The prior 22-path foot/tail/calf set is deliberately included in
Layer 2 because the body configuration and anthropomorphic path depend on it.
The five body-only shared paths moved above the lower layer are
`body_assembly.py`, `tests/test_body_assembly.py`, `body-config.json`,
`body-junction-integration-config.json`, and
`body-refinement-internal-config.json`; the remaining body configs stay with
Layer 3 as well because they select foundation and refinement inputs.

Layer 3's 80-file local delta leaves ten files before the nominal alert and
about six after its recurring documentation overlay. Layer 2 leaves seven
before the alert and about three after its overlay. Alert the Main Worker if
dependency closure or overlays exceed that space; consolidate only with an
approved retention decision that preserves causal records and provenance.
These counts are local-delta packaging estimates, not summed PR changed-file
counts.

## Conditional packaging priority

At the 2026-09-08 integration boundary, Main rechecked PR #127: its open draft
still has head `4ae0a5c8176c60791248ad6eb5e52dc657a2dd34`, base
`db5f11efff124d500d875f7839c53fee9a75f395`, and 51 remote changed files.
The isolated `codex/pr127-integration` working candidate has **57 prospective
PR paths**, including the six additions relative to that published path set:
the gallery README, browser preflight script and mocked test, gallery CSS,
project index, and this ledger. The existing CLI import correction overlaps
the published path set. Protected inbox contents remain excluded. This
materialization count supersedes the earlier 54-path estimate for Layer 1;
the timestamped upper-layer inventory and approximately 87/84 follow-up
budgets remain planning evidence. Browser repair validation is non-launching,
and real-browser coverage remains incomplete.

When the lowest layer is clean and final-review-ready, the recorded priority is
one hosted CodeRabbit cycle together with the committed CLI cycle on the same
immutable pushed OID. Do not mutate that head while hosted review runs; safe
upper-layer work may continue, with rebasing or retargeting only after the
lower layer merges and applicable gates are satisfied. This is a conditional
future priority, not an immediate external action or a new authority grant.

Validation for this documentation change is run after the index link is added:
`python3 dev-tools/validation/validate_docs.py` and
`dev-tools/validation/check_worktree_whitespace.sh`.
