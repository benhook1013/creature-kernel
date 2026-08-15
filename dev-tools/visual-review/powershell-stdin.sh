#!/usr/bin/env bash
set -euo pipefail

if (( $# != 0 )); then
  echo "usage: $0 < readable-script.ps1" >&2
  echo "error: arguments are not accepted; provide the PowerShell script on stdin" >&2
  exit 64
fi

powershell_bin="$(command -v powershell.exe || true)"
if [[ -z "$powershell_bin" ]]; then
  echo "error: powershell.exe was not found on PATH" >&2
  exit 127
fi

exec "$powershell_bin" -NoProfile -NonInteractive -File -
