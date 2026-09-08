#!/usr/bin/env bash

set -euo pipefail

if (( $# == 0 )); then
    printf 'usage: %s PATTERN [PATH ...]\n' "$0" >&2
    exit 64
fi

pattern=$1
shift

if (( $# == 0 )); then
    set -- .
fi

for path in "$@"; do
    if [[ $path == -* ]]; then
        printf '%s: option-shaped path is not allowed after the pattern: %q\n' "$0" "$path" >&2
        exit 64
    fi
done

exec rg -n -C 2 -- "$pattern" "$@"
