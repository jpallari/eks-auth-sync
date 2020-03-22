#!/bin/sh
set -euo pipefail
PROJECT_ROOT="$(dirname "$0")/.."
. "$PROJECT_ROOT/.env/bin/activate"

# Run tests etc.
set -x
black --check src/ tests/ setup.py
pylint --rcfile="$PROJECT_ROOT/pylintrc" src/ tests/ setup.py
mypy src/
python3 setup.py test --test-suite tests.unit
python3 setup.py test --test-suite tests.integration
