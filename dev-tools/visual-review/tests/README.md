# Visual-review tests

The [test module](test_visual_review.py) contains focused tests for the local
visual-review publisher and server, including session and response handling.

For the tool's supported workflow and commands, see the parent
[visual-review README](../README.md).

`test_provisional_form_publication.py` covers the shell-free bounded
`inspect-provisional-form` adapter, strict envelope/variant/shape validation,
immutable collision behavior, timeout/output/nonzero failures, and the
existing localhost API route for a `provisional-form` session.
