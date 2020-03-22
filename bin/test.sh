#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. .env/bin/activate

# Run tests etc.
set -x
python3 -m black --check src/ tests/ setup.py
python3 -m mypy src/
python3 -m pylint --rcfile=pylintrc src/ tests/ setup.py
python3 -m coverage run setup.py test --test-suite tests.unit
python3 -m coverage run -a setup.py test --test-suite tests.integration
