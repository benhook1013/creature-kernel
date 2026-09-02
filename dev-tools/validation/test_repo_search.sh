#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
search_script=$repo_root/dev-tools/repo_search.sh

bash -n "$search_script" "$0"

tmp_dir=$(mktemp -d -t repo-search-test.XXXXXX)
trap 'rm -rf -- "$tmp_dir"' EXIT

test_root=$tmp_dir/repository
mkdir -p "$test_root/space dir"
printf 'before\n-dash-leading\nafter\n' >"$test_root/dash.txt"
printf 'before\nnormal needle\nafter\n' >"$test_root/normal.txt"
printf 'needle with spaces\n' >"$test_root/space dir/result.txt"
printf 'default-marker\n' >"$test_root/default.txt"

dash_output=$(cd -- "$test_root" && "$search_script" '-dash-leading')
[[ $dash_output == *'dash.txt:2:-dash-leading'* ]]

normal_output=$("$search_script" 'normal needle' "$test_root/normal.txt")
[[ $normal_output == *'2:normal needle'* ]]

default_output=$(cd -- "$test_root" && "$search_script" 'default-marker')
[[ $default_output == *'default.txt:1:default-marker'* ]]

spaces_output=$("$search_script" 'needle with spaces' "$test_root/space dir")
[[ $spaces_output == *"$test_root/space dir/result.txt:1:needle with spaces"* ]]

fake_bin=$tmp_dir/fake-bin
rg_called=$tmp_dir/rg-called
mkdir -p "$fake_bin"
printf '#!/usr/bin/env bash\n: >"%s"\nexit 99\n' "$rg_called" >"$fake_bin/rg"
chmod +x "$fake_bin/rg"

option_error=$tmp_dir/option-error
set +e
PATH="$fake_bin:$PATH" "$search_script" needle '--glob=*.txt' 2>"$option_error"
option_status=$?
set -e
[[ $option_status -eq 64 ]]
[[ ! -e $rg_called ]]
rg -F -- 'option-shaped path is not allowed' "$option_error" >/dev/null

set +e
"$search_script" 'does-not-match' "$test_root/normal.txt" >/dev/null
no_match_status=$?
set -e
[[ $no_match_status -eq 1 ]]

printf '%s\n' 'repo_search.sh tests passed'
