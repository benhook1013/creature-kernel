# EXP-0002 phase-one runner

This directory contains the standard-library Python runner for the frozen,
unrun phase-one corpus package. It is research tooling, not a production CLI
or profile selector.

`run_adapter.py` is the entrypoint. `runner_schema.py` loads the exact
manifest/corpus schema and performs hash, byte, ordering, relation,
disjointness, and preflight checks. `runner_oracle.py` independently computes
the exact decimal and scalar/translation Fraction/dyadic expectations.
`runner_transport.py` provides deadline-bounded JSONL subprocess I/O with
stdout/stderr caps, one-response enforcement, trailing-output rejection, and
safe cleanup. `runner_common.py` contains strict JSON and protocol helpers.

Run synthetic checks from the repository root:

```bash
python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/scripts \
  -p 'test*.py'
python3 -m py_compile experiments/EXP-0002-numeric-frame-profile/scripts/*.py
```

The CLI accepts a candidate command after `--`:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/scripts/run_adapter.py \
  --manifest experiments/EXP-0002-numeric-frame-profile/corpora/manifest.json \
  --output <new-result.json> -- <candidate command and arguments>
```

The candidate receives only the protocol ID, an opaque `wire_request_id`,
operation, and input. Runner-only case IDs, relations, expected values, and
oracle data are not projected. The output path is exclusive-create only and
must not alias an input or candidate executable. No command here has been run
against the frozen corpora.

The runner does not select a profile or produce an experiment outcome. It does
not implement quaternion, transform, basis, claim, snapshot, geometry, or R3
activation evidence.
