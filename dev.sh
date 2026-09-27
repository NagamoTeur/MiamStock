#!/usr/bin/env bash
# Lance l'API (rechargement à chaud) et le serveur de dev Vite côté à côté.
#   ./dev.sh  puis  http://localhost:5273
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -e .
fi
if [[ ! -d web/node_modules ]]; then
  npm --prefix web install
fi

.venv/bin/python -m uvicorn miamstock.main:app --reload --port 8077 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

npm --prefix web run dev
