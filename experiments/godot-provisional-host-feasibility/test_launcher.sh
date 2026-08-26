#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/launch_godot_4_7_2.sh"
PINNED_SHA256='8d106cbe6144c2dc7e881d61d2429c1a8a76e6b22ef48bd5e48dcf934953f71e'
EXPECTED_VERSION='4.7.2.stable.official.ed1daf0bf'
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/ck-godot-preflight.XXXXXX")"

cleanup() {
    local owned_path

    if [[ "$TEST_ROOT" != /*/ck-godot-preflight.* || ! -d "$TEST_ROOT" || -L "$TEST_ROOT" ]]; then
        return 0
    fi

    while IFS= read -r -d '' owned_path; do
        if [[ -f "$owned_path" || -L "$owned_path" ]]; then
            unlink -- "$owned_path"
        fi
    done < <(find "$TEST_ROOT" -depth -mindepth 1 \( -type f -o -type l \) -print0)

    while IFS= read -r -d '' owned_path; do
        if [[ -d "$owned_path" && ! -L "$owned_path" ]]; then
            rmdir -- "$owned_path"
        fi
    done < <(find "$TEST_ROOT" -depth -mindepth 1 -type d -print0)

    if [[ -d "$TEST_ROOT" && ! -L "$TEST_ROOT" ]]; then
        rmdir -- "$TEST_ROOT"
    fi
}
trap cleanup EXIT

fail_test() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_contains() {
    local needle=$1
    local haystack=$2
    grep -Fq -- "$needle" "$haystack" || \
        fail_test "expected $haystack to contain: $needle"
}

make_fake_executable() {
    local fake_path=$1
    local reported_version=$2
    local exit_status=$3
    local args_path=$4
    local environment_path=$5

    {
        printf '%s\n' '#!/usr/bin/env bash'
        printf '%s\n' 'set -o errexit -o nounset -o pipefail'
        printf '%s\n' 'if [[ "$#" -eq 1 && "$1" == "--version" ]]; then'
        printf '    printf "%%s\\n" %q\n' "$reported_version"
        printf '%s\n' '    exit 0'
        printf '%s\n' 'fi'
        printf 'printf "%%s\\0" "$@" > %q\n' "$args_path"
        printf 'printf "%%s\\0" "${TEMP-__UNSET__}" "${TMP-__UNSET__}" > %q\n' "$environment_path"
        printf 'exit %d\n' "$exit_status"
    } > "$fake_path"
    chmod +x -- "$fake_path"
}

make_launcher_copy() {
    local fake_path=$1
    local copy_path=$2
    local fake_sha256

    cp -- "$LAUNCHER" "$copy_path"
    chmod +x -- "$copy_path"
    fake_sha256="$(sha256sum -- "$fake_path")"
    fake_sha256="${fake_sha256%% *}"
    sed -i "s/$PINNED_SHA256/$fake_sha256/g" "$copy_path"
}

run_failure_case() {
    local case_name=$1
    local candidate=$2
    local expected_message=$3
    local stderr_path="$TEST_ROOT/$case_name.stderr"
    local status

    set +o errexit
    CK_GODOT_4_7_2_BINARY="$candidate" "$LAUNCHER" > /dev/null 2> "$stderr_path"
    status=$?
    set -o errexit

    [[ "$status" -ne 0 ]] || fail_test "$case_name unexpectedly succeeded"
    assert_contains "$expected_message" "$stderr_path"
}

run_default_failure_case() {
    local case_name=$1
    local expected_message=$2
    local stderr_path="$TEST_ROOT/$case_name.stderr"
    local status
    shift 2

    set +o errexit
    env -u CK_GODOT_4_7_2_BINARY "$@" "$LAUNCHER" > /dev/null 2> "$stderr_path"
    status=$?
    set -o errexit

    [[ "$status" -ne 0 ]] || fail_test "$case_name unexpectedly succeeded"
    assert_contains "$expected_message" "$stderr_path"
}

unset CK_GODOT_4_7_2_BINARY

good_fake="$TEST_ROOT/good-godot"
good_args="$TEST_ROOT/good.args"
good_environment="$TEST_ROOT/good.environment"
make_fake_executable "$good_fake" "$EXPECTED_VERSION" 23 "$good_args" "$good_environment"

success_launcher="$TEST_ROOT/success-launcher.sh"
make_launcher_copy "$good_fake" "$success_launcher"

set +o errexit
TEMP='/wsl-temp/keep-me' TMP='/native-linux-temp/keep-me' \
    CK_GODOT_4_7_2_BINARY="$good_fake" \
    "$success_launcher" 'first argument' '--flag=value with spaces' '' > /dev/null
success_status=$?
set -o errexit
[[ "$success_status" -eq 23 ]] || \
    fail_test "expected Godot exit status 23, got $success_status"

mapfile -d '' forwarded_args < "$good_args"
expected_args=('first argument' '--flag=value with spaces' '')
[[ "${#forwarded_args[@]}" -eq "${#expected_args[@]}" ]] || \
    fail_test 'argument count was not preserved'
for index in "${!expected_args[@]}"; do
    [[ "${forwarded_args[$index]}" == "${expected_args[$index]}" ]] || \
        fail_test "argument $index was not preserved"
done

mapfile -d '' inherited_environment < "$good_environment"
[[ "${inherited_environment[0]}" == '/wsl-temp/keep-me' ]] || \
    fail_test 'TEMP was not inherited unchanged'
[[ "${inherited_environment[1]}" == '/native-linux-temp/keep-me' ]] || \
    fail_test 'TMP was not inherited unchanged'

xdg_default_fake="$TEST_ROOT/xdg-cache/creature-kernel/godot/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64"
xdg_default_args="$TEST_ROOT/xdg-default.args"
xdg_default_environment="$TEST_ROOT/xdg-default.environment"
mkdir -p -- "$(dirname -- "$xdg_default_fake")"
make_fake_executable "$xdg_default_fake" "$EXPECTED_VERSION" 17 \
    "$xdg_default_args" "$xdg_default_environment"
xdg_default_launcher="$TEST_ROOT/xdg-default-launcher.sh"
make_launcher_copy "$xdg_default_fake" "$xdg_default_launcher"
set +o errexit
env -u CK_GODOT_4_7_2_BINARY XDG_CACHE_HOME="$TEST_ROOT/xdg-cache" HOME='relative-home' \
    "$xdg_default_launcher" 'xdg-default' > /dev/null
xdg_default_status=$?
set -o errexit
[[ "$xdg_default_status" -eq 17 && -s "$xdg_default_args" ]] || \
    fail_test 'XDG_CACHE_HOME default path was not selected'

home_default_fake="$TEST_ROOT/home-root/.cache/creature-kernel/godot/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64"
home_default_args="$TEST_ROOT/home-default.args"
home_default_environment="$TEST_ROOT/home-default.environment"
mkdir -p -- "$(dirname -- "$home_default_fake")"
make_fake_executable "$home_default_fake" "$EXPECTED_VERSION" 19 \
    "$home_default_args" "$home_default_environment"
home_default_launcher="$TEST_ROOT/home-default-launcher.sh"
make_launcher_copy "$home_default_fake" "$home_default_launcher"
set +o errexit
env -u CK_GODOT_4_7_2_BINARY -u XDG_CACHE_HOME HOME="$TEST_ROOT/home-root" \
    "$home_default_launcher" 'home-unset-xdg' > /dev/null
home_unset_xdg_status=$?
env -u CK_GODOT_4_7_2_BINARY XDG_CACHE_HOME='' HOME="$TEST_ROOT/home-root" \
    "$home_default_launcher" 'home-empty-xdg' > /dev/null
home_empty_xdg_status=$?
set -o errexit
[[ "$home_unset_xdg_status" -eq 19 && "$home_empty_xdg_status" -eq 19 && -s "$home_default_args" ]] || \
    fail_test 'HOME fallback did not work for unset and empty XDG_CACHE_HOME'

run_failure_case 'relative-path' 'relative/godot' 'path must be absolute'
run_failure_case 'missing-path' "$TEST_ROOT/missing" 'missing or not a regular file'

directory_candidate="$TEST_ROOT/directory"
mkdir -- "$directory_candidate"
run_failure_case 'directory-path' "$directory_candidate" 'missing or not a regular file'

non_executable_candidate="$TEST_ROOT/non-executable"
printf '%s\n' 'not executable' > "$non_executable_candidate"
run_failure_case 'non-executable-path' "$non_executable_candidate" 'not executable'

symlink_candidate="$TEST_ROOT/symlink"
ln -s -- "$good_fake" "$symlink_candidate"
run_failure_case 'symlink-path' "$symlink_candidate" 'is a symlink'

real_directory="$TEST_ROOT/real-directory"
symlink_directory="$TEST_ROOT/symlink-directory"
mkdir -- "$real_directory"
cp -- "$good_fake" "$real_directory/godot"
chmod +x -- "$real_directory/godot"
ln -s -- "$real_directory" "$symlink_directory"
run_failure_case 'symlink-component' "$symlink_directory/godot" 'is a symlink'

run_failure_case 'wrong-digest' "$good_fake" 'SHA-256 does not match'

run_default_failure_case 'relative-xdg' 'XDG_CACHE_HOME must be an absolute path' \
    XDG_CACHE_HOME=relative-cache HOME="$TEST_ROOT/home-root"
run_default_failure_case 'empty-home' 'HOME must be non-empty' \
    -u XDG_CACHE_HOME HOME=''
run_default_failure_case 'relative-home' 'HOME must be an absolute path' \
    -u XDG_CACHE_HOME HOME=relative-home

wrong_version_fake="$TEST_ROOT/wrong-version-godot"
wrong_version_args="$TEST_ROOT/wrong-version.args"
wrong_version_environment="$TEST_ROOT/wrong-version.environment"
make_fake_executable "$wrong_version_fake" '4.7.2.stable.official.wrong' 0 \
    "$wrong_version_args" "$wrong_version_environment"
wrong_version_launcher="$TEST_ROOT/wrong-version-launcher.sh"
make_launcher_copy "$wrong_version_fake" "$wrong_version_launcher"
set +o errexit
CK_GODOT_4_7_2_BINARY="$wrong_version_fake" \
    "$wrong_version_launcher" > /dev/null 2> "$TEST_ROOT/wrong-version.stderr"
wrong_version_status=$?
set -o errexit
[[ "$wrong_version_status" -ne 0 ]] || fail_test 'wrong version unexpectedly succeeded'
assert_contains 'version output is not the pinned version' "$TEST_ROOT/wrong-version.stderr"

printf 'PASS: Godot 4.7.2 launcher preflight and forwarding checks\n'
