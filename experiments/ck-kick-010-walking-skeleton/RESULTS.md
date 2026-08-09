# CK-KICK-010 walking-skeleton evidence

Record type: unregistered exploratory implementation evidence

Date recorded: 2026-08-09

This is a durable textual record for the bounded CK-KICK-010 disposable host.
It is not an experiment registration, does not create `EXP-0001`, and does not
calculate a technology outcome. The generated bundles used for these
observations remain ephemeral under `/tmp/creature-kernel-ck010-evidence.eAdgPm`
and are intentionally not committed under the artifact policy. The hashes,
metrics, and results below are the durable record.

## Method

The implementation accepts the temporary JSON semantic fixture, resolves its
typed ownership tree, evaluates the disposable normalized implicit fields,
extracts a mesh with the disposable marching-cubes adapter, checks the mesh
and source-label channel, verifies the identity export landmark, and publishes
the complete bundle atomically. The invalid fixture is rejected during input
validation before field evaluation or meshing.

The valid run used the README defaults: `128^3` samples, `0.10 m` padding,
smooth-min `k=0.10`, and isovalue `0`. Two valid runs used distinct fresh output
targets. `diff -qr` found the complete five-file bundles byte-identical.

Environment used:

- Python 3.10.12; NumPy 2.2.6; scikit-image 0.25.2; trimesh 5.0.0; pytest
  9.1.1.
- WSL2 Linux 6.18.33.2-microsoft-standard-WSL2, x86_64; 12th Gen Intel Core
  i7-12700KF; WSL exposes 12 logical CPUs, 6 cores, 1 socket; 12,541,632,512
  bytes memory; CPU-only path with no GPU.

The README-style setup and reproduction commands are:

```bash
python3 -m venv /tmp/ck-kick-010-venv
. /tmp/ck-kick-010-venv/bin/activate
cd experiments/ck-kick-010-walking-skeleton
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q

mkdir -p /tmp/ck-kick-010-outputs
python -m ck_spike build \
  --input fixtures/valid.json \
  --output /tmp/ck-kick-010-outputs/valid-a
python -m ck_spike build \
  --input fixtures/valid.json \
  --output /tmp/ck-kick-010-outputs/valid-b
diff -qr /tmp/ck-kick-010-outputs/valid-a \
  /tmp/ck-kick-010-outputs/valid-b

python -m ck_spike build \
  --input fixtures/invalid-missing-right-shin.json \
  --output /tmp/ck-kick-010-outputs/invalid
```

For the first full valid run, `/usr/bin/time -v` observed wall time 3.76 s,
user time 21.30 s, system time 0.77 s, and maximum RSS 443,344 KB. This is one
local observation only, not a benchmark, budget, threshold, or comparative
performance claim.

## Observations

### Valid fixture

The command succeeded twice, each time publishing exactly
`diagnostics.json`, `manifest.json`, `mesh.ply`, `resolved_graph.json`, and
`semantic_regions.json`. The observed structural and semantic metrics were:

- 55,760 vertices; 111,516 faces; one connected component; watertight true;
  zero degenerate faces.
- All vertices, faces, and normals were finite and all face indices were
  valid. There were 55,760 winner-only attributions, and all 15 source labels
  were represented.
- Field minimum `-0.988276700176892`; field maximum `2.605293681316838`;
  domain-face minimum `0.16134049520826932`.
- Signed volume `3.021150985467879`; orientation alignment
  `0.9957994895398741`; export determinant `1`.
- The asymmetric `left_ear` source/export position was
  `[0.22, 2.55, 0.12]` and passed the identity-export check.

The identical valid-run artifact hashes were:

| Artifact | SHA-256 |
| --- | --- |
| `diagnostics.json` | `0cefee54f04a62bdd273a896ecab5a9dfb70da3b6b66f12eff0ce519b1b3896f` |
| `manifest.json` | `fed333fc4a76aceb6626989131ebfc2c5c39ce8d9debc91e3719f42b88c1e0b5` |
| `mesh.ply` | `ee2915bf65e8fc790ef8f052f79959f149ff5b54fd5b9cf9af863521b3dcb228` |
| `resolved_graph.json` | `84b4006ceb59759d64c5bb03f2b041ea6be51df723bd0a2879935e3b644f34c3` |
| `semantic_regions.json` | `c02f56113fea3af592b3cc8477396c6919e03c858b6053a8f05bfc04e09ec3db` |

### Invalid fixture

The missing-right-shin command exited `2` and published only
`diagnostics.json` and `manifest.json`. The primary diagnostic was
`MISSING_REQUIRED_MODULE`; no graph, mesh, or semantic-region artifact was
published. The observed hashes were:

| Artifact | SHA-256 |
| --- | --- |
| `diagnostics.json` | `cc3cc846d94ccba54f9811106cdf63d2633b9a50168b66abad68523191023c44` |
| `manifest.json` | `51e9b32c6206165d2229407942bd74fbe4f8a6c295a97bb3ae4cf662c34101bb` |

### Checks

The consolidated implementation checks recorded before this documentation
task were 34 tests passed in 1.30 s. Compileall passed. Documentation
validation and the scoped diff check passed for the integrated state.

## Limitations

This is one valid fixture in one current CPU-only environment, plus one
expected invalid fixture. The repeatability result is limited to same-host,
same-environment reruns of this disposable implementation. The bundles are
not retained as durable artifacts.

The slice does not establish visual quality, topology generality, morphology
variation, the four-profile Stage 1 gate, cross-platform determinism,
performance, memory budgets, rigging, collision, deformation, runtime
behaviour, engine integration, or production suitability. Winner-only source
labels are debug attribution, not durable semantic lineage, weighted
contribution, or a body-graph contract. The observed mesh is not evidence for
animation-ready topology or a production surface representation.

## Conclusion

The bounded CK-KICK-010 implementation provides an executable, reproducible
same-environment path for one fixture and the expected diagnostics-only gate
for the intentionally invalid fixture. It records implementation evidence,
not a Stage 1 result, formal experiment result, product acceptance, or
production architecture selection. It provides neither support nor reject
evidence for the parked DR-0009/DR-0010 proposals and does not reactivate or
register `EXP-0001`.

CK-KICK-010 is therefore implemented with evidence recorded, pending an
independent implementation review. After that bounded review, normal human
design discussion resumes at CK-KICK-012 unless review or evidence exposes a
specific need for CK-KICK-011.

## Follow-up

Complete the independent review of the implementation and this evidence
boundary. Preserve the disposable host and generated bundles as ephemeral;
retain this summary and the implementation's small source/fixture/test files.
