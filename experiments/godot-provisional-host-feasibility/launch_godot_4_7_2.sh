#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

readonly GODOT_RELATIVE_PATH='creature-kernel/godot/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64'
readonly EXPECTED_SHA256='8d106cbe6144c2dc7e881d61d2429c1a8a76e6b22ef48bd5e48dcf934953f71e'
readonly EXPECTED_VERSION='4.7.2.stable.official.ed1daf0bf'
readonly PREFLIGHT_FAILURE_STATUS=78

fail_preflight() {
    printf 'Godot 4.7.2 preflight failed: %s\n' "$1" >&2
    exit "$PREFLIGHT_FAILURE_STATUS"
}

reject_symlink_path() {
    local current_path=$1

    while [[ "$current_path" != '/' ]]; do
        if [[ -L "$current_path" ]]; then
            return 1
        fi
        current_path=${current_path%/*}
        if [[ -z "$current_path" ]]; then
            current_path='/'
        fi
    done
}

# An explicitly empty or relative override is rejected rather than silently
# selecting another path. Default cache-root validation is only needed when no
# explicit executable override selected the binary.
if [[ "${CK_GODOT_4_7_2_BINARY+set}" == 'set' ]]; then
    binary_path="$CK_GODOT_4_7_2_BINARY"
else
    if [[ -n "${XDG_CACHE_HOME-}" ]]; then
        cache_root="$XDG_CACHE_HOME"
        if [[ "$cache_root" != /* ]]; then
            fail_preflight 'XDG_CACHE_HOME must be an absolute path'
        fi
    else
        if [[ -z "${HOME-}" ]]; then
            fail_preflight 'HOME must be non-empty when XDG_CACHE_HOME is not selected'
        fi
        if [[ "${HOME-}" != /* ]]; then
            fail_preflight 'HOME must be an absolute path'
        fi
        cache_root="${HOME-}/.cache"
    fi

    if [[ -z "$cache_root" || "$cache_root" != /* ]]; then
        fail_preflight 'the selected cache root must be non-empty and absolute'
    fi
    binary_path="$cache_root/$GODOT_RELATIVE_PATH"
fi

if [[ "$binary_path" != /* ]]; then
    fail_preflight 'the executable path must be absolute'
fi

if ! reject_symlink_path "$binary_path"; then
    fail_preflight 'the executable path or one of its components is a symlink'
fi

if [[ ! -f "$binary_path" ]]; then
    fail_preflight 'the executable is missing or not a regular file'
fi

if [[ ! -x "$binary_path" ]]; then
    fail_preflight 'the executable is not executable'
fi

digest_output="$(sha256sum -- "$binary_path" 2>/dev/null)" || \
    fail_preflight 'could not calculate the executable SHA-256'
actual_sha256="${digest_output%% *}"
if [[ "$actual_sha256" != "$EXPECTED_SHA256" ]]; then
    fail_preflight 'the executable SHA-256 does not match the pinned copy'
fi

version_output="$("$binary_path" --version 2>&1)" || \
    fail_preflight 'the executable failed the --version probe'
if [[ "$version_output" != "$EXPECTED_VERSION" ]]; then
    fail_preflight 'the executable --version output is not the pinned version'
fi

# Deliberately inherit TEMP/TMP and every other caller environment variable.
# Do not translate WSL/native-Linux paths or synthesize temporary directories.
# exec also preserves the exact Godot exit status and forwards every argument.
exec "$binary_path" "$@"
