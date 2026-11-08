#!/usr/bin/env bash
# Chạy cả backend (8000) và UI (5173). Nhấn Ctrl+C để dừng cả hai.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -x "$ROOT/backend/.venv/bin/python" ]; then
  python3 -m venv "$ROOT/backend/.venv"
fi
"$ROOT/backend/.venv/bin/python" -c "import fastapi, uvicorn" 2>/dev/null \
  || "$ROOT/backend/.venv/bin/python" -m pip install -q -r "$ROOT/backend/requirements.txt"
[ -d "$ROOT/UI/node_modules" ] || (cd "$ROOT/UI" && npm install)

trap 'kill 0' EXIT
(cd "$ROOT/backend" && .venv/bin/python -m uvicorn app.main:app --reload --no-access-log --port 8000) &
(cd "$ROOT/UI" && npm run dev -- --host 127.0.0.1) &
echo "Backend: http://127.0.0.1:8000   UI: http://127.0.0.1:5173"
wait
