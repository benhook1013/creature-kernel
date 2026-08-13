# Fixture manifest preflight

`preflight.py` is an internal Readiness 2 consistency check. It accepts a
repository root and a manifest path relative to that root:

```text
python3 dev-tools/fixture-preflight/preflight.py REPOSITORY_ROOT path/to/manifest.json
```

The tool uses only the Python standard library. It pins the exact Readiness 2
suite ID, body-schema path, nine fixture IDs, diagnostic registry, and resource
profiles. It rejects malformed or ambiguous JSON, unsafe paths, symlinks,
special files, hardlinked regular files, unsupported modes, inconsistent
hashes, unresolved profiles, and resource-limit expectations that do not agree
with the selected source-byte profile. It emits deterministic JSON containing
the manifest SHA-256 and the `ck.path-set.raw.v1` ordered raw
path/mode/content binding. The independent Rust tests validate the manifest
against the committed Draft 2020-12 manifest schema; this dependency-free tool
enforces the same candidate field/profile invariants directly.

This is internal consistency evidence only. It does not parse fixture body
documents, validate their semantics, admit a corpus, or claim that expected
statuses and diagnostics are correct.
