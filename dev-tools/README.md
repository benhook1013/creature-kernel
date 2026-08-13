# Developer tools

This directory contains repository-local supporting tooling for documentation
validation, the Proposed Readiness 2 fixture preflight, and visual review.

## Entry points

- [Documentation validator](validation/validate_docs.py) checks the repository's
  lightweight documentation contracts; run it from the repository root with
  `python3 dev-tools/validation/validate_docs.py`.
- [Readiness 2 fixture preflight](fixture-preflight/README.md) checks internal
  consistency of the exact candidate manifest, schema, and nine listed files;
  run it with `python3 dev-tools/fixture-preflight/preflight.py . fixtures/body-documents/readiness-2/manifest.v1.json`. It does not admit
  Readiness 2.
- [Readiness 2 evidence generator](readiness-evidence/README.md) emits separate
  fixture, implementation, dependency, support-tool, and build-request
  identities; run it with `python3 dev-tools/readiness-evidence/evidence.py .`.
  It records evidence but cannot approve or activate the gate.
- [Visual-review gallery](visual-review/README.md) describes the localhost
  image-comparison tool and its publish/serve commands.

See the [visual-review README](visual-review/README.md) for its workflow and
the [validation README](validation/README.md) for its command.
