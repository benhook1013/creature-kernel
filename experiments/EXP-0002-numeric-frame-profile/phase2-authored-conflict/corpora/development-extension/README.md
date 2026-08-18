# EXP-0002 phase-two development extension

This package is a separate six-case development extension to the historical
16-case authored-conflict corpus. It runs each case against the strict, micro,
and stress development profiles: 18 requests total. The historical corpus and
its 48-request report remain unchanged.

The deterministic variant is a three-Part descendant path ending at
`tail_end`. Its authored transforms combine centimetre units, a left-handed
signed basis, and non-identity half-turn rotations. Each boundary/successor
pair varies the authored translation component at the strict, micro, or stress
threshold. The expected aggregate is 9 `agree` and 9 `conflict`.

`corpus.json` is the frozen, content-addressed case manifest. The companion
builder in `../../scripts/development_extension_corpus.py` materializes the
source documents and verifies their hashes. The extension runner uses the
independent exact-rational oracle in
`../../scripts/development_extension_oracle.py` to check the complete response
witness, including identity, provenance, descendant path, equation steps,
transforms, tolerances, providers, and classification.

The run is diagnostic and non-authoritative. A successful 18/18 candidate run
does not select a profile, create a held-out or adversarial corpus, or activate
Readiness 3. Evidence synthesis and profile selection remain deferred.

After building the phase-two candidate as described in the parent package,
run the extension from the repository root:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/run_development_extension.py \
  --candidate experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/target/debug/exp-0002-r3-authored-conflict-candidate
```

The command writes one bounded JSON report to standard output and exits
nonzero for failed or inconclusive evidence.
