# Baseline005 anthropomorphic calf measurement diagnostic

Status: diagnostic-only analysis of immutable saved meshes. Baseline005 remains
rejected by its frozen `signed_calf_posterior_expansion` gate. This note changes
no geometry, protocol, helper, or outcome.

## Provenance

The diagnostic read
`connected-leg-assembly-005-integrated-{snapshot,run}` in
`/home/ben/.cache/creature-kernel/`. Its retained derivation script is
`connected-leg-assembly-005-calf-measurement/derive.py` (SHA-256
`c68aee6108b3322eb12647bd874a462d195d09b027f149a90ebbc01e4bd0d79a`)
and its machine-readable output is `evidence.json` (SHA-256
`316b5f67764a8382e979b46dfef126ab419a404127e91f64e616afd18e4337c6`).
The managed frozen launcher executed that script against the saved JSON only;
no body construction, pose, collision, or render was rerun.

Captured source SHA-256 identities were: `perturbations.py`
`ffb1a35594a63534108efd7851262a1b28324dbee677d3cc226974c71372340d`,
`construction.py`
`199672cfb8b57d49842d63b7c1043a0a85b1129eb742dd4b0d8016f52b6b765b`,
`runner.py` `ef41bb5823787308410d25b3e499e0abfde4ea30cf259aaf4c0b6ddbc3a33bd2`,
`inputs.json` `1fbd9448bcef2861fc61623b497e67bd2e84a1106818dcac9d84dcf04bd60bda`,
and `protocol.json`
`8d62a981f37de28500e1b15b545c0e608941610d5fb253902dd450526d010446`.
The anthropomorphic snapshot inputs were `005-mesh-L0`
`6237cc7940e1559fbf05d18ab20d87b444c3dd3dd7238a41ffe17f3c6b881e2e`,
`006-mesh-L2`
`59e4ee377c28451b36ebb821199ecc386bf01ee2421db86d9ada18da9c9bf761`,
`007-binding`
`91e85077e88ea3c503a593755449bb7cce36fac5bd8ac71743fee6449a2c9aa2`,
`008-case` `0f3a9bd29d33f8a9ca5f6b116084209c539eb37120d93d9973c00613358d8c91`,
and `009-landmarks`
`4cd4ca7f973a5f9953818446c7cd7252dae4065bcb4aba8e7b9f423e31c991fb`.
Exact saved-output paths and hashes are in `evidence.json`.

## Finding

The source perturbation raised the left posterior calf radius from `0.065` m
to `0.0715` m. At the calf, local
`F=(0,-0.32599068331940423,0.9453729816262723)` and posterior is `-F`.
The frozen strict `forward < 0` selection chose template slots 0, 1, 6, and 7:

- slot 0: `(-0.7071067811865474,-0.7071067811865474)`, `4.596194` mm;
- slot 1: `(-1,-7.988858113051086e-18)`, `0` mm;
- slot 6: `(0.7071067811865474,-0.7071067811865475)`, `4.596194` mm;
- slot 7: `(-1.4030851643930054e-17,-1)`, `6.5` mm.

Slot 1 is the nominal lateral planar sample. A binary64 projection residue made
its template forward coordinate slightly negative, so the frozen gate selected
it even though its emitted coordinate displacement rounded to exactly zero.
The recorded L0 analytic error was `9.35e-17` m and full-stencil L2 error was
`2.74e-16` m, both within the frozen `1e-8` tolerance.

Local L0 response was confined as designed: maximum displacement was `2.228571`
mm at knee-post support, `6.5` mm at calf, and `2.8` mm at ankle approach; the
mid-thigh, knee-pre, knee, ankle, root, and opposite leg remained unchanged.

Across the 416 L2 vertices with nonzero stencil support from any of the eight
L0 calf-ring controls, signed displacement along calf `-F` was positive at 273,
zero at 143, negative at 0, and at most `4.773528` mm. The posterior support
envelope moved from `0.0546801503` m to `0.0594536780` m, an expansion of
`0.0047735277` m. This is a support-domain envelope across the subdivided calf
neighbourhood, not an exact planar calf section; it demonstrates coherent
supported posterior expansion but does not characterize one cross-sectional
profile or establish anatomy quality.

## Bounded interpretation and closure

The zero therefore identifies a measurement-selection defect, not absence of
meaningful posterior L2 response. It does not retroactively pass Baseline005.
If independent review agrees, evidence closure can reuse these same saved
baseline and perturbed meshes: remeasure a tolerance-classified strictly
posterior domain and/or the declared L2 support envelope, recording that as a
later diagnostic. Repeating the unchanged 10-pose collision run would add no
evidence about this measurement defect.

Independence limit: this analysis began from Main's reported failed metric and
was completed before considering Noether's independent report.

## Accepted measurement-only closure

Main accepted the subsequent Baseline007 measurement-only closure after direct
review of the fixed 416-vertex support domain, literal before/after extrema,
all-row pass reduction, and exact comparisons with the preserved 005 geometry.
The exact report is
`/home/ben/.cache/creature-kernel/connected-leg-assembly-007-measurement-closure/measurement-closure.json`
(SHA-256
`ae1d322e6b43b51708e81b0b3e8224af19cdce17b9ab1c70337cdc73e9f960b1`).
The focused perturbation suite passed 9 tests with 0 failures.

Within that report, `built_L0` is the perturbed constructor result and
`perturbed_L0` is the evaluator's identical L0 return. They are aliases from
one perturbation regeneration, not independent executions. Likewise,
`execution.body_generation: false` means that no upstream calibrated root was
generated: the calf perturbation geometry was regenerated from the saved 005
root. No new pose, collision, or render was run. This acceptance closes only
the corrected calf measurement; it does not pass the rejected 005 full run,
accept body anatomy, or establish a whole-character result.
