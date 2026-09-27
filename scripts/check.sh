#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/ruff check backend scripts
.venv/bin/pytest -q
npm test --prefix frontend
npm run build --prefix frontend
