#!/usr/bin/env bash
set -euo pipefail

# Canonical test entrypoint for the disposable current-form surface preview.
# The repository-owned launcher selects and validates the pinned interpreter;
# this wrapper only provides a location-independent, friendly test command.

TEST_SCRIPT_DIR="$(dirname -- "${BASH_SOURCE[0]}")"
TEST_SCRIPT_DIR="$(CDPATH='' cd -P -- "$TEST_SCRIPT_DIR" && pwd)"
readonly TEST_SCRIPT_DIR
TEST_DIR="$TEST_SCRIPT_DIR/tests"
readonly TEST_DIR
REPOSITORY_ROOT="$(CDPATH='' cd -P -- "$TEST_SCRIPT_DIR/../.." && pwd)"
readonly REPOSITORY_ROOT
LAUNCHER="$TEST_SCRIPT_DIR/surface_preview_launcher.sh"
readonly LAUNCHER

usage() {
  printf 'Usage: %s [test*.py pattern]\n' "${BASH_SOURCE[0]}"
  printf '\n'
  printf 'Run the current-form surface-preview unittest suite through its pinned environment.\n'
  printf 'With one selector, run only matching test files (for example:\n'
  printf '  %s test_structural_gallery_evidence_probe.py\n' "${BASH_SOURCE[0]}"
}

error() {
  printf 'current-form-surface-preview-test: error: %s\n' "$*" >&2
  usage >&2
  exit 2
}

if [[ "$#" -gt 1 ]]; then
  error 'provide at most one test filename or unittest discovery pattern'
fi

if [[ "$#" -eq 1 ]]; then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    test*/*|"")
      error "selector '$1' must begin with 'test' and must not contain '/'; pass a test filename or discovery pattern"
      ;;
    test*)
      TEST_PATTERN="$1"
      ;;
    *)
      error "selector '$1' must begin with 'test' and must not contain '/'; pass a test filename or discovery pattern"
      ;;
  esac
else
  TEST_PATTERN='test*.py'
fi

if ! find "$TEST_DIR" -maxdepth 1 -type f -name "$TEST_PATTERN" -print -quit | grep -q .; then
  error "selector '$TEST_PATTERN' matched no test files"
fi

cd -- "$REPOSITORY_ROOT"
exec "$LAUNCHER" -m unittest discover -s "$TEST_DIR" -p "$TEST_PATTERN"
