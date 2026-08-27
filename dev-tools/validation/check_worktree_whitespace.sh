#!/usr/bin/env bash

set -uo pipefail

repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
root_status=$?
if (( root_status != 0 )); then
    printf '%s\n' 'check_worktree_whitespace.sh: not inside a Git repository' >&2
    exit "$root_status"
fi

failed=0

run_index_check() {
    local label=$1
    shift
    local check_status=0

    "$@" || check_status=$?
    if (( check_status != 0 )); then
        printf 'whitespace check failed (%s; git exit %d)\n' "$label" "$check_status" >&2
        failed=1
    fi
}

run_index_check 'tracked unstaged changes' git -C "$repo_root" diff --check --
run_index_check 'staged changes' git -C "$repo_root" diff --cached --check --

untracked_list=$(mktemp)
list_status=0
git -C "$repo_root" ls-files --others --exclude-standard -z >"$untracked_list" || list_status=$?
if (( list_status != 0 )); then
    printf 'unable to enumerate untracked files (git exit %d)\n' "$list_status" >&2
    exit "$list_status"
fi

diagnostic_file=$(mktemp)
cleanup() {
    rm -f -- "$untracked_list" "$diagnostic_file"
}
trap cleanup EXIT

while IFS= read -r -d '' path; do
    : >"$diagnostic_file"
    check_status=0
    git -C "$repo_root" diff --no-index --check -- /dev/null "$path" \
        >"$diagnostic_file" 2>&1 || check_status=$?

    if [[ -s "$diagnostic_file" ]]; then
        printf 'whitespace check failed (untracked file %q; git exit %d)\n' \
            "$path" "$check_status" >&2
        cat "$diagnostic_file" >&2
        failed=1
    elif (( check_status != 0 && check_status != 1 )); then
        printf 'untracked file check failed (file %q; git exit %d)\n' \
            "$path" "$check_status" >&2
        failed=1
    fi
done <"$untracked_list"

exit "$failed"
