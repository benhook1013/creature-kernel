# EXP-0002 phase-one attempt-001

This is the human-readable index for the completed phase-one evidence. The
immutable raw records are [result.json](results/phase1/d88f5eca3ad3c0c0cb00dcf7dd012471be979305/attempt-001/result.json)
and [receipt.json](results/phase1/d88f5eca3ad3c0c0cb00dcf7dd012471be979305/attempt-001/receipt.json).

## Attempt identity

- Evaluation binding: `ck.exp-0002.phase1-persistent-conformance-v1`
- Source commit: `d88f5eca3ad3c0c0cb00dcf7dd012471be979305`
- Attempt: `attempt-001`
- Result SHA-256: `b8cf96fb7ef4f9387f0f0be086cf053d36f0d4a474ee8fe8ebf2dcab111a671a`
- Receipt SHA-256: `f4793d6f64f8030750a281702ba400c75429b17c9aa4eb99dfc8821e3f9c3a2a`
- Candidate SHA-256: `c96181b8f23bdb78d82751359831601aabd109c8702b00be0b3873d779113558`
- Manifest SHA-256: `ea05ece0de84bc6d2250abb2bfca39ee913ef87cdcdd915bde0fde324ba17440`

## Recorded outcome

The wrapper receipt records `completed-evidence`, `failure: null`, one
authoritative runner invocation, and runner exit `0`. The result records
`run_status: complete`, `evidence_status: passed`, `profile_binding: null`,
and `technology_result: none`.

All 49 cases and 26 registered relations passed:

| Corpus | Passed |
| --- | ---: |
| Development | 10/10 |
| Held-out | 13/13 |
| Adversarial | 26/26 |
| Total cases | 49/49 |
| Registered relations | 26/26 |

The raw receipt records clean wrapper source checkpoints at the same source
commit. The raw result records runner-side observational identity as
dirty/untracked at that commit. An independently reviewed explanation is the
pre-created empty untracked attempt directory plus differing Git probes, but
the artifacts do not directly encode or prove causation. The audit found no
evidence of source mutation or inadmissibility.

## Boundary

This is evidence for the identified candidate and runner on the frozen
phase-one cases and registered relation classifications only. It does not
select a production profile, activate Readiness 3, or establish portability,
repeatability, role isolation, order independence, broad generalization, or a
production-domain claim. Quaternion, later transform/basis, composition,
claim-identity, authored/snapshot, adapter-tier, runtime, and other broader
experiment obligations remain outside this result.

Overall EXP-0002 remains `planned` with `open` evidence closure and technology
outcome `none`, because the broader experiment obligations remain incomplete.
