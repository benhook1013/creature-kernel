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
  printf 'Usage: %s [test*.py pattern [test method pattern]]\n' "${BASH_SOURCE[0]}"
  printf '\n'
  printf 'Run the current-form surface-preview unittest suite through its pinned environment.\n'
  printf 'With one selector, run only matching test files (for example):\n'
  printf '  %s test_structural_gallery_evidence_probe.py\n' "${BASH_SOURCE[0]}"
  printf 'With two selectors, also filter methods during focused development (for example):\n'
  printf '  %s test_successor_surface_preview.py test_shoulder\n' "${BASH_SOURCE[0]}"
}

error() {
  printf 'current-form-surface-preview-test: error: %s\n' "$*" >&2
  usage >&2
  exit 2
}

if [[ "$#" -gt 2 ]]; then
  error 'provide at most one test filename pattern and one test method pattern'
fi

if [[ "$#" -ge 1 ]]; then
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

METHOD_PATTERN="${2:-}"
if [[ -n "$METHOD_PATTERN" && "$METHOD_PATTERN" != test* ]]; then
  error "method selector '$METHOD_PATTERN' must begin with 'test'"
fi

if ! find "$TEST_DIR" -maxdepth 1 -type f -name "$TEST_PATTERN" -print -quit | grep -q .; then
  error "selector '$TEST_PATTERN' matched no test files"
fi

cd -- "$REPOSITORY_ROOT"
if [[ -n "$METHOD_PATTERN" ]]; then
  TEST_OUTPUT_FILE="$(mktemp)"
  trap 'rm -f -- "$TEST_OUTPUT_FILE"' EXIT
  set +e
  "$LAUNCHER" -m unittest discover -v -s "$TEST_DIR" -p "$TEST_PATTERN" -k "$METHOD_PATTERN" 2>&1 | tee "$TEST_OUTPUT_FILE"
  PIPELINE_STATUS=("${PIPESTATUS[@]}")
  TEST_STATUS="${PIPELINE_STATUS[0]}"
  TEE_STATUS="${PIPELINE_STATUS[1]}"
  set -e
  if grep -q '^Ran 0 tests' "$TEST_OUTPUT_FILE"; then
    error "method selector '$METHOD_PATTERN' matched no tests in '$TEST_PATTERN'"
  fi
  if [[ "$TEST_STATUS" -ne 0 ]]; then
    exit "$TEST_STATUS"
  fi
  if [[ "$TEE_STATUS" -ne 0 ]]; then
    error "tee failed with status $TEE_STATUS"
  fi
  exit 0
fi
exec "$LAUNCHER" -m unittest discover -v -s "$TEST_DIR" -p "$TEST_PATTERN"
