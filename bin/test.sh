#!/bin/sh
set -euo pipefail
PROJECT_ROOT="$(dirname "$0")/.."

# Run tests etc.
set -x
black --check src/ tests/ setup.py
mypy src/
pylint --rcfile="$PROJECT_ROOT/pylintrc" src/ tests/ setup.py
python3 setup.py test --test-suite tests.unit
python3 setup.py test --test-suite tests.integration
