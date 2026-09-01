#!/usr/bin/env bash
set -euo pipefail

# Purpose-named entrypoint for the disposable current-form surface preview.
# It selects and checks an already-created Python environment, normalizes the
# temporary-root environment for WSL, and then passes every caller argument to
# Python unchanged. It never creates an environment or installs packages.

LAUNCHER_DIR="$(dirname -- "${BASH_SOURCE[0]}")"
LAUNCHER_DIR="$(CDPATH='' cd -P -- "$LAUNCHER_DIR" && pwd)"
readonly LAUNCHER_DIR
REQUIREMENTS_FILE="$LAUNCHER_DIR/requirements.txt"
readonly REQUIREMENTS_FILE

error() {
  printf 'surface-preview-launcher: error: %s\n' "$*" >&2
  exit 2
}

warning() {
  printf 'surface-preview-launcher: warning: %s\n' "$*" >&2
}

native_linux_path() {
  local candidate="$1"
  local resolved parent filesystem_type

  [[ "$(uname -s)" == Linux ]] || return 1
  [[ "$candidate" == /* ]] || return 1
  resolved="$(realpath -m -- "$candidate" 2>/dev/null)" || return 1
  while [[ ! -e "$resolved" ]]; do
    parent="${resolved%/*}"
    [[ -n "$parent" ]] || parent="/"
    [[ "$parent" != "$resolved" ]] || break
    resolved="$parent"
  done
  filesystem_type="$(df -P -T -- "$resolved" 2>/dev/null | awk 'NR == 2 { print $2; exit }')"
  [[ -n "$filesystem_type" ]] || return 1

  case "$filesystem_type" in
    9p|drvfs|fuseblk|cifs|smb|smb2|smb3|ntfs|ntfs3|vfat|exfat|fat|fat32)
      return 1
      ;;
  esac
}

native_writable_directory() {
  [[ -d "$1" && -w "$1" ]] || return 1
  native_linux_path "$1"
}

default_python_path() {
  local cache_root

  if [[ -n "${XDG_CACHE_HOME:-}" ]] && native_linux_path "$XDG_CACHE_HOME"; then
    printf '%s\n' "$XDG_CACHE_HOME/creature-kernel/current-form-surface-venv/bin/python"
    return
  fi
  if [[ -n "${HOME:-}" ]] && native_linux_path "$HOME"; then
    printf '%s\n' "$HOME/.cache/creature-kernel/current-form-surface-venv/bin/python"
    return
  fi

  # This fallback is still native Linux and matches the historical disposable
  # environment documented for this experiment.
  cache_root=/tmp
  printf '%s\n' "$cache_root/ck-current-form-surface-venv/bin/python"
}

resolve_python() {
  local requested="$1"
  local resolved

  if [[ "$requested" == */* ]]; then
    resolved="$requested"
  else
    resolved="$(command -v -- "$requested" 2>/dev/null || true)"
  fi
  [[ -n "$resolved" && -x "$resolved" ]] || error "Python interpreter '$requested' was not found or is not executable. Create the pinned cache environment with the commands in experiments/current-form-surface-preview/README.md under 'Run', or set CK_CURRENT_FORM_SURFACE_PYTHON to an existing Linux interpreter with the pinned requirements installed; do not fall back to bare system Python."
  native_linux_path "$resolved" || error "Python interpreter '$resolved' is not on a native Linux filesystem. Set CK_CURRENT_FORM_SURFACE_PYTHON to a Linux-side interpreter."
  printf '%s\n' "$resolved"
}

select_temp_root() {
  local variable value

  if [[ -n "${CK_CURRENT_FORM_SURFACE_TMPDIR:-}" ]]; then
    native_writable_directory "$CK_CURRENT_FORM_SURFACE_TMPDIR" || error "CK_CURRENT_FORM_SURFACE_TMPDIR must name an existing writable directory on a native Linux filesystem (for example /tmp or /home/...); refusing '$CK_CURRENT_FORM_SURFACE_TMPDIR'."
    printf '%s\n' "$CK_CURRENT_FORM_SURFACE_TMPDIR"
    return
  fi

  # Match Python's normal TMPDIR, TEMP, TMP precedence, but discard inherited
  # Windows/DrvFS values instead of allowing tempfile to select them.
  for variable in TMPDIR TEMP TMP; do
    value="${!variable:-}"
    [[ -n "$value" ]] || continue
    if native_writable_directory "$value"; then
      printf '%s\n' "$value"
      return
    fi
    # Windows commonly exports these paths into WSL. They are expected host
    # noise, not a caller mistake; the native /tmp fallback below is the
    # documented route and does not need a warning on every invocation.
    if [[ "$value" == /mnt/?/* ]]; then
      continue
    fi
    warning "ignoring $variable=$value because it is not an existing writable native Linux directory"
  done

  native_writable_directory /tmp || error "the native Linux default temporary root /tmp is unavailable or not writable; set CK_CURRENT_FORM_SURFACE_TMPDIR to an existing writable native Linux directory."
  printf '%s\n' /tmp
}

PYTHON_REQUESTED="${CK_CURRENT_FORM_SURFACE_PYTHON:-$(default_python_path)}"
PYTHON="$(resolve_python "$PYTHON_REQUESTED")"
TEMP_ROOT="$(select_temp_root)"
export TMPDIR="$TEMP_ROOT"
export TEMP="$TEMP_ROOT"
export TMP="$TEMP_ROOT"
export PYTHONDONTWRITEBYTECODE=1

"$PYTHON" - "$REQUIREMENTS_FILE" <<'PY'
import importlib
import importlib.metadata
import pathlib
import sys

requirements_path = pathlib.Path(sys.argv[1])
import_names = {
    "scikit-image": "skimage",
    "Pillow": "PIL",
}
failures = []

try:
    requirement_lines = requirements_path.read_text(encoding="utf-8").splitlines()
except OSError as exc:
    print(f"surface-preview-launcher: unable to read pinned requirements {requirements_path}: {exc}", file=sys.stderr)
    raise SystemExit(1)

for line_number, raw_line in enumerate(requirement_lines, start=1):
    line = raw_line.split("#", 1)[0].strip()
    if not line:
        continue
    if "==" not in line:
        failures.append(f"{requirements_path}:{line_number}: expected a pinned package (name==version), got {raw_line!r}")
        continue
    distribution, expected_version = (part.strip() for part in line.split("==", 1))
    module_name = import_names.get(distribution, distribution.replace("-", "_"))
    try:
        installed_version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        failures.append(f"{distribution}=={expected_version} is not installed")
        continue
    if installed_version != expected_version:
        failures.append(f"{distribution}=={expected_version} is required, but {installed_version} is installed")
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        failures.append(f"import {module_name!r} failed for {distribution}: {exc}")

if failures:
    print("surface-preview-launcher: Python preflight failed:", file=sys.stderr)
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    print(f"  interpreter: {sys.executable}", file=sys.stderr)
    print(f"  requirements: {requirements_path}", file=sys.stderr)
    print("  install explicitly with: <interpreter> -m pip install -r experiments/current-form-surface-preview/requirements.txt", file=sys.stderr)
    raise SystemExit(1)
PY

exec "$PYTHON" "$@"
