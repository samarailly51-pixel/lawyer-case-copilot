#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pid_file="$repo_root/.demo-runtime/processes.json"

if [[ ! -f "$pid_file" ]]; then
  printf '未发现正在运行的 Demo。\n'
  exit 0
fi

backend_pid="$(sed -n 's/.*"backend_pid":\([0-9]*\).*/\1/p' "$pid_file")"
frontend_pid="$(sed -n 's/.*"frontend_pid":\([0-9]*\).*/\1/p' "$pid_file")"
[[ -n "$backend_pid" ]] && kill "$backend_pid" 2>/dev/null || true
[[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
rm -f "$pid_file"
printf 'Lawyer Case Copilot Demo 已停止。\n'
