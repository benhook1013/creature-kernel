# Developer tools

This directory contains repository-local supporting tooling for documentation
validation and visual review.

## Entry points

- [Documentation validator](validation/validate_docs.py) checks the repository's
  lightweight documentation contracts; run it from the repository root with
  `python3 dev-tools/validation/validate_docs.py`.
- [Visual-review gallery](visual-review/README.md) describes the localhost
  image-comparison tool and its publish/serve commands.

See the [visual-review README](visual-review/README.md) for its workflow and
the [validation README](validation/README.md) for its command.
