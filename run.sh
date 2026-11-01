#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "Created .env. Add your TINYFISH_API_KEY to it, then run ./run.sh again."; exit 0; }
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
echo "ExitLens is live! Open http://localhost:${PORT}"
python -m uvicorn backend.app:app --host "${HOST}" --port "${PORT}"
