# Readiness 2 body-document fixtures

Status: Proposed candidate corpus; not admitted or activated.

These nine source files are the lean structural Readiness 2 cases: a minimal
valid envelope, absent optional module, duplicate member, malformed
discriminator, unsupported revision, unknown core member, unsupported required
extension, opaque optional extension, and a compact resource-limit input.
The duplicate-member case is intentionally not valid JSON under strict
duplicate-preserving admission. The adjacent `manifest.v1.json` supplies the
exact hashes, profiles, expected statuses, diagnostics, provenance, and
external path-set framing. Its presence does not self-admit this corpus;
admission remains a separate reviewed human decision.
