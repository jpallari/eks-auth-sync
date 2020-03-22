#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(dirname "$0")/.."
. "$PROJECT_ROOT/.env/bin/activate"

# Run tests etc.
set -x
python3 -m black --check src/ tests/ setup.py
python3 -m mypy src/
python3 -m pylint --rcfile="$PROJECT_ROOT/pylintrc" src/ tests/ setup.py
python3 setup.py test --test-suite tests.unit
python3 setup.py test --test-suite tests.integration
