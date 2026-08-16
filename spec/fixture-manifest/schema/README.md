# Fixture-manifest schema

Status: Proposed schema specification; exact Readiness 2 schema artifact
admitted and active within the recorded transaction.

`ck-fixture-manifest-v1.schema.json` defines the closed JSON encoding for the
Readiness 2 body-document fixture manifest. It covers field shape, constants,
local value constraints, and conditional primary-diagnostic presence. The
independent parser-preflight tool remains responsible for cross-record ID and
path uniqueness, profile-reference resolution, on-disk hash/path checks,
canonical payload binding, and implementation/dependency closure checks.
