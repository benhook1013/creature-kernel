# Development profile sweep

`development-sweep.json` is a small, deterministic, non-activating definition
for the EXP-0002 authored-conflict successor. It records development constants
only; it is not a production comparison profile and does not select one. The
three candidate records are ordered `strict`, `micro`, `stress`, and each
constant carries both its exact binary64 bits and its exact decimal spelling.
The comparison mode is `semantic-exact-dyadic-tolerance`: binary64 inputs are
represented by exact dyadic values and compared using the declared A/R/H
tolerance predicates, not by asserting bitwise equality of transforms.

The definition is deliberately closed. Its `schema`, `sweep_id`, and
`definition_id` identify the sweep definition, while each ordered candidate
has its own exact bindable `profile_id` and `profile_role` identifies the
development-only purpose. `selected_profile_id` is explicitly `null` and
`r3_activation` is explicitly `inactive`. This package makes no resolver or
Readiness 3 activation claim; a later admission transaction must bind any
production profile and content digest separately. The definition does not
contain a digest of itself.

## Scope and regeneration

The constants are the exact development candidates supplied for this bounded
successor slice:

- `strict`: A `0x3cf0000000000000`; R/H `0x3d10000000000000`.
- `micro`: A/H `0x3eb0000000000000`; R `0x3d70000000000000`.
- `stress`: A `0x3f50000000000000`; R `0x3df0000000000000`; H `0x3f30000000000000`.

This is an authored fixture, not generated output. If a successor definition
is ever regenerated, derive decimal spellings from the authoritative bits with
the standard-library `struct`/`float` conversion, inspect the resulting diff,
and run the validator below. For example, the derivation check is:

```bash
python3 - <<'PY'
import struct
for bits in ("3cf0000000000000", "3d10000000000000"):
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    print("0x" + bits, repr(value))
PY
```

Do not add defaults, repair values, or bind a digest inside the definition; a
later manifest owns content identity.

## Validation

The bounded loader rejects duplicate JSON keys, non-finite or negative values,
unknown or missing fields, wrong candidate order, bit/decimal disagreement,
extra records, oversized files, and malformed JSON with stable failure codes.
Object member order is immaterial; candidate array order is contractual.

From the repository root:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/profile_sweep.py
python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts \
  -p 'test_profile_sweep.py'
python3 -m py_compile \
  experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/profile_sweep.py \
  experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/test_profile_sweep.py
```

The loader is standard-library-only and is intended to become the runner's
bounded input boundary. It validates the supplied record as-is and performs no
profile selection or R3 activation.
