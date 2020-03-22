#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(dirname "$0")/.."

# Prepare virtualenv
if [ ! -f "$PROJECT_ROOT/.env/bin/activate" ]; then
    python3 -m venv "$PROJECT_ROOT/.env"
fi
. "$PROJECT_ROOT/.env/bin/activate"

# Install dependencies
set -x
python3 -m pip install -r requirements.txt
