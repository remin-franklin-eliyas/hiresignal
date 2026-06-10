#!/usr/bin/env bash
set -euo pipefail

# Minimal demo runner for local development. Copy .env.example to .env
# and set required values before running.

if [ ! -f .env ]; then
  echo ".env not found — copying .env.example to .env (edit values before running)"
  cp .env.example .env
fi

echo "Starting HireSignal API on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
