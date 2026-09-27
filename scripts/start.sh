#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then
  "${PYTHON_BIN:-python3}" -m venv .venv
fi
.venv/bin/python -m ensurepip --upgrade >/dev/null
.venv/bin/python -m pip install -q -r backend/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.simulator
exec ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${APP_PORT:-8765}" --workers 1
