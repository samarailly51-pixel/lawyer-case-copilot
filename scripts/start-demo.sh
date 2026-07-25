#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"
runtime_dir="$repo_root/.demo-runtime"
venv_dir="$backend_dir/.venv"

mkdir -p "$runtime_dir"

if [[ ! -x "$venv_dir/bin/python" ]]; then
  python3 -m venv "$venv_dir"
fi

"$venv_dir/bin/python" -m pip install --disable-pip-version-check -r "$backend_dir/requirements.txt"
if [[ ! -d "$frontend_dir/node_modules" ]]; then
  npm ci --prefix "$frontend_dir"
fi

(
  cd "$backend_dir"
  MODEL_PROVIDER=mock AUTH_MODE=disabled "$venv_dir/bin/python" -m uvicorn main:app --host 127.0.0.1 --port 8000
) >"$runtime_dir/backend.log" 2>&1 &
backend_pid=$!

(
  cd "$frontend_dir"
  npm run dev -- --host 127.0.0.1 --port 5173
) >"$runtime_dir/frontend.log" 2>&1 &
frontend_pid=$!

printf '{"backend_pid":%s,"frontend_pid":%s}\n' "$backend_pid" "$frontend_pid" >"$runtime_dir/processes.json"

for _ in $(seq 1 60); do
  if curl --silent --fail http://127.0.0.1:8000/api/health >/dev/null; then
    printf 'Lawyer Case Copilot 已启动：http://localhost:5173\n'
    exit 0
  fi
  sleep 1
done

printf '后端健康检查超时，请查看 .demo-runtime/backend.log\n' >&2
exit 1
