#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Prepare virtualenv
if [ ! -f ".env/bin/activate" ]; then
    python3 -m venv .env
fi
. ".env/bin/activate"

# Install dependencies
set -x
python3 -m pip install -r requirements.txt
