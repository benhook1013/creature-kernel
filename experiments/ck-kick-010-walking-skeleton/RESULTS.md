# CK-KICK-010 walking-skeleton evidence

Record type: unregistered exploratory implementation evidence

Date recorded: 2026-08-09

This is a durable textual record for the bounded CK-KICK-010 disposable host.
It is not an experiment registration, does not create `EXP-0001`, and does not
calculate a technology outcome. The generated bundles used for these
observations remain ephemeral under
`/tmp/creature-kernel-ck010-final-evidence.F2WyjG/evidence` and are
intentionally not committed under the artifact policy. The hashes, metrics,
and results below are the durable record.

## Method

The implementation accepts the temporary JSON semantic fixture, resolves its
typed ownership tree, evaluates the disposable normalized implicit fields,
extracts a mesh with the disposable marching-cubes adapter, checks the mesh
and source-label channel, verifies the identity export landmark, and publishes
the complete bundle atomically. The invalid fixture is rejected during input
validation before field evaluation or meshing.

The preferred reproduction used the README defaults: `128^3` samples, `0.10 m`
padding, smooth-min `k=0.10`, and isovalue `0`. The disposable reproduction
tool ran valid-a, valid-b, invalid-a, and invalid-b into a fresh output root;
it checked the exact five-file and two-file inventories and found both pairs
byte-identical. All four manifests recorded source identity
`sha256:5664256e69ff5ec472e0ed6054c8978fb5e19e44684ccf20edd0a17f1b79d127`.

The preferred command, run from
`experiments/ck-kick-010-walking-skeleton`, was:

```bash
/tmp/creature-kernel-ck010.60GXUX/venv/bin/python tools/reproduce_evidence.py \
  --output-root /tmp/creature-kernel-ck010-final-evidence.F2WyjG/evidence
```

It exited `0`; the child builds exited `0`, `0`, `2`, and `2` respectively.

Environment used:

- Python 3.10.12; NumPy 2.2.6; scikit-image 0.25.2; trimesh 5.0.0; pytest
  9.1.1.
- WSL2 Linux 6.18.33.2-microsoft-standard-WSL2, x86_64; 12th Gen Intel Core
  i7-12700KF; WSL exposes 12 logical CPUs, 6 cores, 1 socket; 12,541,632,512
  bytes memory; CPU-only path with no GPU.

Dependency provenance and repeatability boundary:

- The exact evidence environment was `/tmp/creature-kernel-ck010.60GXUX/venv`.
  Its complete installed-package map was captured with
  `/tmp/creature-kernel-ck010.60GXUX/venv/bin/python -m pip list
  --format=freeze`:

  ```text
  exceptiongroup==1.3.1
  ImageIO==2.37.4
  iniconfig==2.3.0
  lazy-loader==0.5
  networkx==3.4.2
  numpy==2.2.6
  packaging==26.3
  pillow==12.3.0
  pip==22.0.2
  pluggy==1.6.0
  Pygments==2.20.0
  pytest==9.1.1
  scikit-image==0.25.2
  scipy==1.15.3
  setuptools==59.6.0
  tifffile==2025.5.10
  tomli==2.4.1
  trimesh==5.0.0
  typing_extensions==4.16.0
  ```

- `requirements.txt` pins the direct runtime dependencies only
  (`numpy`, `scikit-image`, and `trimesh`); `requirements-dev.txt` pins the
  direct test dependency (`pytest`). The other entries above are transitive
  packages or virtual-environment tooling. These files are direct version
  pins, not hash-locked requirements or a complete cross-platform environment
  lock. Installing those direct pins later is not claimed to reconstruct this
  complete environment indefinitely.
- The repeatability result below is byte repeatability in the exact recorded
  same-host environment, with matching source bytes, fixture, configuration,
  and seed. It is not a claim of cross-platform or indefinite reproducibility.

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

For the current timed valid observation, `/usr/bin/time -v` observed wall time
4.10 s, user time 21.46 s, system time 0.96 s, and maximum RSS 444,156 KB.
This is one local observation only, not a benchmark, budget, threshold, or
comparative performance claim.

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
- Export face-normal alignment minimum `0.5241767756364115`, mean
  `0.9984185578327188`, tolerance `0.05`; directed edge orientation mismatches
  `0`.
- The asymmetric `left_ear` source/export position was
  `[0.22, 2.55, 0.12]` and passed the identity-export check.

The identical valid-run artifact hashes were:

