#!/usr/bin/env bash
set -euo pipefail
EXPECTED_CONTRACT_SHA256="3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490" EXPECTED_SOURCE_SHA256="82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14" EXPECTED_PROFILE_SHA256="a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
SCRIPT_DIR="$(CDPATH='' cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR"; REPO_ROOT="$(CDPATH='' cd -P -- "$PACKAGE_DIR/../.." && pwd)"
CURRENT_LAUNCHER="$REPO_ROOT/experiments/current-form-surface-preview/surface_preview_launcher.sh"; CONTRACT="$PACKAGE_DIR/design-contract.md"; SIDECAR="$PACKAGE_DIR/design-contract.sha256"
SOURCE="$REPO_ROOT/examples/body-documents/stylized-digitigrade-biped-authored-form.json"; PROFILE="$REPO_ROOT/experiments/current-form-surface-preview/structural_profile_candidates.json"; REQUIREMENTS="$REPO_ROOT/experiments/current-form-surface-preview/requirements.txt"; BUILDER_ROLE="experiments/owned-root-assembly-successor/build_owned_root.py"; COMPARATOR_ROLE="experiments/owned-root-assembly-successor/compare_two_seed_outputs.py"
OUTPUT=""; STAGING=""
error() { printf 'owned-root-launcher: error: %s\n' "$*">&2; exit 1; }
cleanup() { [[ -n "$STAGING" && -d "$STAGING" && ! -L "$STAGING" ]] || return 0; rm -rf -- "$STAGING"; }
finish() { local status=$?; trap - EXIT; cleanup || status=1; (( status == 0 )) || exit 1; }
trap finish EXIT; trap 'exit 1' HUP INT TERM
[[ "${PYTHONHASHSEED-}" == 0 ]] || error "public invocation requires literal PYTHONHASHSEED=0"
[[ $# == 2 && $1 == --output ]] || error "usage: PYTHONHASHSEED=0 owned_root_launcher.sh --output ABSENT_PATH"
OUTPUT="$2"; [[ "$OUTPUT" == /* && "$(realpath -m -- "$OUTPUT")" == "$OUTPUT" ]] || error "--output requires a canonical absolute path"
[[ ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || error "--output must name an absent path"; OUTPUT_PARENT="$(dirname -- "$OUTPUT")"
[[ -d "$OUTPUT_PARENT" && -w "$OUTPUT_PARENT" ]] || error "output parent must be an existing writable directory"
case "$(df -P -T -- "$OUTPUT_PARENT" 2>/dev/null | awk 'NR == 2 { print $2; exit }')" in ""|9p|drvfs|fuseblk|cifs|smb|smb2|smb3|ntfs|ntfs3|vfat|exfat|fat|fat32) error "output parent must be native Linux storage";; esac
for fixed in "$CONTRACT" "$SIDECAR" "$SOURCE" "$PROFILE" "$REQUIREMENTS" "$CURRENT_LAUNCHER"; do [[ -f "$fixed" && ! -L "$fixed" ]] || error "fixed path is not a regular non-symlink file: $fixed"; done
sha256sum -- "$CONTRACT" | awk -v expected="$EXPECTED_CONTRACT_SHA256" '$1 != expected { exit 1 }' || error "design-contract SHA-256 mismatch"
cmp -s <(printf '%s  experiments/owned-root-assembly-successor/design-contract.md\n' "$EXPECTED_CONTRACT_SHA256") "$SIDECAR" || error "design-contract sidecar mismatch"
sha256sum -- "$SOURCE" | awk -v expected="$EXPECTED_SOURCE_SHA256" '$1 != expected { exit 1 }' || error "source SHA-256 mismatch"
sha256sum -- "$PROFILE" | awk -v expected="$EXPECTED_PROFILE_SHA256" '$1 != expected { exit 1 }' || error "profile-table SHA-256 mismatch"
cmp -s <(printf 'numpy==2.2.6\nscikit-image==0.25.2\nPillow==11.1.0\n') "$REQUIREMENTS" || error "requirements are not the exact pinned file"
PYTHONHASHSEED=0 "$CURRENT_LAUNCHER" - <<'PY'
import importlib, importlib.metadata, importlib.util, platform, sys
if (platform.python_implementation(), platform.python_version(), platform.system(), getattr(sys.implementation, "cache_tag", None)) != ("CPython", "3.10.12", "Linux", "cpython-310"): raise SystemExit("owned-root-launcher: runtime is not the pinned CPython 3.10.12 Linux form")
for name, expected in (("imageio", "2.37.4"), ("lazy-loader", "0.5"), ("networkx", "3.4.2"), ("numpy", "2.2.6"), ("packaging", "26.3"), ("pillow", "11.1.0"), ("scikit-image", "0.25.2"), ("scipy", "1.15.3"), ("tifffile", "2025.5.10")):
    if importlib.metadata.version(name) != expected: raise SystemExit(f"owned-root-launcher: runtime distribution drift: {name}")
if not all((getattr(module := importlib.import_module(name), "__file__", None) is None and (spec := importlib.util.find_spec(name)) is not None and spec.origin == "built-in") for name in ("math", "zlib")): raise SystemExit("owned-root-launcher: built-in module admission failed")
PY
IMPLEMENTATION_FILES=(build_owned_root.py prepared_projection.py owned_root_surface.py mesh_correctness.py render_export.py owned_root_launcher.sh compare_two_seed_outputs.py artifact_serialization.py anatomy_gates.py chart_lineage.py tests/test_build_owned_root.py tests/test_prepared_projection.py tests/test_owned_root_surface.py tests/test_mesh_correctness.py tests/test_render_export.py); expected="$(printf 'f %s\n' "${IMPLEMENTATION_FILES[@]}" | LC_ALL=C sort)"; actual="$(find -P "$PACKAGE_DIR" \( -name '*.py' -o -name '*.sh' \) -printf '%y %P\n' | LC_ALL=C sort)"
[[ "$actual" == "$expected" ]] || error "package implementation source does not match the exact 15-file allowlist"
for relative in "${IMPLEMENTATION_FILES[@]}"; do path="$PACKAGE_DIR/$relative"; [[ -f "$path" && ! -L "$path" ]] || error "required implementation file is missing or not regular: $relative"; (( $(stat -c '%s' -- "$path") <= 4000000 )) || error "implementation file exceeds 4,000,000 bytes: $relative"; done
cd -- "$REPO_ROOT"; token="$(if [[ -r /proc/sys/kernel/random/uuid ]]; then tr -d '-' </proc/sys/kernel/random/uuid; else printf '%s-%s' "$RANDOM" "$RANDOM"; fi)"; STAGING="$OUTPUT_PARENT/.owned-root-assembly-successor-$$-$token"; [[ ! -e "$STAGING" && ! -L "$STAGING" ]] || error "selected staging path is unexpectedly occupied"
PYTHONHASHSEED=0 "$CURRENT_LAUNCHER" "$BUILDER_ROLE" --internal-managed-tests --receipt "$STAGING/managed-test-receipt.json"
[[ -d "$STAGING" ]] || error "managed tests did not create the invocation staging root"
PYTHONHASHSEED=17 "$CURRENT_LAUNCHER" "$BUILDER_ROLE" --output "$STAGING/seed-17"
PYTHONHASHSEED=29 "$CURRENT_LAUNCHER" "$BUILDER_ROLE" --output "$STAGING/seed-29"
PYTHONHASHSEED=0 "$CURRENT_LAUNCHER" "$COMPARATOR_ROLE" "$STAGING/seed-17" "$STAGING/seed-29" --test-receipt "$STAGING/managed-test-receipt.json" --output "$STAGING/comparison"
[[ ! -e "$STAGING/managed-test-receipt.json" && ! -L "$STAGING/managed-test-receipt.json" ]] || error "managed-test receipt was not removed"
PYTHONHASHSEED=0 "$CURRENT_LAUNCHER" - "$STAGING" "$OUTPUT" <<'PY'
import sys; from pathlib import Path
sys.path.insert(0, "experiments/owned-root-assembly-successor"); import artifact_serialization as artifacts, compare_two_seed_outputs as comparator
root, target = Path(sys.argv[1]), Path(sys.argv[2]); artifacts.publish_no_replace(root, target, comparator.outer_publication_inventory(root), max_file_bytes=256 * 1024 * 1024)
PY
