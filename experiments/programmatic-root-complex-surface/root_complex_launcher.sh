#!/usr/bin/env bash
set -euo pipefail

LAUNCHER_DIR="$(CDPATH='' cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly LAUNCHER_DIR
readonly PREVIEW_LAUNCHER="$LAUNCHER_DIR/../current-form-surface-preview/surface_preview_launcher.sh"

if [[ ! -e "$PREVIEW_LAUNCHER" ]]; then
  printf 'root_complex_launcher: required sibling launcher is missing: %s\n' \
    "$PREVIEW_LAUNCHER" >&2
  exit 1
fi
if [[ ! -f "$PREVIEW_LAUNCHER" || ! -x "$PREVIEW_LAUNCHER" ]]; then
  printf 'root_complex_launcher: required sibling launcher is not executable: %s\n' \
    "$PREVIEW_LAUNCHER" >&2
  exit 1
fi

exec "$PREVIEW_LAUNCHER" "$@"
