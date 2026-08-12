# Build operation and derived-output contract

Status: Proposed contract; CK-KICK-012 Batch 9 discussion-approved canonical
owner. This document is not an accepted format and does not activate a build
implementation, serializer, fixture corpus, or artifact store.

This document is the canonical Proposed owner of the public `build` operation
and its derived-output/publication contract. The [body-document contract](../body-document/README.md)
owns source admission, resolution phases, resolver statuses, diagnostics, and
the in-memory resolved-snapshot handoff. [DR-0006](../../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md)
owns durable semantic identity and the separation of build and artifact
identity. [DR-0013](../../docs/decisions/DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
owns the Proposed platform boundary and activation gates. This contract does
not choose final avatar-package serialization, field spellings, hash
algorithms, transport, or a permanent geometry backend.

The words **must**, **must not**, and **may** state this Proposed contract. The
exact serialized syntax and concrete filesystem encoding remain deferred; the
conceptual target and lifecycle rules below are normative within the proposal.

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

## Identity and manifest lifecycle

Build and artifact identity are distinct. A build/operation identity exists for
every invocation, including failure. Artifact identity is committed only after
successful publication. The staged manifest carries a **candidate artifact
identity**: it is a non-authoritative proposal used to name and validate the
staged result, not proof that an artifact has been published. Successful atomic
publication promotes that same candidate identity to the committed artifact
identity; publication does not mint a replacement identity.

The manifest is written last within immutable, invocation-owned, build-scoped
sibling staging. Its conceptual fields are:

| Field group | Proposed contents |
| --- | --- |
| Build lineage | build/operation identity, source/dependency/configuration/seed lineage, and contract/profile revisions |
| Candidate identity | non-authoritative candidate artifact identity and its identity revision |
| Outputs | relative output paths, expected sizes, hashes, and output roles |
| Integrity | manifest revision, completeness, and the data needed to verify one build lineage |
| Diagnostics | top-level status, primary/root diagnostic reference, completeness, and any trusted failure-bundle marker |

Exact member names, hash algorithm, byte encoding, and manifest serialization
are deferred. The manifest must be complete and internally consistent before
publication is attempted. Consumers must reject absolute or traversal paths,
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
adopted, or repaired in place. If the required atomic no-replace primitive is
unavailable, the operation fails closed as `output-failure`; it must not use an
adoption, delete-then-rename, or overwrite workaround.

Cleanup is limited to invocation-owned staging. An existing target and an
unrelated directory are never cleanup targets.

## Inspection and lineage

Artifact inspection is a separate read operation, not a second build-status
channel. Callers must provide the expected build and artifact lineage (and any
required contract/profile identity). Inspection verifies that expectation
against the target's committed manifest, identity, paths, hashes, sizes, and
completeness. It must report an explicit mismatch, stale, absent, or
unverifiable result; it must never guess that an occupant belongs to the
requested build or silently treat stale output as current. Exact read-operation
syntax remains deferred.

## Failure-bundle trust boundary

A compile or geometry failure may produce a diagnostics-only failure bundle
when publication succeeds. That bundle is trusted only when the publisher and
diagnostic reporter remain independently trusted from the failed component and
the manifest identifies the failed operation, root diagnostic, lineage, and
completeness. If the publisher/reporter is the failed component, shares its
lost trust, or cannot establish that separation, no diagnostics-only artifact
may be treated as trusted; the caller receives only the reserved CLI/API
failure envelope. Publication failure likewise returns the authoritative
envelope and cannot promise to publish its own failure bundle.

Failure-bundle publication does not turn a failed semantic resolution into a
successful snapshot. It is a derived diagnostic output with its own candidate
identity and publication checks.

## Operation outcome matrix

The following matrix is the complete Proposed outcome boundary. “No final
artifact” means the authoritative envelope is still returned; it does not mean
the process may discard the root diagnostic.

| Condition | Top-level outcome | Snapshot / publication consequence |
| --- | --- | --- |
| Source unavailable, unreadable, or incomplete before complete acquisition | `input-failure` | No resolver snapshot; no final artifact |
| Supplied bytes fail UTF-8, strict JSON, discriminator, schema, source semantic, or source invariant checks | `invalid-source` | No successful resolver snapshot; a trusted diagnostics-only bundle is optional |
| Unknown family/revision, unsupported required extension, or recognized unsupported assembly/capability | `unsupported` | No successful resolver snapshot; a trusted diagnostics-only bundle is optional |
| Required authored dependency cannot be acquired, verified, or matched to its declared revision | `dependency-failure` | No successful resolver snapshot; a trusted diagnostics-only bundle is optional |
| Configured source, dependency, graph, work, memory, or diagnostic/resource bound prevents required processing or trusted completion | `resource-limit` | No trusted successful snapshot; a diagnostics-only failure bundle is permitted only across an independent trusted reporter/publisher boundary, otherwise no final artifact; retain the root/resource diagnostic |
| Implementation, environment, worker, publisher, or invariant trust is lost | `internal-failure` | No trusted successful snapshot or final artifact; do not manufacture a failure bundle |
| Required build capability is explicitly unsupported, or required worker protocol/version negotiation cannot be satisfied as an unsupported contract | `unsupported` | No derived artifact; retain the capability/protocol diagnostic |
| Worker timeout or worker-reported resource exhaustion within the configured bound | `resource-limit` | No trusted output from that worker; a failure bundle is allowed only across an independent trust boundary |
| Worker crash or protocol corruption that loses trust in the operation | `internal-failure` | No trusted failure artifact; return the reserved envelope |
| Worker/geometry output is malformed, incomplete, out of contract, or fails output validation while the reporter remains trusted | `output-failure` | No success artifact; a trusted diagnostics-only bundle may be staged |
| A source-caused resolved-graph invariant fails | `invalid-source` | No successful in-memory snapshot or success artifact |
| An admissible resolved value/transform violates an implementation invariant during derivation | `internal-failure` | No trusted output; no failure bundle unless an independent reporter remains trusted |
| Derived output encoding/serialization fails while result trust is retained | `output-failure` | No final artifact; a trusted failure bundle may be attempted |
| Staging allocation, path, write, manifest, hash, or completeness validation fails while result trust is retained | `output-failure` | No final artifact; clean only invocation-owned staging |
| Target occupant has different, incomplete, stale, or unverifiable identity/lineage/hashes | `output-failure` (`target-conflict`) | Never overwrite or adopt the occupant; no final artifact |
| Atomic no-replace publication is unavailable or atomic publication fails | `output-failure` | Never fall back to overwrite/adoption; no final artifact |
| Atomic publication succeeds for a new target | `success` | The candidate identity is promoted to the committed artifact identity |
| Existing target verifies identical identity, lineage, complete manifest, and hashes | `success` (`already-published`) | Idempotent success; no replacement and the same identity is committed |
| Inspection receives an expected lineage and verifies a matching committed target | `success` | Inspection returns the verified artifact; it does not rebuild or guess |
| Inspection finds absent, stale, mismatched, incomplete, or unverifiable output | Explicit non-success inspection result, with mismatch/stale diagnostic | Never report the output as current; exact read-operation spelling remains deferred |

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
preservation, and trusted versus untrusted diagnostics-only bundles before a
public implementation claim is made.
