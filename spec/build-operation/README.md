# Build operation and derived-output contract

Status: Proposed conceptual contract; CK-KICK-012 Batch 13/14 discussion-approved
canonical owner. Current Batch 13/14 material is recorded in DR-0006 Revision 11,
DR-0011 Revision 14, DR-0012 Revision 13, and DR-0013 Revision 11; each remains
Proposed with Owner approval Pending and Review Pending after material
technical-review resolution edits; prior Batch 13 review evidence is stale and
fresh successor-target review is pending. Batch 13/14 cross-links
the C1 keyed-collection, C3 separate implementation-binding, and C4
diagnostic/bootstrap resolutions. This document owns build/output status and
adapter output context only; it does not own comparator arithmetic, diagnostic
registry definitions, or fixture implementation-binding framing. It is not an
accepted format and does not activate a build implementation, serializer,
fixture corpus, or artifact store.

This document is the canonical Proposed owner of the public `build` operation
and its derived-output/publication contract. The [body-document contract](../body-document/README.md)
owns source admission, resolution phases, resolver statuses, diagnostics, and
the in-memory resolved-snapshot handoff. [DR-0006](../../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md)
owns durable semantic identity and the separation of build and artifact
identity. [DR-0013](../../docs/decisions/DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
owns the Proposed platform boundary and activation gates. The [canonical-data
profile](../canonical-data/README.md) owns canonical JSON and digest framing;
this contract owns which outcome-affecting values enter the build-request
projection. This contract does not choose final avatar-package field
vocabulary, transport, or a permanent geometry backend.

The words **must**, **must not**, and **may** state this Proposed contract. The
exact serialized syntax and concrete filesystem encoding remain deferred. The
canonical-data, semantic-address, numeric/frame, and diagnostic profiles are
Proposed activation prerequisites. The conceptual target and lifecycle rules
below are normative within the proposal.

## Operation boundary

The public `build` operation uses one authoritative result envelope from source
admission through derived generation and publication. Geometry, worker,
encoding, staging, and publisher diagnostics are normalized into that envelope;
they do not create a competing status channel. The resolver's closed statuses
remain `success`, `input-failure`, `invalid-source`, `unsupported`,
`dependency-failure`, `resource-limit`, and `internal-failure`. The build
operation extends that vocabulary with `output-failure` for a trusted
derived-output, staging, encoding, collision, or publication failure after
source/semantic work, subject to earlier status precedence.

Resolver success and output publication are separate boundaries:

```text
source admission -> in-memory resolved snapshot -> derived build outputs
                                      -> staged manifest -> atomic publication
```

Phase 8 of resolution is in-memory resolved-snapshot finalization and handoff.
It is not filesystem serialization and does not itself commit an artifact. A
successful `resolve` operation must contain the validated snapshot required by
that operation's contract. Other operations, such as `validate`, may omit a
snapshot only when their own operation contract explicitly permits omission.
Serialization and publication of a snapshot or any other derived output belong
to `build`; failures in those external steps are `output-failure` when the
operation still trusts the result. A source-caused semantic failure remains an
`invalid-source` or `unsupported` resolver outcome, not an output failure.

Status precedence remains global: loss of trust is `internal-failure`; a
qualifying configured resource or time interruption that prevents required
processing or trusted completion is `resource-limit`; otherwise the earliest
applicable phase that cannot produce its required output determines the status.
The body-document same-phase and dependency precedence rules continue to
apply. A root diagnostic and its causal identity must remain available even
when a later build/publication failure normalizes the top-level status.

## Future adapter and output context

The core resolved snapshot and all semantic graph comparisons remain binary64.
A future adapter has two distinct guarantees: (1) a conversion/output
guarantee that a requested target profile is applied and validated before
publication, and (2) a runtime guarantee that the published output advertises
only the capabilities and quality/runtime tier it can actually support, with a
strictly positive target unit scale where the target uses a different length
unit. A non-positive or otherwise invalid requested scale cannot produce a
trusted adapter output. The exact scale representation and numeric validation
remain owned by the numeric/frame profile.
These are separate output and runtime metadata concerns; this operation does
not select an engine or redefine numeric/frame conversion rules. The
numeric/frame profile owns basis maps, narrowing, subnormal/underflow/overflow,
rotation conversion, and angular/translation formulas and budgets. This build
contract owns only the output boundary, capability/guarantee metadata, and
failure context.

Adapter output must fail closed for any target-profile violation. It must not
saturate, clamp, or depend on an ambient numeric mode. A requested but
unsupported target profile maps to `unsupported`; a trusted conversion,
encoding, or output validation failure maps to `output-failure`; a qualifying
resource breach maps to `resource-limit`; and loss of worker/coordinator/
publisher trust maps to `internal-failure`, under the global precedence above.
The root semantic diagnostic remains in the authoritative envelope when output
status is normalized. Adapter activation is a separate post-Readiness-3
transaction with its own conformance fixtures and profile binding; no adapter
is active from this Proposed contract. The exact runtime capability labels,
profile IDs, and status code strings remain fixture-gated.

The adapter status mapping reuses the existing operation statuses, but
malformed adapter request/profile mapping is deliberately unselected until
adapter activation. Adapter profile data is a build-request/target-platform
input, not authoritative body-source content. Before an adapter profile/schema
activates, the owning request-validation mapping must be chosen and reviewed
while preserving the closed operation status set (or explicitly revising it).
A well-formed unknown profile revision or unavailable claimed capability remains
`unsupported`; a violated already-admitted project-profile invariant remains
`internal-failure`; and a valid supported profile whose conversion overflows,
whose underflow is disallowed, or whose output is malformed/invalid remains
`output-failure`. Until then no adapter activates, and malformed adapter
profile input is not classified here as `invalid-source` during source
admission. Resource and trust outcomes retain their existing precedence over
these mappings. Exact diagnostic codes and field names remain fixture-gated.
This request-validation choice is implementation/evidence-dependent and is not
a blocker for the first Rust slice.
Proof obligations include zero/negative/nonfinite scale, unknown revision,
unavailable capability, invariant violation, overflow, disallowed underflow,
malformed output, and precedence fixtures; this contract does not create those
fixtures or activate an adapter.

## Identity and manifest lifecycle

Build and artifact identity are distinct. Every invocation has a unique
`attempt_id`, including an invocation that fails before it can establish a
complete build request. The authoritative CLI/API result envelope,
invocation-owned staging metadata, and logs may use that attempt identity for
tracing only. A deterministic `build_request_id` is established from the complete
outcome-affecting request when that request is available; it is stable across
retries. Artifact identity is committed only after successful publication. The
staged manifest carries a **candidate artifact identity**: it is a
non-authoritative proposal used to name and validate the staged result, not
proof that an artifact has been published. Successful atomic publication
promotes that same candidate identity to the committed artifact identity;
publication does not mint a replacement identity.

Attempt identity is invocation-local trace data. It never enters committed
success manifests or other committed artifact bytes, and never affects the
target, candidate identity, deterministic equality, or idempotent equality. A
build request includes every outcome-affecting source/source-set, an exact
reference to the implementation-content-binding identity used for execution,
an exact reference to the dependency-closure identity used for execution,
compiler and toolchain, contract/schema/profile, configuration and seed,
backend capability/protocol, and target-platform input. These are references
only: its deterministic projection does not inline raw implementation
path/mode/content entries or raw dependency sets, which remain owned by their
separate domains. Fixture-payload identity and attempt identity are excluded.
Omitting an outcome-affecting input or either exact execution binding reference
is an identity error. Its deterministic projection and digest use the
[canonical-data profile](../canonical-data/README.md), and activation is blocked
until that profile and all referenced semantic profiles are admitted. If a
readiness gate activates code, the separate implementation binding owned by the
[fixture-manifest contract](../fixture-manifest/README.md) is checked as part of
that gate; the binding record is outside the fixture payload and is not a
whole-repository or commit-equality identity.

For each artifact role, candidate artifact identity derives deterministically
from the build-request identity, artifact role, and identity-rule revision.
When publication succeeds, that candidate is promoted unchanged to the
committed artifact identity. The identity rule must not incorporate attempt
identity, timestamps, staging paths, or incidental ordering.

The manifest is written last within immutable, invocation-owned, build-scoped
sibling staging. Its conceptual fields are:

| Field group | Proposed contents |
| --- | --- |
| Build lineage | deterministic `build_request_id` when established, source/dependency/configuration/seed lineage, and contract/profile revisions; no attempt-local data |
| Candidate identity | non-authoritative candidate artifact identity and its identity revision |
| Outputs | relative output paths, expected sizes, hashes, and output roles |
| Integrity | manifest revision, completeness, and the data needed to verify one build lineage |
| Diagnostics | top-level status, primary/root diagnostic reference, and completeness |

Exact manifest member names and final artifact package fields remain deferred;
canonical bytes and digest domains are owned by the [canonical-data profile](../canonical-data/README.md).
The manifest must be complete and internally consistent before
publication is attempted. Any semantically unordered output or metadata
collection must declare its typed total canonical key and uniqueness or
multiplicity rule under the canonical-data profile before activation;
consumers must reject missing or colliding keys rather than falling back to
array index or source order. Consumers must reject absolute or traversal paths,
symlinks, unlisted outputs, incomplete manifests, mixed-build lineage, and
stale or unverifiable identities.

## Deterministic target and collision rule

The explicit output root is an input to `build`; it is never inferred from a
source filename, current directory, stale manifest, or existing occupant. The
one conceptual target rule is:

```text
target = explicit_output_root / candidate_artifact_identity
```

The candidate identity is one validated, safe path component: it is non-empty,
contains no path separator or dot-segment, and is not accepted if its platform
mapping is ambiguous. This is a conceptual path rule, not a commitment to a
particular serialized directory layout. The target is derived deterministically
from the explicit output root and candidate identity; no timestamp, traversal,
source basename, or guessed prior artifact may alter it.

Publication uses an atomic no-replace primitive. Before publication, an
existing target may be admitted as an idempotent result only when inspection
verifies the same committed artifact identity, build/source/dependency lineage,
complete manifest, and all listed output hashes and sizes. Such a verified
match returns `success` with an `already-published` outcome and commits no
replacement. A different, incomplete, stale, or unverifiable occupant is an
`output-failure` with a target-conflict diagnostic; it must never be overwritten,
adopted, or repaired in place. A no-replace collision always performs
post-collision inspection. Exact identity, lineage, complete manifest, and all
listed output hashes/sizes mean `already-published`; a different lineage is
`target-conflict`; and a target with the same deterministic request/candidate
but byte-divergent output is `internal-failure` with a
`nondeterministic-output` diagnostic. The latter is not repaired or accepted as
an alternate winner. If the required atomic no-replace primitive is unavailable,
the operation fails closed as `output-failure`; it must not use an adoption,
delete-then-rename, or overwrite workaround.

Cleanup is limited to invocation-owned staging. An existing target and an
unrelated directory are never cleanup targets.

## Initial filesystem profile

The initial supported profile is a tested local Linux filesystem under WSL in
`/home`. `/mnt/c`, network filesystems, removable media, and unspecified
filesystems are outside this profile. Publication uses same-filesystem sibling
staging, a capability probe, an atomic no-replace primitive, immutable
committed outputs, cooperating builders, and post-collision inspection.

This profile claims process-crash-safe namespace publication only. It makes no
sudden-power-loss durability claim. Malicious or privileged concurrent
filesystem mutation is outside the initial threat model; inspection still
verifies a complete artifact or rejects it. The candidate filesystem component
uses a profile-defined unambiguous safe ASCII mapping. The exact mapping is an
activation prerequisite, not an implementation detail that may vary between
builders.

## Inspection and lineage

Artifact inspection is a separate read operation, not a second build-status
channel. Callers must provide the expected build and artifact lineage (and any
required contract/profile identity). Inspection verifies that expectation
against the target's committed manifest, identity, paths, hashes, sizes, and
completeness. Its closed result statuses are `success`, `absent`, `unavailable`,
`mismatch`, `invalid-artifact`, `unsupported`, `resource-limit`, and
`internal-failure`. Their meanings are respectively: the expected committed
artifact is verified; no target exists; the target cannot be read; the target is
readable but does not match the expected lineage; the target is malformed,
incomplete, or unverifiable; the requested inspection contract/profile is not
supported; configured inspection work/resources prevent trusted completion; or
implementation/environment trust is lost. Inspection precedence is
`internal-failure`, then qualifying `resource-limit`, then the earliest
applicable read/validation failure; a complete readable artifact with wrong
expectations is `mismatch`, not `invalid-artifact`.

Inspection reports processing completeness and diagnostic completeness under the
same shared envelope conventions as other operations. Every non-success
inspection result has a primary diagnostic; successful inspection has no
failure primary. It must never guess that an occupant belongs to the requested
build or silently treat stale output as current. Exact read-operation syntax
remains deferred.

## Failure-bundle trust boundary

A compile or geometry worker's producer/output trust is separate from the
coordinator, diagnostic reporter, and publisher trust. A worker crash,
protocol loss, or malformed result invalidates that worker's output. A trusted
isolated parent may authoritatively report only its own observation of the
worker failure in the result envelope; it must never adopt worker output after
trust is lost. Loss of coordinator, reporter, publisher, or invariant trust
forbids publication and may leave only the surrounding launcher/CLI envelope.

The initial contract persists no diagnostics-only failure bundle. Successful
operations may publish a success bundle; failed operations return the
authoritative CLI/API failure envelope, and any attempt-local staging is
cleanup-only. A later requirement to persist attempt evidence or a diagnostics
bundle needs a separate identity and lifecycle decision. Validation cannot
rehabilitate output whose worker trust was lost.

## Operation outcome matrix

The following matrix is the complete Proposed outcome boundary. “No final
artifact” means the authoritative failure envelope is still returned; it does
not mean the process may discard the root diagnostic. Success bundles are the
only persisted derived-output bundles in this initial contract.

| Condition | Top-level outcome | Snapshot / publication consequence |
| --- | --- | --- |
| Source unavailable, unreadable, or incomplete before complete acquisition | `input-failure` | No resolver snapshot; no final artifact |
| Supplied bytes fail UTF-8, strict JSON, discriminator, schema, source semantic, or source invariant checks | `invalid-source` | No successful resolver snapshot or success artifact; return the authoritative failure envelope |
| Unknown family/revision, unsupported required extension, or recognized unsupported assembly/capability | `unsupported` | No successful resolver snapshot or success artifact; return the authoritative failure envelope |
| Required authored dependency cannot be acquired, verified, or matched to its declared revision | `dependency-failure` | No successful resolver snapshot or success artifact; return the authoritative failure envelope |
| Configured source, dependency, graph, work, memory, or diagnostic/resource bound prevents required processing or trusted completion | `resource-limit` | No trusted successful snapshot or success artifact; return the authoritative envelope with the root/resource diagnostic |
| Coordinator, diagnostic reporter, publisher, or invariant trust is lost | `internal-failure` | No trusted successful snapshot or publication; return the authoritative envelope if it remains trustworthy |
| Required build capability is explicitly unsupported, or required worker protocol/version negotiation cannot be satisfied as an unsupported contract | `unsupported` | No derived artifact; retain the capability/protocol diagnostic |
| Worker is terminated by a trusted parent after an established configured deadline or validated resource breach | `resource-limit` | No trusted output from that worker; a trusted parent may report its own observation in the authoritative envelope |
| Unexpected worker termination, transport loss, truncated/corrupt framing, or termination without a qualifying bound loses trust in worker output | `internal-failure` | No worker-produced output; a trusted parent may report its own observation in the authoritative envelope |
| Worker/geometry output is well-framed and decoded but malformed, incomplete, out of contract, or fails output validation while the reporter remains trusted | `output-failure` | No success artifact; return the authoritative envelope |
| A well-framed worker-declared domain failure is received | Governed status after validation | Validate the declaration and map it to the applicable operation/domain status; do not adopt worker output |
| A source-caused resolved-graph invariant fails | `invalid-source` | No successful in-memory snapshot or success artifact |
| An admissible resolved value/transform violates an implementation invariant during derivation | `internal-failure` | No trusted output; return the authoritative envelope |
| Derived output encoding/serialization fails while result trust is retained | `output-failure` | No final artifact; return the authoritative envelope |
| Staging allocation, path, write, manifest, hash, or completeness validation fails while result trust is retained | `output-failure` | No final artifact; clean only invocation-owned staging |
| No-replace collision has the same deterministic request/candidate but byte-divergent output | `internal-failure` (`nondeterministic-output`) | Never accept either divergent result as an alternate winner; preserve the target and report the mismatch |
| Target occupant has different, incomplete, stale, or unverifiable identity/lineage/hashes | `output-failure` (`target-conflict`) | Never overwrite or adopt the occupant; no final artifact |
| Atomic no-replace publication is unavailable or atomic publication fails | `output-failure` | Never fall back to overwrite/adoption; no final artifact |
| Atomic publication succeeds for a new target | `success` | The candidate identity is promoted to the committed artifact identity |
| Existing target verifies identical identity, lineage, complete manifest, and hashes | `success` (`already-published`) | Idempotent success; no replacement and the same identity is committed |
| Inspection receives an expected lineage and verifies a matching committed target | `success` | Inspection returns the verified artifact; it does not rebuild or guess |
| Inspection finds no target | `absent` | Never report an output as current; return the closed inspection status and its primary diagnostic |
| Inspection cannot read the target | `unavailable` | Never report an output as current; return the closed inspection status and its primary diagnostic |
| Inspection reads a target that does not match the expected lineage | `mismatch` | Never report the output as current; return the closed inspection status and its primary diagnostic |
| Inspection reads a malformed, incomplete, or unverifiable target | `invalid-artifact` | Never report the output as current; return the closed inspection status and its primary diagnostic |
| Inspection requests an unsupported manifest or profile revision | `unsupported` | Fail closed; return the closed inspection status and its primary diagnostic |
| Configured inspection work or resources are exhausted before trusted completion | `resource-limit` | Fail closed; return the closed inspection status and its primary diagnostic |
| Inspection implementation, environment, or trust fails | `internal-failure` | Fail closed; return the closed inspection status and its primary diagnostic |

The matrix does not authorize converting a lower-level failure into success by
publishing a partial graph or stale target. When a top-level build status is
normalized to `output-failure`, the originating resolver/worker diagnostic
remains in the envelope as the root diagnostic or causal reference.

## Activation and proof boundary

This Proposed contract becomes implementation-relevant only through the
readiness gates in [DR-0013](../../docs/decisions/DR-0013-first-production-implementation-platform-and-geometry-boundary.md).
Readiness 2 concerns parser/bootstrap and an admitted fixture manifest;
Readiness 3 concerns canonical numeric/frame rules and expected graph outputs;
Readiness 4 concerns a working resolver, provisional geometry profile, and the
project-owned geometry seam. None of those gates accepts this contract or
selects final artifact serialization. Representative fixtures must exercise
new-target publication, idempotent re-publication, target conflict, unavailable
no-replace, malformed output, worker/resource outcomes, root-diagnostic
preservation, and trusted versus untrusted result-envelope observations before
a public implementation claim is made. The identity/publication matrix also
includes first build, retry with a new attempt identity, concurrent winner,
lineage change, and same-candidate byte divergence. These remain conceptual
fixture cases until an immutable admission under the [fixture-manifest
contract](../fixture-manifest/README.md) activates them.
