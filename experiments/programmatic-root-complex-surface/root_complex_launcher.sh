#!/usr/bin/env bash
set -euo pipefail

readonly LAUNCHER_DIR="$(CDPATH='' cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$LAUNCHER_DIR/../current-form-surface-preview/surface_preview_launcher.sh" "$@"
