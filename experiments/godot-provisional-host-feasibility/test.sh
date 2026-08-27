#!/usr/bin/env bash
set -euo pipefail

# Canonical test entrypoint for the disposable provisional Godot host probes.
# The current-form launcher selects and validates the pinned Python
# environment; this wrapper only provides local discovery and a friendly
# command without changing the caller's environment.

TEST_SCRIPT_DIR="$(dirname -- "${BASH_SOURCE[0]}")"
TEST_SCRIPT_DIR="$(CDPATH='' cd -P -- "$TEST_SCRIPT_DIR" && pwd)"
readonly TEST_SCRIPT_DIR
REPOSITORY_ROOT="$(CDPATH='' cd -P -- "$TEST_SCRIPT_DIR/../.." && pwd)"
readonly REPOSITORY_ROOT
TEST_DIR="$TEST_SCRIPT_DIR"
readonly TEST_DIR
LAUNCHER="$REPOSITORY_ROOT/experiments/current-form-surface-preview/surface_preview_launcher.sh"
readonly LAUNCHER

usage() {
  printf 'Usage: %s [test*.py pattern]\n' "${BASH_SOURCE[0]}"
  printf '\n'
  printf 'Run the provisional Godot host unittest suite through the pinned current-form Python environment.\n'
  printf 'With one selector, run only matching local test files (for example:\n'
  printf '  %s test_structural_gallery_smoke.py\n' "${BASH_SOURCE[0]}"
}

error() {
  printf 'godot-provisional-host-feasibility-test: error: %s\n' "$*" >&2
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
      error "selector '$1' must begin with 'test' and must not contain '/'; pass a local test filename or discovery pattern"
      ;;
    test*)
      TEST_PATTERN="$1"
      ;;
    *)
      error "selector '$1' must begin with 'test' and must not contain '/'; pass a local test filename or discovery pattern"
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