| Artifact | SHA-256 |
| --- | --- |
| `diagnostics.json` | `0cefee54f04a62bdd273a896ecab5a9dfb70da3b6b66f12eff0ce519b1b3896f` |
| `manifest.json` | `2b70724f637fe564ae8de2264691fa23f85f0be15b1f9c39d3623cf501111073` |
| `mesh.ply` | `ee2915bf65e8fc790ef8f052f79959f149ff5b54fd5b9cf9af863521b3dcb228` |
| `resolved_graph.json` | `84b4006ceb59759d64c5bb03f2b041ea6be51df723bd0a2879935e3b644f34c3` |
| `semantic_regions.json` | `c02f56113fea3af592b3cc8477396c6919e03c858b6053a8f05bfc04e09ec3db` |

### Invalid fixture

The missing-right-shin command exited `2` in both runs and published exactly
`diagnostics.json` and `manifest.json` in each output directory. The tool's
outputs were `/tmp/creature-kernel-ck010-final-evidence.F2WyjG/evidence/invalid-a`
and `invalid-b`. The primary diagnostic was `MISSING_REQUIRED_MODULE`; no
graph, mesh, or semantic-region artifact was published. Both inventories and
both files in the pair were byte-identical. The identical hashes were:

| Artifact | SHA-256 |
| --- | --- |
| `diagnostics.json` | `cc3cc846d94ccba54f9811106cdf63d2633b9a50168b66abad68523191023c44` |
| `manifest.json` | `6b16cf3b2b428483f485f428241dd315753eb13d9072c9c1b3016f18f63a8580` |

### Checks

The current consolidated implementation checks were 44 tests passed, with 8
subtests passed, in 3.34 s. Compileall passed. Documentation validation and
the scoped diff check passed for the integrated state.

## Independent implementation review

Review level: Single. Review status: completed with findings dispositioned, not
clean. The fresh independent implementation review identified five substantive
actionable items plus trailing whitespace:

1. Blocking aggregate-only orientation gate: added the per-face area-weighted
   normal tolerance `0.05`, directed-edge consistency checking, and a face
   reversal regression test.
2. Nonblocking huge-number diagnostic escape: added structured overflow
   diagnostics.
3. Staged symlink/special-file acceptance: added `lstat`/non-regular rejection
   and tests.
4. Missing second invalid rerun: ran and byte-compared two invalid bundles.
5. Incomplete transitive dependency provenance: recorded the full 19-package
   map and narrowed the repeatability language.
6. Trailing whitespace: fixed.

Main consolidated validation passed after these corrections. This records the
dispositions and implementation evidence; it does not claim that the
reviewer approved the fixes. No second review or review-until-clean pass was
run.

## Limitations

This is one valid fixture in one current CPU-only environment, plus one
expected invalid fixture, each run twice. The repeatability result is limited
to byte-identical reruns in the exact recorded same-host environment of this
disposable implementation. The committed reproduction helper is durable but
explicitly disposable, nonproduction tooling. Only the generated bundles
under `/tmp` are ephemeral and unretained as durable artifacts.

The slice does not establish visual quality, topology generality, morphology
variation, the four-profile Stage 1 gate, cross-platform determinism,
performance, memory budgets, rigging, collision, deformation, runtime
behaviour, engine integration, or production suitability. Winner-only source
labels are debug attribution, not durable semantic lineage, weighted
contribution, or a body-graph contract. The observed mesh is not evidence for
animation-ready topology or a production surface representation.

## Conclusion

The bounded CK-KICK-010 implementation provides an executable, byte-repeatable
same-environment path for one fixture and the expected diagnostics-only gate
for the intentionally invalid fixture. It records implementation evidence,
not a Stage 1 result, formal experiment result, product acceptance, or
production architecture/tool selection. The reproduction helper is
disposable experiment tooling, not a production or formal-experiment runner.
It provides neither support nor reject evidence for the parked DR-0009/DR-0010
proposals and does not reactivate or register `EXP-0001`.

CK-KICK-010 is therefore implemented with evidence recorded and its Single
independent implementation review completed with findings dispositioned, not
clean. Normal human design discussion resumes at CK-KICK-012 unless review or
evidence exposes a specific need for CK-KICK-011.

## Follow-up

Preserve the completed review disposition and evidence boundary. The helper is
durable source but remains disposable/nonproduction tooling; generated bundles
under `/tmp` remain ephemeral. Retain this summary and the implementation's
source, fixture, and test files.
